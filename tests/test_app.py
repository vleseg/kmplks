# coding=utf-8
import os
import unittest
# Third-party imports
from google.appengine.ext import testbed
import webtest
# Project imports
from db_tools import bulk_load
from main import app


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testapp = webtest.TestApp(app)
        cls.testbed = testbed.Testbed()
        cls.testbed.activate()
        cls.testbed.init_datastore_v3_stub()
        cls.testbed.init_memcache_stub()
        bulk_load()

    def insert_patch(self):
        path = os.path.join(os.path.dirname(__file__), 'test_patch_insert.xml')
        with open(path, 'r') as f:
            xml = f.read()
        bulk_load(load_mode='patch', xml=xml)

    def test_standard_routine(self):
        start_page = self.testapp.get('/')
        self.assertEqual(start_page.status_int, 200)
        for assert_str in (u'Рождение ребенка', u'МФЦ г. Якутск',
                           u'МФЦ г. Нюрба'):
            self.assertIn(assert_str, start_page)

        prerequisites_page = start_page.click(
            description=u'Рождение ребенка').follow()
        self.assertEqual(prerequisites_page.status_int, 200)
        for assert_str in (u'Рождение ребенка',
                           u'Уже есть свидетельство о рождении',
                           u'Уже есть прописка'):
            self.assertIn(assert_str, prerequisites_page)

        id_to_use = None
        for cell in prerequisites_page.html.findAll('td'):
            if u'Уже есть свидетельство о рождении' in cell.get_text():
                id_to_use = cell.label['for']
        services_page = self.testapp.post(
            '/prerequisites', {'prerequisite': id_to_use}).follow()

        srv_names = [
            u'Регистрация по месту жительства',
            u'Ежемесячное пособие на ребенка',
            u'Выдача нагрудного знака и удостоверения многодетной семьи'
        ]
        self.assertEqual(services_page.status_int, 200)
        for assert_str in [u'Рождение ребенка'] + srv_names:
            self.assertIn(assert_str, services_page)

        ids_to_use = []
        for cell in services_page.html.findAll('td'):
            if cell.get_text().strip() in srv_names:
                ids_to_use.append(cell.label['for'])
        req_params = {'service': ids_to_use}
        result_page = self.testapp.post('/services', req_params).follow()
        doc_names = [
            u'Заявление о выдаче нагрудного знака и удостоверения многодетной '
            u'семьи',
            u'Заявление о регистрации по месту жительства, форма №6',
            u'Заявление о назначении ежемесячного пособия на ребенка'
        ]
        for assert_str in doc_names:
            self.assertIn(assert_str, result_page)

    def test_insert_patching(self):
        self.insert_patch()

        start_page = self.testapp.get('/')
        for assert_str in (u'Дурацкая походка', u'МФЦ г. Якутск',
                           u'МФЦ г. Нюрба', u'МФЦ с. Намцы'):
            self.assertIn(assert_str, start_page)

        prerequisites_page = start_page.click(
            description=u'Дурацкая походка').follow()
        services_page = self.testapp.post('/prerequisites').follow()
        srv_names = [
            u'Лицензирование дурацкой походки',
            u'Выдача выписки из реестра дурацких походок'
        ]
        for assert_str in [u'Дурацкая походка'] + srv_names:
            self.assertIn(assert_str, services_page)

        ids_to_use = []
        for cell in services_page.html.findAll('td'):
            if cell.get_text().strip() in srv_names:
                ids_to_use.append(cell.label['for'])
        req_params = {'service': ids_to_use}
        result_page = self.testapp.post('/services', req_params).follow()
        doc_names = [
            u'Заявление о лицензировании дурацкой походки',
            u'Заявление о выдаче выписки из реестра дурацких походок',
            u'Документ, удостоверяющий личность заявителя'
        ]
        for assert_str in doc_names:
            self.assertIn(assert_str, result_page)

    def test_delete_patching(self):
        self.insert_patch()

        path = os.path.join(os.path.dirname(__file__), 'test_patch_delete.xml')
        with open(path, 'r') as f:
            xml = f.read()
        bulk_load(load_mode='patch', xml=xml)

        start_page = self.testapp.get('/')
        self.assertNotIn(u'Дурацкая походка', start_page)

    def test_update_patching(self):
        path = os.path.join(os.path.dirname(__file__), 'test_patch_update.xml')
        with open(path, 'r') as f:
            xml = f.read()
        bulk_load(load_mode='patch', xml=xml)

        start_page = self.testapp.get('/')
        for assert_str in (u'Рождение ребенка', u'МФЦ г. Якутск',
                           u'МФЦ г. Нюрба', u'МФЦ с. Намцы'):
            self.assertIn(assert_str, start_page)

        prerequisites_page = start_page.click(
            description=u'Рождение ребенка').follow()
        services_page = self.testapp.post('/prerequisites').follow()
        self.assertNotIn(u'Регистрация по месту жительства', services_page)
        self.assertIn(u'Регистрация по месту пребывания', services_page)

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()