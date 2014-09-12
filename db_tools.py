import logging
import os
# Third-party imports
from google.appengine.api.app_identity import get_application_id
from google.appengine.ext import ndb
from lxml import etree
# Project imports
import model

PATH_TO_INIT_FILE = "init/init_data.xml"


class DbToolsException(BaseException):
    pass


class TextGetter(object):
    """
    Has to be initialized with XML node (etree.Element). Use it to retrieve
    node attrs or contents -- as plain text, serialized XHTML or None, if it
    is not a leaf node.
    """
    def __init__(self, node):
        self.node = node
        if len(node) > 0:  # if it is not a leaf node
            if 'description' in self.node.tag:
                self.type = 'xhtml'
            else:
                self.type = 'non-leaf'
        else:
            self.type = 'plain'

    def __getattr__(self, item):
        sub = self.node.find(item)
        if sub is None or sub.text is None:
            return None
        else:
            return self._normalize(sub.text)

    def attr(self, attr_name):
        if attr_name in self.node.attrib:
            return self.node.attrib[attr_name]
        return None

    def get_text(self):
        return self._normalize() if self.type != 'non-leaf' else None

    def _normalize(self, input_=None):
        """
        If input_ is given, it will be normalized. Otherwise self.node.text is
        processed.
        """
        if input_ is not None:
            return ' '.join(input_.split())
        if self.type == 'plain':
            result = ' '.join(self.node.text.split())
        else:  # self.type == 'xhtml'
            container = etree.Element('div')
            for e in self.node:
                container.append(e)
            result = etree.tounicode(container)
        return result


def get_entity_by_prop(kind, prop, value, key_only=True):
    qry_params = {}
    if get_application_id() != 'testbed-test':
        qry_params['ancestor'] = model.ANCESTOR

    entity = kind.query(**qry_params).filter(prop == value).get()

    if key_only:
        if entity is None:
            raise DbToolsException(
                'Entity with {} == {} was not found for kind {}'.format(
                    prop, str(value).encode('utf-8'), kind.__name__))
        return entity.key
    return entity


def get_kind(raw_kind):
    if isinstance(raw_kind, basestring):
        return getattr(model, raw_kind)
    else:
        return raw_kind


def insert_or_update(entity_class, entity_init_kwargs):
    if get_application_id() != 'testbed-test':
        entity_init_kwargs['parent'] = model.ANCESTOR
    if entity_init_kwargs.pop('load_mode') == 'init':
        entity = entity_class(**entity_init_kwargs)
    else:  # load_mode == 'patch'
        # TODO: test coverage
        entity = get_entity_by_prop(
            entity_class, entity_class.id, entity_init_kwargs['id'],
            key_only=False)
        if entity is not None:
            entity.populate(**entity_init_kwargs)
        else:
            entity = entity_class(**entity_init_kwargs)
    entity.put()


def iter_kinds():
    for name in model.__dict__:
        kind = getattr(model, name)
        if isinstance(kind, type) and issubclass(ndb.Model, kind):
            yield kind


def bulk_load(load_mode='init', xml=None):
    if load_mode == 'init':
        for kind in iter_kinds():
            ndb.delete_multi(kind.query().iter(keys_only=True))  # clean up
        path = os.path.join(os.path.dirname(__file__), PATH_TO_INIT_FILE)
        with open(path, 'r') as f:
            xml = f.read()
    elif load_mode == 'patch':
        if xml is None:
            raise DbToolsException("patch not provided")
    else:
        raise DbToolsException("Unknown bulk load mode: {}".format(load_mode))

    parser = etree.XMLParser(remove_comments=True)
    root = etree.fromstring(xml, parser)

    for kind_node in root:
        entity_class = getattr(model, kind_node.tag)

        if kind_node.get('delete') == 'true':
            for item_node in kind_node:
                entity = get_entity_by_prop(
                    entity_class, entity_class.id,
                    int(item_node.find('id').text))
                entity.delete()
            continue

        for _kind_node_child in kind_node:
            entity_init_kwargs = {}

            instance_node = _kind_node_child
            for property_node in instance_node:
                property_name = property_node.tag
                property_class = getattr(entity_class, property_name)
                raw_value = TextGetter(property_node).get_text()

                if property_class.__class__.__name__ == 'IntegerProperty':
                    value_to_store = int(raw_value)
                elif property_class.__class__.__name__ == 'BooleanProperty':
                    value_to_store = bool(int(raw_value))
                elif property_class.__class__.__name__ == 'KeyProperty':
                    referred_kind = get_kind(property_class._kind)
                    f_kwargs = dict(kind=referred_kind,
                                    prop=referred_kind.id)
                    if property_class._repeated:
                        value_to_store = []
                        for property_node_child in property_node:
                            f_kwargs['value'] = int(TextGetter(
                                property_node_child).get_text())
                            value_to_store.append(get_entity_by_prop(**f_kwargs))
                    else:
                        f_kwargs['value'] = int(raw_value)
                        value_to_store = get_entity_by_prop(**f_kwargs)
                # Property is ndb.StringProperty, ndb.TextProperty or other
                else:
                    value_to_store = raw_value
                entity_init_kwargs[property_name] = value_to_store
            entity_init_kwargs.update({'load_mode': load_mode})

            insert_or_update(entity_class, entity_init_kwargs)

    def create_patch(modified):
        original = os.path.join(os.path.dirname(__file__), PATH_TO_INIT_FILE)