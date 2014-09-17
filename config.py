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

    # Main human-readable property will be used in admin interface as a key and
    # field to search, when displaying lists of entities; this entry is being
    # validated at ndb import time in main app
    # 'human readable' means, that numeric id or datastore key cannot be used!
    'MODEL_DISPLAY_PARAMS': OrderedDict([
        ('DocClass', {
            # Kind name in Russian
            'ru_name': u'Класс документа',
            # Kind name in Russian (plural)
            'ru_name_plural': u'Классы документов',
            # Russian names (or labels) for properties
            'ru_name_prop': {
                'sort_key': u'Ключ сортировки',
                "value": u'Имя класса'
            },
            # Field to use to display entities of this kind in lists
            'repr_field': 'value'
        }),
        ('MFC', {
            'ru_name': u'МФЦ',
            'ru_name_plural': u'МФЦ',
            'ru_name_prop': {
                'name': u'Название',
            },
            'repr_field': 'name'
        }),
        ('Kompleks', {
            'ru_name': u'Комплексная услуга',
            'ru_name_plural': u'Комлпексные услуги',
            'ru_name_prop': OrderedDict([
                ('name', u'Название'),
                ('mfcs', u'В каких МФЦ можно получить?')
            ]),
            'repr_field': 'name'
        }),
        ('OGV', {
            'ru_name': u'Ведомство',
            'ru_name_plural': u'Ведомства',
            'ru_name_prop': OrderedDict([
                ('name', u'Название'),
                ('short_name', u'Краткое название')
            ]),
            'repr_field': 'short_name',
        }),
        ('Service', {
            'ru_name': u'Услуга',
            'ru_name_plural': u'Услуги',
            'ru_name_prop': OrderedDict([
                ('name', u'Название'),
                ('short_description',
                 u'Краткое описание условий предоставления услуги'),
                ('kb_id', u'ID в Базе знаний МФЦ'),
                ('prerequisite_description',
                 u'При каких условиях получение услуги не требуется?'),
                ('max_days',
                 u'Максимальный срок предоставления (календарные дни)'),
                ('max_work_days',
                 u'Максимальный срок предоставления (рабочие дни)'),
                ('terms_description', u'Комментарий к срокам'),
                ('ogv', u'Ответственное ведомство'),
                (
                'containing_komplekses', u'Комплексы, в которые входит услуга'),
                ('related_komplekses', u'Комплексы, с которыми связана услуга'),
                ('dependencies', u'Предварительно необходимые услуги')
            ]),
            'repr_field': 'name'
        }),
        ('Document', {
            'ru_name': u'Документ',
            'ru_name_plural': u'Документы',
            'ru_name_prop': OrderedDict([
                ('name', u'Название'),
                ('description', u'Условия предоставления'),
                ('o_count_method', u'Метод подсчета оригиналов'),
                ('c_count_method', u'Метод подсчета копий'),
                ('o_supply_type', u'Возвращается ли оригинал завяителю?'),
                ("n_originals", u'Количество оригиналов'),
                ('n_copies', u'Количество копий'),
                ('is_a_paper_document', {
                    '_name': u'Это физический документ?',
                    '_true': u'Да',
                    '_false': u'Нет'
                }),
                ('doc_class', u'Класс документа')
            ]),
            'repr_field': 'name'
        }),
        # DocumentToService is not considered a distinct property in admin
        # context.
        ('DocumentToService', None)
    ])
}