# coding=utf-8
from __future__ import unicode_literals
import os
import unittest
# Third-party imports
from google.appengine.ext import testbed
import json
import webtest
# Project imports
from db_tools import initialize_datastore
from main import app
from models import Document


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
        try:
            self.assertNotIn(u'Государственная регистрация рождения ребенка',
                             services_page.testbody)
        except:
            pass
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
