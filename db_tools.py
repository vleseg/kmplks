import logging
import os
# Third-party imports
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


def get_entity_key(kind, prop, value, test_mode):
    try:
        if not test_mode:
            return kind.query(
                ancestor=model.ANCESTOR).filter(prop == value).get().key
        else:
            return kind.query().filter(prop == value).get().key
    except AttributeError:
        raise DbToolsException(
            'Entity with {} == {} was not found for kind {}'.format(
                prop, value.encode('utf-8'), kind.__name__))


def get_kind(raw_kind):
    if isinstance(raw_kind, basestring):
        return getattr(model, raw_kind)
    else:
        return raw_kind


def insert_or_update(entity_class, entity_init_kwargs):
    if not entity_init_kwargs.pop('test_mode'):
        entity_init_kwargs['parent'] = model.ANCESTOR
    if entity_init_kwargs.pop('load_mode') == 'init':
        new_entity = entity_class(**entity_init_kwargs)
        new_entity.put()
    else:  # TODO: patch mode
        pass


def bulk_load(test_mode=False, load_mode='init', f=None):
    if load_mode == 'init':
        f = os.path.join(os.path.dirname(__file__), PATH_TO_INIT_FILE)
    elif load_mode == 'patch':
        if f is None:
            raise DbToolsException("Patch file not provided")
    else:
        raise DbToolsException("Unknown bulk load mode: {}".format(load_mode))

    parser = etree.XMLParser(remove_comments=True)
    root = etree.parse(f, parser).getroot()

    for kind_node in root:
        entity_class = getattr(model, kind_node.tag)

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
                                    prop=referred_kind.id,
                                    test_mode=test_mode)
                    if property_class._repeated:
                        value_to_store = []
                        for property_node_child in property_node:
                            f_kwargs['value'] = int(TextGetter(
                                property_node_child).get_text())
                            value_to_store.append(get_entity_key(**f_kwargs))
                    else:
                        f_kwargs['value'] = int(raw_value)
                        value_to_store = get_entity_key(**f_kwargs)
                # Property is ndb.StringProperty, ndb.TextProperty or other
                else:
                    value_to_store = raw_value
                entity_init_kwargs[property_name] = value_to_store
                entity_init_kwargs.update({
                    'test_mode': test_mode,
                    'load_mode': load_mode
                })

            insert_or_update(entity_class, entity_init_kwargs)