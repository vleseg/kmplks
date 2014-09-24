# coding=utf-8
from __future__ import unicode_literals
import os
import unittest
# Third-party imports
from google.appengine.ext import ndb, testbed
import json
import webtest
# Project imports
from datastore_init import initialize_datastore
from main import app
from models import Document, Service, Kompleks, MFC, from_urlsafe, OGV


class KompleksTestCase(unittest.TestCase):
    def assertUniqueSubstring(self, sub, s):
        self.assertIn(sub, s)
        # If it doesn't fail ->
        new_s = s[s.index(sub): + len(sub)]
        if sub in new_s:
            raise AssertionError(
                "'{}' occurs more than once in '{}'".format(sub, s))

    def assertAllIn(self, seq, s):
        for sub in seq:
            self.assertIn(sub, s)

    def assertAllInAndUnique(self, seq, s):
        for sub in seq:
            self.assertUniqueSubstring(sub, s)

    def assertAllNotIn(self, seq, s):
        for sub in seq:
            self.assertNotIn(sub, s)

@unittest.skip
class AppTest(KompleksTestCase):
    @classmethod
    def setUpClass(cls):
        cls.testapp = webtest.TestApp(app)
        cls.testbed = testbed.Testbed()
        cls.testbed.activate()
        cls.testbed.init_datastore_v3_stub()
        cls.testbed.init_memcache_stub()
        path_to_test_data = os.path.join(os.path.dirname(__file__),
                                         'test_data.xml')
        initialize_datastore(path_to_test_data)

    # Misc testing
    def test_backref_query(self):
        backref_info = Kompleks.backref_info()
        self.assertEqual(backref_info, {
            'Service': ['containing_komplekses', 'related_komplekses'],
            'DocumentToService': ['kompleks']})

        test_srv = Service.by_property(
            u'name', u'Государственная регистрация рождения ребенка',
            key_only=False)

        dts_items = list(test_srv.backref_query('DocumentToService', 'service'))

        self.assertEqual(len(dts_items), 7)


    # Testing handlers.
    def test_standard_routine(self):
        start_page = self.testapp.get('/')
        self.assertEqual(start_page.status_int, 200)
        self.assertAllInAndUnique(
            (u'Рождение ребенка', u'МФЦ г. Якутск', u'МФЦ г. Нюрба'),
            start_page.testbody
        )

        prerequisites_page = start_page.click(
            description=u'Рождение ребенка').follow()
        self.assertEqual(prerequisites_page.status_int, 200)
        self.assertAllInAndUnique(
            (u'Рождение ребенка', u'Уже есть свидетельство о рождении',
             u'Уже есть прописка'),
            prerequisites_page.testbody
        )

        id_to_use = None
        for cell in prerequisites_page.html.findAll('td'):
            if u'Уже есть свидетельство о рождении' in cell.text:
                id_to_use = cell.label['for']
        services_page = self.testapp.post(
            '/prerequisites', {'prerequisite': id_to_use}).follow()

        srv_names = [
            u'Регистрация по месту жительства',
            u'Ежемесячное пособие на ребенка',
            u'Выдача нагрудного знака и удостоверения многодетной семьи'
        ]
        self.assertEqual(services_page.status_int, 200)
        self.assertNotIn(u'Государственная регистрация рождения ребенка',
                         services_page.testbody)
        self.assertAllInAndUnique(srv_names + [u'Рождение ребенка'],
                                  services_page.testbody)

        ids_to_use = []
        for cell in services_page.html.findAll('td'):
            if cell.text and cell.text.strip() in srv_names:
                ids_to_use.append(cell.label['for'])
        req_params = {'service': ids_to_use}
        result_page = self.testapp.post('/services', req_params).follow()

        self.assertAllNotIn((
            u'Заявление о рождении, форма №1',
            u'Заявление о назначении единовременного пособия при рождении '
            u'ребенка',
            u'Заявление о включении в список нуждающихся в получении '
            u'земельного участка'
        ), result_page.testbody)
        self.assertAllInAndUnique((
            u'Заявление о выдаче нагрудного знака и удостоверения многодетной '
            u'семьи',
            u'Заявление о регистрации по месту жительства, форма №6',
            u'Заявление о назначении ежемесячного пособия на ребенка'
        ), result_page.testbody)

    def test_api_list(self):
        response = self.testapp.get('/admin/api/Service/entities')

        self.assertEqual(response.status_int, 200)
        response_obj = json.loads(response.body)

        self.assertEqual(response_obj['kind'], u'Услуга')
        self.assertEqual(response_obj['kind_plural'], u'Услуги')
        self.assertEqual(len(response_obj['items']), 6)

    def test_api_fields(self):
        response = self.testapp.get('/admin/api/Service/fields')

        self.assertEqual(response.status_int, 200)
        response_obj = json.loads(response.body)

        self.assertEqual(response_obj['kind'], u'Услуга')
        self.assertEqual(response_obj['kind_plural'], u'Услуги')

        self.assertAllIn(response_obj['fields'], [
            {'name': 'id', 'type': 'int', 'label': u'ID'},
            {'name': 'name', 'type': 'plain', 'label': u'Название'},
            {'name': 'short_description', 'type': 'rich',
             'label': u'Краткое описание'},
            {'name': 'kb_id', 'type': 'int', 'label': u'ID в Базе знаний МФЦ'},
            {'name': 'prerequisite_description', 'type': 'plain',
             'label': u'При каком условии надобность в услуге отпадает?'},
            {'name': 'max_days', 'type': 'int',
             'label': u'Максимальный срок (календарные дни)'},
            {'name': 'max_work_days', 'type': 'int',
             'label': u'Максимальный срок (рабочие дни)'},
            {'name': 'terms_description', 'type': 'plain',
             'label': u'Примечание к срокам предоставления услуги'},
            {'name': 'ogv', 'type': 'ref', 'kind': 'OGV',
             'label': u'Ответственное ведомство'},
            {'name': 'containing_komplekses', 'type': 'multi_ref',
             'kind': 'Kompleks',
             'label': u'Комплексы, в которые входит услуга'},
            {'name': 'related_komplekses', 'type': 'multi_ref',
             'kind': 'Kompleks',
             'label': u'Комплексы, к которым услугу можно отнести'},
            {'name': 'dependencies', 'type': 'multi_ref', 'kind': 'Service',
             'label': u'Какие услуги нужно получить предварительно?'}
        ])

    def test_api_entity(self):
        test_doc = Document.by_property(
            'name', u'Заявление о регистрации по месту жительства, форма №6',
            key_only=False)

        response = self.testapp.get(
            '/admin/api/entities/' + test_doc.urlsafe())

        self.assertEqual(response.status_int, 200)
        response_obj = json.loads(response.body)

        self.assertAllIn(response_obj['choices'].keys(),
                         ['COUNT_METHOD', 'ORIGINAL_SUPPLY_TYPE'])
        self.assertEqual(response_obj['kind'], u'Документ')
        self.assertEqual(response_obj['kind_plural'], u'Документы')
        self.assertEqual(
            response_obj['label'],
            u'Заявление о регистрации по месту жительства, форма №6')
        self.assertAllIn(response_obj['fields'], [
            {'name': 'id', 'type': 'int', 'label': u'ID', 'value': 8},
            {'name': 'name', 'type': 'plain', 'label': u'Название',
             'value': u'Заявление о регистрации по месту жительства, форма №6'},
            {'name': 'description', 'type': 'rich',
             'label': u'Условия предоставления',
             'value': u'Форма заявления предоставляется консультантом МФЦ.'},
            {'name': 'o_count_method', 'type': 'enum',
             'label': u'Метод подсчета оригиналов', 'value': 'per_service'},
            {'name': 'c_count_method', 'type': 'enum',
             'label': u'Метод подсчета копий', 'value': 'per_service'},
            {'name': 'n_originals', 'type': 'int',
             'label': u'Количество оригиналов', 'value': 1},
            {'name': 'n_copies', 'type': 'int', 'label': u'Количество копий',
             'value': 0},
            {'name': 'o_supply_type', 'type': 'enum',
             'label': u'Возвращается ли оригинал заявителю?',
             'value': 'no_return'},
            {'name': 'is_a_paper_document', 'type': 'bool',
             'label': u'Это физический документ?', 'value': True},
            {'name': 'doc_class', 'type': 'ref', 'label': u'Класс документа',
             'value': u'Заявления', 'kind': 'DocClass'}
        ])

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()


