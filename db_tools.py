import os
# Third-party imports
from google.appengine.api.app_identity import get_application_id
from google.appengine.ext import ndb
from lxml import etree
from lxml.builder import E
# Project imports
import model

PATH_TO_INIT_FILE = "init/init_data.xml"
PARSER = etree.XMLParser(remove_comments=True)


class DbToolsException(BaseException):
    pass


class NodeReader(object):
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

    def get_bool(self):
        return bool(self.get_int())

    def get_int(self):
        return int(self.get_text())

    def get_text(self):
        return self._normalize() if self.type != 'non-leaf' else None

    def xpath(self, *args, **kwargs):
        return self.node.xpath(*args, **kwargs)

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


def by_property(entity_kind, property_, value, key_only=True):
    qry_params = {}
    if get_application_id() != 'testbed-test':
        qry_params['ancestor'] = model.ANCESTOR

    entity = entity_kind.query(**qry_params).filter(property_ == value).get()

    if entity is None:
        raise DbToolsException(
            'Entity with {} == {} was not found for entity_kind {}'.format(
                property_, str(value).encode('utf-8'), entity_kind.__name__))
    elif key_only:
        return entity.key
    return entity


def get_kind(raw_kind):
    if isinstance(raw_kind, basestring):
        return getattr(model, raw_kind)
    else:
        return raw_kind


def insert_or_update(entity_kind, entity_properties, load_mode):
    if get_application_id() != 'testbed-test':
        entity_properties['parent'] = model.ANCESTOR

    if load_mode == 'init':
        entity = entity_kind(**entity_properties)
    else:  # load_mode == 'patch'
        entity = by_property(
            entity_kind=entity_kind,
            property_=entity_kind.id,
            value=entity_properties['id'],
            key_only=False
        )
        if entity is not None:
            entity.populate(**entity_properties)
        else:
            entity = entity_kind(**entity_properties)

    entity.put()


def iter_existing_kinds():
    for name in model.__dict__:
        obj = getattr(model, name)

        try:
            if issubclass(obj, model.BaseModel) and obj is not model.BaseModel:
                yield obj
        except TypeError:
            pass


def bulk_load(load_mode='init', xml=None):
    if load_mode == 'init':
        for kind in iter_existing_kinds():
            ndb.delete_multi(kind.query().iter(keys_only=True))  # clean up

        path = os.path.join(os.path.dirname(__file__), PATH_TO_INIT_FILE)
        with open(path, 'r') as f:
            xml = f.read()
    elif load_mode == 'patch':
        if xml is None:
            raise DbToolsException("Patch not provided")
    elif load_mode is None or load_mode == '':
        raise DbToolsException('Bulk load mode not specified')
    else:
        raise DbToolsException("Unknown bulk load mode: {}".format(load_mode))

    root = etree.fromstring(xml, PARSER)

    for kind_node in root:
        entity_kind = getattr(model, kind_node.tag)

        if kind_node.get('delete') == 'true':
            for item_node in kind_node:
                by_property(
                    entity_kind=entity_kind,
                    property_=entity_kind.id,
                    value=int(item_node.find('id').text)
                ).delete()
            continue

        for item_node in kind_node:
            entity_properties = {}

            for property_node in item_node:
                property_name = property_node.tag
                property_class = getattr(entity_kind, property_name)
                reader = NodeReader(property_node)

                if property_class.__class__.__name__ == 'IntegerProperty':
                    value_to_store = reader.get_int()
                elif property_class.__class__.__name__ == 'BooleanProperty':
                    value_to_store = reader.get_bool()
                elif property_class.__class__.__name__ == 'KeyProperty':
                    referred_kind = get_kind(property_class._kind)
                    req_params = {
                        'kind': referred_kind, 'property': referred_kind.id}
                    if property_class._repeated:
                        value_to_store = []
                        for id_ in map(int, reader.xpath('item/text()')):
                            req_params['value'] = id_
                            value_to_store.append(by_property(**req_params))
                    else:
                        req_params['value'] = reader.get_int()
                        value_to_store = by_property(**req_params)
                # Property is ndb.StringProperty, ndb.TextProperty or other
                else:
                    value_to_store = reader.get_text()

                entity_properties[property_name] = value_to_store

            insert_or_update(
                entity_kind, entity_properties, load_mode=load_mode)


def create_patch(modified):
    original = os.path.join(os.path.dirname(__file__), PATH_TO_INIT_FILE)

    modified_root = etree.fromstring(modified, parser=PARSER)
    original_root = etree.parse(original, parser=PARSER).getroot()
    patch_root = etree.Element('data')

    for kind_node in modified_root:
        patch_kind_node = etree.Element(kind_node.tag)
        patch_kind_node_w_delete = etree.Element(
            kind_node.tag, attrib={'delete': 'true'})

        ids_xpath = 'item/id/text()'
        original_ids = original_root.find(kind_node.tag).xpath(ids_xpath)
        modified_ids = kind_node.xpath(ids_xpath)

        for id_ in set(original_ids) - set(modified_ids):
            patch_kind_node_w_delete.append(E.item(E.id(id_)))

        for id_ in modified_ids:
            pass  # TODO: finish

