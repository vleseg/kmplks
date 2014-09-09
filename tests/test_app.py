# coding=utf-8
import os
import sys
import unittest
# Third-party imports
from google.appengine.ext import testbed
import webtest
# Project imports
from main import app
from init.init_db import init_db


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.testapp = webtest.TestApp(app)
        cls.testbed = testbed.Testbed()
        cls.testbed.activate()
        cls.testbed.init_datastore_v3_stub()
        cls.testbed.init_memcache_stub()
        init_db(test_mode=True)

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
            u'Регистрация по месту жительства',
            u'Ежемесячное пособие на ребенка')
        related_services_names = (
            u'Выдача нагрудного знака и удостоверения многодетной семьи',)

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
            u'Государственная регистрация рождения ребенка',
            u'Регистрация по месту жительства',
            u'Выдача нагрудного знака и удостоверения многодетной семьи')

        ids_to_use = []
        for cell in srv_page_response.html.findAll('td'):
            if cell.get_text().strip() in srv_names:
                ids_to_use.append(cell.label['for'])

        req_params = {'service': ids_to_use}
        response = self.testapp.post('/services', req_params).follow()

        doc_names = [
            u'Заявление о выдаче нагрудного знака и удостоверения многодетной '
            u'семьи',
            u'Заявление о регистрации по месту жительства, форма №6',
            u'Заявление о рождении, форма №1',
            u'Документ, удостоверяющий личность заявителя',
            u'Документ, удостоверяющий личность второго родителя',
            u'Простая доверенность',
            u'Доверенность на передачу согласия на обработку ПДн',
            u'Согласие на обработку персональных данных',
            u'Документ о перемене имени', u'Свидетельство о заключении брака',
            u'Свидетельство о рождении', u'Свидетельство об усыновлении',
            u'Документ о праве на жилое помещение', u'Домовая книга',
            u'Медицинское свидетельство о рождении, форма №103/У',
            u'Решение суда о признании гражданина недееспособным, ограниченно '
            u'дееспособным',
            u'Решение суда об ограничении родительских прав, о лишении '
            u'родительских прав, об отмене усыновления',
            u'Свидетельство о смерти либо решение суда об объявлении '
            u'гражданина умершим',
            u'Фотография 3х4']

        for assert_str in doc_names:
            self.assertIn(assert_str, response)

    @classmethod
    def tearDownClass(cls):
        cls.testbed.deactivate()