import os
# Third-party imports
from google.appengine.ext import ndb
from lxml import etree
# Project imports
from config import CFG
import models
from tools import whoami


class DbToolsException(BaseException):
    pass


class NodeReader(object):
    """
    Has to be initialized with XML node (etree.Element). Use it to retrieve
    node contents -- as plain text, serialized XHTML or None, if it is not a
    leaf node.
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


def initialize_datastore(path_to_xml=None):
    if path_to_xml is None:  # not test mode; use init/init_data.xml
        for kind in models.iter_datastore_kinds():
            ndb.delete_multi(kind.query().iter(keys_only=True))  # clean up

        path_to_xml = os.path.join(
            os.path.dirname(__file__), CFG["PATH_TO_INIT_FILE"])

    p = etree.XMLParser(remove_comments=True)

    for kind_node in etree.parse(path_to_xml, parser=p).getroot():
        entity_kind = getattr(models, kind_node.tag)

        for item_node in kind_node:
            entity_properties = {}

            for property_node in item_node:
                property_name = property_node.tag
                property_class = getattr(entity_kind, property_name)
                reader = NodeReader(property_node)

                if whoami(property_class) == 'IntegerProperty':
                    value_to_store = reader.get_int()
                elif whoami(property_class) == 'BooleanProperty':
                    value_to_store = reader.get_bool()
                elif whoami(property_class) == 'KeyProperty':
                    referred_kind = models.kind_by_name(property_class._kind)
                    req_params = {
                        'property_': referred_kind.id, 'key_only': True
                    }
                    if property_class._repeated:
                        value_to_store = []
                        for id_ in map(int, reader.xpath('item/text()')):
                            req_params['value'] = id_
                            value_to_store.append(
                                referred_kind.by_property(**req_params))
                    else:
                        req_params['value'] = reader.get_int()
                        value_to_store = referred_kind.by_property(**req_params)
                # Property is ndb.StringProperty, ndb.TextProperty or other
                else:
                    value_to_store = reader.get_text()

                entity_properties[property_name] = value_to_store

            entity_kind.insert_or_update(entity_properties)