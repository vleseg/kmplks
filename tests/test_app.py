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
        # Start with kompleks choice page and choose a kompleks
        primary_response = self.testapp.get('/').click(
            description=u'Рождение ребенка')
        # Choice is stored in session; follow redirect
        final_response = primary_response.follow()

        self.assertEqual(final_response.status_int, 200)

        for assert_str in (u'Рождение ребенка',
                           u'Уже есть свидетельство о рождении',
                           u'Уже есть прописка'):
            self.assertIn(assert_str, final_response)

    def test_service_choice_handler(self):
        # Start with kompleks choice page and choose a kompleks.
        primary_response = self.testapp.get('/').click(
            description=u'Рождение ребенка')
        # Choice is stored in session; follow redirect.
        secondary_response = primary_response.follow()
        # Pick a 'satisfied' prerequisite.
        id_to_use = None
        for cell in secondary_response.html.findAll('td'):
            if u'Уже есть свидетельство о рождении' in cell.get_text():
                id_to_use = cell.label['for']
        # Next page.
        final_response = self.testapp.post(
            '/prerequisites', {'prerequisite': id_to_use}).follow()

        self.assertEqual(final_response.status_int, 200)

        kompleks_name = u'Рождение ребенка',
        contained_services_names = (
            u'Регистрация по месту жительства (Тест)',
            u'Ежемесячное пособие на ребенка (Тест)')
        related_services_names = (
            u'Выдача нагрудного знака и удостоверения многодетной семьи '
            u'(Тест)',)
        intermediate_messages = (
            u'Рождение ребенка — Выберите услуги',
            u'Если какие-то из этих условий соблюдены — отметьте:',
            u'Выберите нужные услуги:',
            u'Эти услуги не входят в комплекс, но подходят по жизненной '
            u'ситуации')

        assert_strings = (kompleks_name + contained_services_names +
                          related_services_names + intermediate_messages)

        for assert_str in assert_strings:
            self.assertIn(assert_str, final_response)

    def test_document_list_handler(self):
        # Start with kompleks choice page and choose a kompleks
        primary_response = self.testapp.get('/').click(
            description=u'Рождение ребенка')
        # Choice is stored in session; follow redirect
        secondary_response = primary_response.follow()

        # Pick 3 of 4 services on service choice page and submit
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