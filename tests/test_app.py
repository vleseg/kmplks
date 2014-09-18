# coding=utf-8
from __future__ import unicode_literals
import os
import unittest
# Third-party imports
from google.appengine.ext import testbed
import json
import webtest
# Project imports
from db_tools import initialize_datastore, by_property
from main import app


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
        # Authentication.
        # admin_login_form = self.testapp.get('/admin').form
        # admin_login_form['admin'] = True
        # admin_login_form.submit()

        res = self.testapp.get('/admin/api/list?kind=Service')

        self.assertEqual(res.status_int, 200)

        res_list = json.loads(res.body)

        # Test schema (fields presence)
        services = [
            u'Государственная регистрация рождения ребенка',
            u'Регистрация по месту жительства',
            u'Ежемесячное пособие на ребенка',
            u'Выдача нагрудного знака и удостоверения многодетной семьи',
            u'Единовременное пособие при рождении ребенка',
            u'Предоставление земельного участка многодетной семье'
        ]

        self.assertItemsEqual(('value', 'id'), res_list[0])
        self.assertEqual(len(res_list), 6)

        self.assertItemsEqual(services, [item['value'] for item in res_list])

    def test_api_entity(self):
        entity = by_property('Service',
                             'name',
                             u'Государственная регистрация рождения ребенка',
                             key_only=False)
        urlsafe = entity.urlsafe()

        res_json = self.testapp.get('/admin/api/entity?id={}'.format(urlsafe))

        self.assertEqual(res_json.status_int, 200)
        self.maxDiff = None
        expected = {
            u'_id': unicode(urlsafe),
            u'_kind': u'Услуга',
            u'_use_as_name': u'name',
            u'name': {
                u'type': u'plain', u'label': u'Название',
                u'value': u'Государственная регистрация рождения ребенка'},
            u'short_description': {
                u'type': u'plain_or_html',
                u'label': u'Краткое описание условий предоставления услуги',
                u'value': u'Только для родителей, состоящих в браке и имеющих '
                          u'регистрацию по месту обращения (или если ребенок '
                          u'родился по месту обращения)'},
            u'kb_id': {
                u'type': u'int', u'value': 244,
                u'label': u'ID в Базе знаний МФЦ'},
            u'prerequisite_description': {
                u'type': u'plain',
                u'value': u'Уже есть свидетельство о рождении',
                u'label': u'При каких условиях получение услуги не требуется?'
            },
            u'max_days': {
                u'type': u'int', u'value': 0,
                u'label': u'Максимальный срок предоставления (календарные '
                          u'дни)'},
            u'max_work_days': {
                u'type': u'int', u'value': 4,
                u'label': u'Максимальный срок предоставления (рабочие дни)'
            },
            u'ogv': {
                u'type': u'entity', u'kind': u'OGV', u'value': u'УЗАГС',
                u'label': u'Ответственное ведомство'},
            u'containing_komplekses': {
                u'type': u'multi_entity', u'kind': u'Kompleks',
                u'value': u'Рождение ребенка',
                u'label': u'Комплексы, в которые входит услуга'}}

        self.assertDictEqual(json.loads(res_json.body), expected)

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()
