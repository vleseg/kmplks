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
        pass

    def test_api_entity(self):
        pass

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()
