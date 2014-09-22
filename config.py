# coding=utf-8
from collections import OrderedDict
import os
# Third-party imports
from jinja2 import Environment, FileSystemLoader as FSLoader
from google.appengine.ext.ndb import Key

# Patching
OrderedDict.index = lambda self, item: self.keys().index(item)

# OrderedDicts are used where order is important.
CFG = {
    # handlers configuration
    'JINJA2_ENV': Environment(
        autoescape=True,
        loader=FSLoader(os.path.join(os.path.dirname(__file__), 'templates'))
    ),

    # db_tools configuration
    'PATH_TO_INIT_FILE': 'init/init_data.xml',
    'ANCESTOR': Key('app', 'kompleks'),  # Application-wide ancestor key

    # datastore and models configuration
    # enumerations
    'ORIGINAL_SUPPLY_TYPE': OrderedDict([
        ('demonstrate', u'Возвращается после приема документов'),
        ('return_with_result', u'Возвращается после предоставления услуги'),
        ('no_return', u'Не возвращается')
    ]),
    'COUNT_METHOD': {
        'one_for_all': u'Один экземпляр на комплекс',
        'per_service': u'Один экземпляр на услугу',
        'per_ogv': u'Один экземпляр на ведомство'
    },
    'RAW_REST_TREE': None  # TODO: fill this one out
}