# coding=utf-8
import os
# Third-party imports
from jinja2 import Environment, FileSystemLoader as FSLoader
from google.appengine.ext.ndb import Key
CFG = {
    # handlers configuration
    'JINJA2_ENV': Environment(
        autoescape=True,
        loader=FSLoader(os.path.join(os.path.dirname(__file__), 'templates'))
    ),

    # db_tools configuration
    'PATH_TO_INIT_FILE': 'init/init_data.xml',

    # datastore and models configuration
    'ORIGINAL_SUPPLY_TYPE': ('demonstrate', 'return_with_result', 'no_return'),
    'COUNT_METHOD': ('one_for_all', 'per_service', 'per_ogv'),
    'ANCESTOR': Key('app', 'kompleks'),  # Application-wide ancestor key
    # Main human-readable property will be used in admin interface as a key and
    # field to search, when displaying lists of entities; this entry is being
    # validated at ndb import time in main app
    # 'human readable' means, that numeric id or datastore key cannot be used!
    'KEY_HR_PROPERTY': {
        'DocClass': 'value',
        'MFC': 'name',
        'Kompleks': 'name',
        'OGV': 'short_name',
        'Service': 'name',
        'Document': 'name',
        'DocumentToService': None  # will be skipped on validation time
    },
    # Translations
    'RUSSIAN': {
        '_enum': {
            'ORIGINAL_SUPPLY_TYPE': {
                'demonstrate': u'Возвращается после приема документов',
                'return_with_result':
                    u'Возвращается после предоставления услуги',
                'no_return': u'Не возвращается'
            },
            'COUNT_METHOD': {
                'one_for_all': u'Один экземпляр на комплекс',
                'per_service': u'Один экземпляр на услугу',
                'per_ogv': u'Один экземпляр на ведомство'
            }
        },
        'DocClass': {
            '_name': u'Класс документа',
            '_name_plural': u'Классы документов',
            'sort_key': u'Ключ сортировки',
            "value": u'Имя класса'
        },
        'MFC': {
            '_name': u'МФЦ',
            '_name_plural': u'МФЦ',
            'name': u'Название'
        },
        'Kompleks': {
            '_name': u'Комплексная услуга',
            '_name_plural': u'Комплексные услуги',
            'name': u'Название',
            'mfcs': u'В каких МФЦ можно получить?'
        },
        'OGV': {
            '_name': u'Ведомство',
            '_name_plural': u'Ведомства',
            'name': u'Название',
            'short_name': u'Краткое название'
        },
        'Service': {
            '_name': u'Услуга',
            '_name_plural': u'Услуги',
            'name': u'Название',
            'short_description':
                u'Краткое описание условий предоставления услуги',
            'kb_id': u'ID в Базе знаний МФЦ',
            'prerequisite_description':
                u'При каких условиях получение услуги не требуется?',
            'max_days': u'Максимальный срок предоставления (календарные дни)',
            'max_work_days': u'Максимальный срок предоставления (рабочие дни)',
            'terms_description': u'Комментарий к срокам',
            'ogv': u'Ответственное ведомство',
            'containing_komplekses': u'Комплексы, в которые входит услуга',
            'related_komplekses': u'Комплексы, с которыми связана услуга',
            'dependencies': u'Предварительно необходимые услуги'
        },
        'Document': {
            '_name': u'Документ',
            '_name_plural': u'Документы',
            'name': u'Название',
            'description': u'Условия предоставления',
            'o_count_method': u'Метод подсчета оригиналов',
            'c_count_method': u'Метод подсчета копий',
            'o_supply_type': u'Возвращается ли оригинал завяителю?',
            "n_originals": u'Количество оригиналов',
            'n_copies': u'Количество копий',
            'is_a_paper_document': {
                '_name': u'Это физический документ?',
                '_true': u'Да',
                '_false': u'Нет'
            },
            'doc_class': u'Класс документа'
        },
        'DocumentToService': None
        # DocumentToService is never treated as a distinct property in admin
        # context.
    }
}