# coding=utf-8
from __future__ import unicode_literals
import os
import unittest
# Third-party imports
from google.appengine.ext import testbed
from google.appengine.ext import ndb
import json
import webtest
# Project imports
from config import CFG
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
    # TODO: do more misc testing here
    def test_backref_query(self):
        backref_info = Kompleks.backref_info()
        self.assertEqual(backref_info, {
            'Service': ['containing_komplekses', 'related_komplekses'],
            'DocumentToService': ['kompleks']})

        test_srv = Service.by_property(
            u'name', u'Государственная регистрация рождения ребенка')

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
        # TODO: test api list refetch after items were added/deleted
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
        # TODO: test api refetch after api was modified/deleted
        test_doc = Document.by_property(
            'name', u'Заявление о регистрации по месту жительства, форма №6')

        response = self.testapp.get('/admin/api/entities/' + test_doc.urlsafe())

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
        cls.testapp.post(
            '/admin/adduser',
            {'username': 'test', 'email': 'test', 'password': 'test'})
        cls.testapp.post(
            '/admin/login', {'username': 'test', 'password': 'test'})

    def setUp(self):
        initialize_datastore(self.path_to_test_data)

    def test_delete_entity_simple(self):
        new_mfc = MFC(name='test', id=-1)
        new_mfc.put()
        new_mfc_key = new_mfc.key

        self.testapp.delete('/admin/api/entities/' + new_mfc_key.urlsafe())

        self.assertIsNone(new_mfc_key.get())

    def test_delete_entity_cascade(self):
        # TODO: test erroneous cascade delete of entities, that are referenced
        # as a required property.
        initial_dts_count = [
            {'service': s,
             'count': len(
                 s.backref_query('DocumentToService', 'service').fetch())}
            for s in Service.query().fetch()
        ]

        # == Testing cascade delete of references ==
        test_mfc = MFC.by_property('name', u'МФЦ г. Нюрба')
        testmfc_urlsafe = test_mfc.urlsafe()

        self.testapp.delete('/admin/api/entities/' + testmfc_urlsafe)

        # Only one MFC entity is left.
        self.assertEqual(len(MFC.query().fetch()), 1)
        # Only one MFC entity is now referenced by the sole kompleks in test
        # data.
        kompleks = Kompleks.by_property('name', u'Рождение ребенка')
        self.assertEqual(len(kompleks.mfcs), 1)

        # == Testing cascade delete of linked DocumentToService entities ==
        test_doc = Document.by_property(
            'name', u'Документ, удостоверяющий личность заявителя')
        testdoc_urlsafe = test_doc.urlsafe()

        self.testapp.delete('/admin/api/entities/' + testdoc_urlsafe)

        # All DocumentToService entities linked to the deleted document are gone
        # as well.
        for item in initial_dts_count:
            s = item['service']
            self.assertEqual(
                item['count'] - 1,
                len(s.backref_query('DocumentToService', 'service').fetch()))

    def test_modify_entity(self):
        # TODO: test erroneous cases (required field deleted, field type
        # mismatch etc.)
        test_srv = Service.by_property(
            'name', u'Предоставление земельного участка многодетной семье')
        required_srv = Service.by_property(
            'name', u'Регистрация по месту жительства')
        kmplks_to_remove = Kompleks.by_property('name', u'Рождение ребенка')

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
        # TODO: test erroneous cases (required fields left blank, field type
        # mismatch etc.)
        dependencies = [
            Service.by_property('name', n, key_only=True) for n in
            (u'Государственная регистрация рождения ребенка',
             u'Регистрация по месту жительства')
        ]
        kompleks = Kompleks.by_property(
            'name', u'Рождение ребенка', key_only=True)
        ogv = OGV.by_property('short_name', u'УЗАГС', key_only=True)

        req_data = [
            {'name': 'id', 'value': -1},
            {'name': 'name', 'value': u'Тестовая услуга'},
            {'name': 'short_description',
             'value': u'Короткое тестовое описание тестовой услуги'},
            {'name': 'kb_id', 'value': -1},
            {'name': 'prerequisite_description',
             'value': u'Тестовое описание условий, при которых нужда в '
                      u'тестовой услуге отпадает'},
            {'name': 'max_days', 'value': 10},
            {'name': 'max_work_days', 'value': 100},
            {'name': 'terms_description',
             'value': u'Тестовый комментарий к срокам предоставления тестовой '
                      u'услуги'},
            {'name': 'ogv', 'value': ogv.urlsafe()},
            {'name': 'containing_komplekses', 'value': [kompleks.urlsafe()]},
            {'name': 'dependencies',
             'value': [d.urlsafe() for d in dependencies]}
        ]
        req_url = '/admin/api/Service/entities'

        response = self.testapp.post_json(req_url, req_data)
        self.assertEqual(response.status_int, 200)

        test_srv = from_urlsafe(json.loads(response.body).get('id'))

        self.assertEqual(
            (test_srv.id, test_srv.name, test_srv.short_description,
             test_srv.kb_id, test_srv.prerequisite_description,
             test_srv.max_days, test_srv.max_work_days,
             test_srv.terms_description, test_srv.ogv,
             test_srv.containing_komplekses, test_srv.dependencies),
            (-1, u'Тестовая услуга',
             u'Короткое тестовое описание тестовой услуги', -1,
             u'Тестовое описание условий, при которых нужда в тестовой услуге '
             u'отпадает', 10, 100,
             u'Тестовый комментарий к срокам предоставления тестовой услуги',
             ogv, [kompleks], dependencies)
        )

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()


def response_title(response):
    return response.html('title')[0].get_text().strip()


class AuthTest(KompleksTestCase):
    @classmethod
    def setUpClass(cls):
        cls.testapp = webtest.TestApp(app)
        cls.testbed = testbed.Testbed()
        cls.testbed.activate()
        cls.testbed.init_datastore_v3_stub()
        cls.testbed.init_memcache_stub()
        cls.path_to_test_data = os.path.join(
            os.path.dirname(__file__), 'test_data.xml')

    def test_new_user(self):
        post_params = {
            'username': 'test', 'email': 'test@example.com', 'password': '123'}
        response = self.testapp.post(
            '/admin/adduser', params=post_params)

        self.assertEqual(200, response.status_int)
        self.assertAllIn(
            [u'Отлично!', u'Пользователь test успешно создан.'],
            response.html.get_text())

        response = self.testapp.post(
            '/admin/adduser', params=post_params)
        self.assertEqual(200, response.status_int)
        self.assertAllIn(
            [u'Ошибка!', u'Пользователь с именем test уже существует.'],
            response.html.get_text())

    def test_user_required(self):
        response = self.testapp.get('/admin')
        # Must redirect to login page.
        self.assertEqual(response.status_int / 100, 3)
        self.assertIn(u'Вход в приложение', response_title(response.follow()))

    def test_login(self):
        # Register test user.
        post_params = {
            'username': 'testuser', 'email': 'test@example.com',
            'password': '123'}
        self.testapp.post('/admin/adduser', params=post_params)

        # Login as test user.
        post_params = {'username': 'testuser', 'password': '123'}
        response = self.testapp.post(
            '/admin/login', params=post_params).follow()
        self.assertEqual(response.status_int, 200)
        self.assertIn(u'Список объектов', response_title(response))
        self.assertIn('testuser', response)

    def tearDown(self):
        self.testapp.reset()

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()