class DatastoreModTest(KompleksTestCase):
    @classmethod
    def setUpClass(cls):
        cls.testapp = webtest.TestApp(app)
        cls.testbed = testbed.Testbed()
        cls.testbed.activate()
        cls.testbed.init_datastore_v3_stub()
        cls.testbed.init_memcache_stub()
        cls.path_to_test_data = os.path.join(
            os.path.dirname(__file__), 'test_data.xml')

    def setUp(self):
        initialize_datastore(self.path_to_test_data)

    def test_delete_entity(self):
        services = Service.query().fetch()
        srv_to_dts = [
            {'object': s,
             'len_before': len(
                 s.backref_query('DocumentToService', 'service').fetch())} for
            s in services
        ]

        test_doc = Document.by_property(
            'name', u'Документ, удостоверяющий личность заявителя',
            key_only=False)
        test_mfc = MFC.by_property('name', u'МФЦ г. Нюрба', key_only=False)
        testdoc_urlsafe = test_doc.urlsafe()
        testmfc_urlsafe = test_mfc.urlsafe()

        self.testapp.delete('/admin/api/entities/' + testdoc_urlsafe)
        self.testapp.delete('/admin/api/entities/' + testmfc_urlsafe)

        for item in srv_to_dts:
            s = item['object']
            self.assertEqual(
                item['len_before'] - 1,
                len(s.backref_query('DocumentToService', 'service').fetch()))

        self.assertEqual(len(MFC.query().fetch()), 1)
        birth_kompleks = Kompleks.by_property(
            'name', u'Рождение ребенка', key_only=False)
        self.assertEqual(len(birth_kompleks.mfcs), 1)

        response_after = self.testapp.get(
            '/admin/api/entities/' + testdoc_urlsafe, expect_errors=True)

        self.assertEqual(response_after.status_int, 404)

    def test_modify_entity(self):
        test_srv = Service.by_property(
            'name', u'Предоставление земельного участка многодетной семье',
            key_only=False
        )
        required_srv = Service.by_property(
            'name', u'Регистрация по месту жительства', key_only=False
        )
        kmplks_to_remove = Kompleks.by_property(
            'name', u'Рождение ребенка', key_only=False)

        test_srv.prerequisite_description = u"это нужно будет удалить"
        test_srv.put()

        req_data = [
            {'name': 'short_description', 'value': u'тест тест тест'},
            {'name': "dependencies", 'edits': [
                {'values': [required_srv.urlsafe()], 'method': 'add'}]},
            {'name': 'related_komplekses', 'edits': [
                {'values': [kmplks_to_remove.urlsafe()],
                 'method': 'subtract'}]},
            {'name': 'prerequisite_description', 'value': None}]
        req_url = '/admin/api/entities/' + test_srv.urlsafe()

        response = self.testapp.put_json(req_url, req_data)
        self.assertEqual(response.status_int, 200)

        test_srv = from_urlsafe(test_srv.urlsafe())

        self.assertEqual(test_srv.prerequisite_description, None)
        self.assertNotIn(
            from_urlsafe(kmplks_to_remove.urlsafe(),key_only=True),
            test_srv.related_komplekses)
        self.assertIn(from_urlsafe(required_srv.urlsafe(), key_only=True),
                      test_srv.dependencies)
        self.assertEqual(test_srv.short_description, u'тест тест тест')

    def test_new_entity(self):
        dependencies = [
            Service.by_property('name', n, key_only=True) for n in
            (u'Государственная регистрация рождения ребенка',
             u'Регистрация по месту жительства')
        ]
        kmplks = Kompleks.by_property(
            'name', u'Рождение ребенка', key_only=False)
        ogv = OGV.by_property('short_name', u'УЗАГС', key_only=False)

        req_data = [
            {'name': 'id', 'value': 100500},
            {'name': 'name', 'value': u'Тестовая услуга'},
            {'name': 'short_description',
             'value': u'Короткое тестовое описание тестовой услуги'},
            {'name': 'kb_id', 'value': 100500},
            {'name': 'prerequisite_description',
             'value': u'Тестовое описание условий, при которых нужда в '
                      u'тестовой услуге отпадает'},
            {'name': 'max_days', 'value': 10},
            {'name': 'max_work_days', 'value': 100},
            {'name': 'terms_description',
             'value': u'Тестовый комментарий к срокам предоставления тестовой '
                      u'услуги'},
            {'name': 'ogv', 'value': ogv.urlsafe()},
            {'name': 'containing_komplekses', 'value': [kmplks.urlsafe()]},
            {'name': 'dependencies',
             'value': [d.urlsafe() for d in dependencies]}
        ]
        req_url = '/admin/api/entities'

        response = self.testapp.post_json(req_url, req_data)
        self.assertEqual(response.status_int, 200)

        test_srv = from_urlsafe(json.loads(response.body).get('id'))

        self.assertEqual(test_srv.id, 100500)
        self.assertEqual(test_srv.name, u'Тестовая услуга')
        self.assertEqual(
            test_srv.short_description,
            u'Короткое тестовое описание тестовой услуги'
        )
        self.assertEqual(test_srv.kb_id, 100500)
        self.assertEqual(
            test_srv.prerequisite_descrption,
            u'Тестовое описание условий, при которых нужда в тестовой услуге '
            u'отпадает'
        )
        self.assertEqual(test_srv.max_days, 10)
        self.assertEqual(test_srv.max_work_days, 100)
        self.assertEqual(
            test_srv.terms_description,
            u'Тестовый комментарий к срокам предоставления тестовой услуги'
        )
        self.assertEqual(test_srv.ogv, ogv)
        self.assertEqual(test_srv.containing_komplekses, [kmplks])
        self.assertAllIn(test_srv.dependencies, [dependencies])

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()
