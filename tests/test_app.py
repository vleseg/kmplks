# coding=utf-8
import unittest
# Third-party imports
from google.appengine.ext import testbed
import webtest
# Project imports
from main import app
from init_test_db import init_test_db


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testapp = webtest.TestApp(app)
        cls.testbed = testbed.Testbed()
        cls.testbed.activate()
        cls.testbed.init_datastore_v3_stub()
        cls.testbed.init_memcache_stub()
        init_test_db()

    def test_kompleks_choice_handler(self):
        response = self.testapp.get('/')

        self.assertEqual(response.status_int, 200)
        for assert_str in (u'Рождение ребенка', u'МФЦ г. Якутск',
                           u'МФЦ г. Нюрба'):
            self.assertIn(assert_str, response)

    def test_prerequisite_choice_handler(self):
        # Choose a kompleks on start page, follow redirect.
        response = self.testapp.get('/').click(
            description=u'Рождение ребенка').follow()

        self.assertEqual(response.status_int, 200)

        for assert_str in (u'Рождение ребенка',
                           u'Уже есть свидетельство о рождении',
                           u'Уже есть прописка'):
            self.assertIn(assert_str, response)

    def test_service_choice_handler(self):
        # Choose a kompleks on start page, follow redirect.
        prereq_page_response = self.testapp.get('/').click(
            description=u'Рождение ребенка').follow()
        # Mark a prerequisite as satisfied.
        id_to_use = None
        for cell in prereq_page_response.html.findAll('td'):
            if u'Уже есть свидетельство о рождении' in cell.get_text():
                id_to_use = cell.label['for']
        # Submit, follow redirect.
        response = self.testapp.post(
            '/prerequisites', {'prerequisite': id_to_use}).follow()

        self.assertEqual(response.status_int, 200)

        kompleks_name = u'Рождение ребенка',
        contained_services_names = (
            u'Регистрация по месту жительства (Тест)',
            u'Ежемесячное пособие на ребенка (Тест)')
        related_services_names = (
            u'Выдача нагрудного знака и удостоверения многодетной семьи '
            u'(Тест)',)

        assert_strings = (kompleks_name + contained_services_names +
                          related_services_names)

        for assert_str in assert_strings:
            self.assertIn(assert_str, response)

    def test_document_list_handler(self):
        # Choose a kompleks on start page.
        self.testapp.get('/').click(description=u'Рождение ребенка')
        # Skip prerequisite choice page.
        srv_page_response = self.testapp.post('/prerequisites').follow()

        # Pick 3 of 4 services on service choice page and submit
        srv_names = (
            u'Государственная регистраци рождения ребенка (Тест)',
            u'Регистрация по месту жительства (Тест)',
            u'Выдача нагрудного знака и удостоверения многодетной семьи '
            u'(Тест)')

        ids_to_use = []
        for cell in srv_page_response.html.findAll('td'):
            if cell.get_text().strip() in srv_names:
                ids_to_use.append(cell.label['for'])

        req_params = 

        form = secondary_response.form
        checkboxes = [form.get('service', index=i) for i in (1, 2, 3)]
        for cb in checkboxes:
            cb.checked = True
        form.submit()
        # Choice is stored in session; go to result in debug_mode
        final_response = self.testapp.get('/result?debug_mode=1')

        #
        # TODO: finish this
        #

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()