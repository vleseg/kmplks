import logging
import os
# Third-party imports
from google.appengine.ext import ndb
from lxml import etree
# Project imports
import model


class TestDbInitException(BaseException):
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
            if self.node.tag == 'description':
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


class RefMeta(object):
    def __init__(self, raw_data):
        tg = TextGetter(raw_data)
        self.referring_property = tg.name
        self.referred_kind = getattr(model, tg.refd_kind)
        self.referred_field = getattr(self.referred_kind, tg.refd_field)
        self.reference_type = tg.attr('type')


def get_entity_key(kind, prop, value):
    try:
        return kind.query(
            ancestor=model.ANCESTOR).filter(prop == value).get().key
    except AttributeError:
        raise TestDbInitException(
            'Entity with {} == {} was not found for kind {}'.format(
                prop, value.encode('utf-8'), kind.__name__))


def put_new_entity(entity_class, entity_init_kwargs):
    entity_init_kwargs['parent'] = model.ANCESTOR
    new_entity = entity_class(**entity_init_kwargs)
    new_entity.put()


def init_test_db():
    parser = etree.XMLParser(remove_comments=True)
    file_path = os.path.join(os.path.dirname(__file__), "test_data.xml")
    root = etree.parse(file_path, parser).getroot()

    for kind_node in root:
        entity_class = getattr(model, kind_node.tag)
        references = {}

        for _kind_node_child in kind_node:
            entity_init_kwargs = {}

            if _kind_node_child.tag == 'reference':
                rm = RefMeta(_kind_node_child)
                references[rm.referring_property] = rm
            else:
                instance_node = _kind_node_child
                for property_node in instance_node:
                    property_name = property_node.tag
                    property_class = type(getattr(entity_class, property_name))
                    ref_meta_entry = references.get(property_name)
                    raw_value = TextGetter(property_node).get_text()

                    if property_class is ndb.IntegerProperty:
                        value_to_store = int(raw_value)
                    elif property_class is ndb.BooleanProperty:
                        value_to_store = bool(int(raw_value))
                    # Property is ndb.KeyProperty -- single or repeated
                    elif ref_meta_entry is not None:
                        f_kwargs = dict(kind=ref_meta_entry.referred_kind,
                                        prop=ref_meta_entry.referred_field)
                        if ref_meta_entry.reference_type == 'to_one':
                            f_kwargs['value'] = raw_value
                            value_to_store = get_entity_key(**f_kwargs)
                        elif ref_meta_entry.reference_type == 'to_many':
                            value_to_store = []
                            for property_node_child in property_node:
                                f_kwargs['value'] = TextGetter(
                                    property_node_child).get_text()
                                value_to_store.append(
                                    get_entity_key(**f_kwargs))
                        else:
                            raise TestDbInitException(
                                "Unknown reference type: {}".format(
                                    ref_meta_entry.reference_type))
                    # Property is ndb.StringProperty, ndb.TextProperty or other
                    else:
                        value_to_store = raw_value
                    entity_init_kwargs[property_name] = value_to_store

                put_new_entity(entity_class, entity_init_kwargs)
