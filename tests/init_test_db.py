#
# FIXME: for some reason XHTML content is still not being stored into DS...
#
from collections import namedtuple
import logging
import os
from time import sleep
# Third-party imports
from lxml import etree
# Project imports
from model import MFC, OGV, Kompleks, Service, Document, DocumentToService, db


Reference = namedtuple(
    'Reference', ['refd_kind', 'refd_field', 'type'])


class TestDbInitException(BaseException):
    pass


class TextGetter(object):
    """
    Has to be initialized with XML node (etree.Element). Use it to retrieve
    node attrs or  contents -- as plain text, serialized XHTML or None, if it
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
    

def get_entity(kind, by, value, key_only=False):
    q = kind.all()
    q.filter(u'{} ='.format(by), value)
    result = q.get()
    if result is None:
        raise TestDbInitException(
            u'Entity with {} == {} is not found for kind {}'.format(
                by, value, kind).encode("utf-8"))
    else:
        return result if not key_only else result.key()


def write_to_ref_dict(ref_node, ref_dict):
    tg = TextGetter(ref_node)
    ref_dict[tg.name] = Reference(tg.refd_kind, tg.refd_field, tg.attr("type"))


def make_new_entity(entity_class, entity_init_kwargs):
    new_entity = entity_class(**entity_init_kwargs)
    new_entity.put()
    sleep(0.1)




# A whole lot of unsafe things are happening in this parsing routine. But
# since nobody except for me is having access to test_data.mml, I don't care.
def init_test_db(from_console=False):
    parser = etree.XMLParser(remove_comments=True)
    file_path = os.path.join(os.path.dirname(__file__), "test_data.xml")
    root = etree.parse(file_path, parser).getroot()

    for kind_node in root:
        entity_class = eval(kind_node.tag)
        ref_dict = {}

        for _kind_node_sub in kind_node:
            entity_init_kwargs = {}

            if _kind_node_sub.tag == 'reference':
                write_to_ref_dict(_kind_node_sub, ref_dict)
            else:
                instance_node = _kind_node_sub
                for property_node in instance_node:
                    property_name = property_node.tag
                    property_class = type(getattr(entity_class, property_name))
                    raw_value = TextGetter(property_node).get_text()
                    ref_entry = ref_dict.get(property_name)

                    if property_class is db.IntegerProperty:
                        value_to_store = int(raw_value)
                    elif property_class is db.BooleanProperty:
                        value_to_store = bool(raw_value)
                    # Property is either db.ReferenceProperty or
                    # db.ListProperty
                    elif ref_entry is not None:

                        refd_kind = eval(ref_entry.refd_kind)
                        f_kwargs = dict(kind=refd_kind,
                                        by=ref_entry.refd_field)
                        if ref_entry.type == 'to_one':
                            f_kwargs['value'] = raw_value
                            value_to_store = get_entity(**f_kwargs)
                        elif ref_entry.type == 'to_many':
                            value_to_store = []
                            for property_sub in property_node:
                                f_kwargs['value'] = TextGetter(
                                    property_sub).get_text()
                                f_kwargs['key_only'] = True
                                value_to_store.append(get_entity(**f_kwargs))
                        else:
                            raise TestDbInitException(
                                "Unknown reference type: {}".format(
                                    ref_entry.type))
                    # Property is db.StringProperty, db.TextProperty or other
                    else:
                        value_to_store = raw_value
                    entity_init_kwargs[property_name] = value_to_store

                make_new_entity(entity_class, entity_init_kwargs)
