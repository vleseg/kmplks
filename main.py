#!/usr/bin/env python
# coding=utf-8
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from collections import OrderedDict
from itertools import chain
import json
# Third-party imports
from google.appengine.api import taskqueue
from google.appengine.ext import ndb
import webapp2
from webapp2_extras import sessions, routes
# Project-specific imports
from config import CFG
from datastore_init import initialize_datastore
import models


class KompleksError(BaseException):
    pass


class SessionHandlingError(KompleksError):
    pass


# Custom jinja2 filters and tests.
def is_list(value):
    return isinstance(value, list)


def to_url(value):
    """
    Generate MFC knowledge base URL using Service.kb_id

    :param int value: ID of a service in MFC knowledge base.
    """
    kb_pattern = 'http://mfcportal/yakutiya/services/default.aspx?element={}'
    return kb_pattern.format(value)

CFG['JINJA2_ENV'].tests.update({
    'list': is_list,
    'None': lambda x: x is None
})
CFG['JINJA2_ENV'].filters['to_url'] = to_url
CFG['JINJA2_ENV'].globals['uri_for'] = webapp2.uri_for


class BaseHandler(webapp2.RequestHandler):
    """
    Base class for all handlers in this app. All session handling logic and
    convenience method render() are defined here.
    """
    template_filename = ""

    def __init__(self, request, response):
        super(BaseHandler, self).__init__(request, response)
        # Will be used with jinja2 template.
        self.context = {}
        # Will be used later in dispatch().
        self.session_store = None

    def dispatch(self):
        """
        Wraps default dispatcher with session handling routine.
        """
        # Get a session store for this request.
        self.session_store = sessions.get_store(
            request=self.request, key=CFG['ANCESTOR'])

        try:
            # Dispatch the request.
            super(BaseHandler, self).dispatch()
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        """
        Returns a session using default cookie key.
        """
        return self.session_store.get_session()

    def store_session_data(self, key, value):
        """
        Puts data into session store.

        Ensures integrity. Note that you can't put None values in session
        store, since it would cause ambiguity on retrieval time: one wouldn't
        know, if self.session.get() returns None because key is not found or
        because None value was stored.

        :type key: str
        """
        if value is None:
            raise SessionHandlingError(
                "Attempt to put a None value by key '{}' in session store."
                .format(key))
        self.session[key] = value

    def get_session_data(self, keys, obligatory=True):
        """
        Retrieves data from session store.

        :param keys: one or more keys to be used to retrieve data from session
            store
        :param obligatory: if False and a key is not found in session store,
            session is not considered corrupt and None is returned for
            corresponding key
        :return: OrderedDict if more than one key was passed; otherwise a
            single value, retrieved from session store by key passed is
            returned
        """
        multiple = False
        if not isinstance(keys, (list, tuple)):
            keys = [keys]
        elif len(keys) > 1:
            multiple = True

        data = OrderedDict()

        for key in keys:
            value = self.session.get(key)
            if value is None and obligatory:
                #
                # TODO: replace with 'corrupt session' warning someday
                #
                self.redirect('/', abort=True)
            elif not multiple:
                return value
            else:
                data[key] = value

        return data

    def render(self):
        """
        Renders template and context together.

        A convenience method.
        """
        template = CFG['JINJA2_ENV'].get_template(self.template_filename)
        self.response.out.write(template.render(**self.context))


    @staticmethod
    def construct_service_graph(services):
        """
        Constructs a dictionary, that represents a graph of dependencies
        between services.

        Resulting dictionary is serialized as JSON and passed in a context for
        rendering and is later used by special JS script, that does not let a
        user choose a service, whose dependencies were not satisfied.

        :type services: list[Service]
        """
        service_keys = [s.key for s in services]
        service_ids = [k.urlsafe() for k in service_keys]

        service_graph = dict(
            (id_, {'children': [], 'parents': []}) for id_ in service_ids)

        for s, sid in zip(services, service_ids):
            relations = service_graph[sid]
            relations['days'] = s.max_days
            relations['workDays'] = s.max_work_days
            relations['enabled'] = True
            relations['checked'] = False

            for parent_key in s.dependencies:
                if parent_key in service_keys:
                    parent_id = parent_key.urlsafe()
                    relations['parents'].append(parent_id)
                    service_graph[parent_id]['children'].append(sid)

        return service_graph


class KompleksHandler(BaseHandler):
    """
    Handler for kompleks choice page.

    On this page all available komplekses are listed. List of MFCs, where every
    kompleks is available is provided as well.

    User can choose a kompleks by clicking on its name.
    """
    template_filename = "start.html"

    def get(self):
        kompleks_id = self.request.get("id")
        if kompleks_id:
            self.store_session_data('kompleks_id', kompleks_id)
            self.store_services_in_session(kompleks_id)
            self.redirect('/prerequisites')

        k_iter = models.Kompleks.query().iter()

        # Constructing context.
        self.context['komplekses'] = (self.prepare(k) for k in k_iter)

        self.render()

    def store_services_in_session(self, kompleks_id):
        """
        Retrieve ids of services (both related and contained), that are bound
        to kompleks and save them in session store.

        This is a sub of a KompleksHandler.get() routine. It was made a
        separate method to avoid cluttering of KompleksHandler.get()

        :type kompleks_id: str
        """
        # Services, that are contained in the kompleks.
        contained_ids = []
        # Services, that are related to the kompleks (see model.Service docs
        # for better understanding).
        related_ids = []
        kompleks = models.from_urlsafe(kompleks_id)

        for service in models.Service.query().iter():
            if kompleks.key in service.containing_komplekses:
                contained_ids.append(service.urlsafe())
            elif kompleks.key in service.related_komplekses:
                related_ids.append(service.urlsafe())

        # Writing session data.
        self.store_session_data("contained_ids", contained_ids)
        self.store_session_data("related_ids", related_ids)

    @staticmethod
    def prepare(kompleks):
        mfcs = (mfc_key.get() for mfc_key in kompleks.mfcs)
        return {'name': kompleks.name, 'mfcs': mfcs,
                'id': kompleks.urlsafe()}


class PrerequisiteChoiceHandler(BaseHandler):
    """
    Handler for prerequisite choice page.

    Prerequisite descriptions are displayed on this page. See docs for
    model.Service to find out, what a prerequisite description is.

    If a user checks a prerequisite summary on this page, corresponding
    service is excluded from list on next page. A user can check any number of
    prerequisites. However, the on-page script will not let a user check
    a prerequisite, whose dependencies were not satisfied.
    """
    template_filename = 'prerequisites.html'

    def get(self):
        session_data = self.get_session_data(
            ['kompleks_id', 'contained_ids', 'related_ids'])

        kompleks = models.from_urlsafe(session_data['kompleks_id'])
        services = models.from_urlsafe(
            chain(session_data['contained_ids'], session_data['related_ids']),
            multi=True)

        # Since services can share prerequisites, we need to filter unique
        # ones before rendering.
        prereq_keys = set()

        for service in services:
            prereq_keys |= set(service.dependencies)

        prerequisites = ndb.get_multi(prereq_keys)
        """:type prerequisites: Service | list[Service]"""
        dependency_graph = self.construct_service_graph(prerequisites)

        # Constructing context.
        self.context["kompleks"] = kompleks
        self.context["prerequisites"] = [
            self.prepare(s) for s in prerequisites]

        self.context['dependency_graph'] = json.dumps(dependency_graph)

        self.render()

    def post(self):
        # Please note that prerequisites can only be part of 'contained' list,
        # but not of 'related'. Might be changed in future.
        prereqs_satisfied = self.request.get_all('prerequisite')

        # Writing session data.
        self.store_session_data('prereqs_satisfied', prereqs_satisfied)

        self.redirect('/services')

    @staticmethod
    def prepare(service):
        return {'id': service.urlsafe(),
                'text': service.prerequisite_description}


class ServiceChoiceHandler(BaseHandler):
    """
    Handler for service choice page.

    This page is split into two parts -- for 'contained' and 'related' services
    (see docs for model.Service for description of why and how they differ.

    A user can check any number of services of both types. However, the on-page
    script will not let a user check services, whose dependencies were not
    satisfied.
    """
    template_filename = 'services.html'

    def get(self):
        d = self.get_session_data([
            'kompleks_id', 'contained_ids', 'related_ids',
            'prereqs_satisfied'])
        # If this page is being visited not for the first time in current
        # session, # retrieve services, that were checked and submitted the
        # last time.
        contained_ids = set(d['contained_ids']) - set(d['prereqs_satisfied'])
        contained_services = models.from_urlsafe(contained_ids, multi=True)
        related_services = models.from_urlsafe(d['related_ids'], multi=True)

        # Constructing context.
        self.context["kompleks"] = models.from_urlsafe(d['kompleks_id'])
        self.context["contained_services"] = map(self.prepare,
                                                 contained_services)
        self.context["related_services"] = map(self.prepare,
                                               related_services)

        # If our last choice of services was saved in session -- restore it.
        # if service_ids:
        #     self.context['service_ids'] = json.dumps(service_ids)
        self.context["dependency_graph"] = json.dumps(
            self.construct_service_graph(
                contained_services + related_services))

        self.render()

    def post(self):
        # Writing session data.
        self.store_session_data('service_ids', self.request.get_all('service'))

        self.redirect('/result')

    @staticmethod
    def prepare(service):
        return {'id': service.key.urlsafe(), 'name': service.name,
                'description': service.short_description,
                'ogv': service.ogv.get().short_name,
                'max_days':  service.max_days, 'kb_id': service.kb_id,
                'max_work_days': service.max_work_days,
                'terms_description': service.terms_description,
                '_key': service.key}


class ResultHandler(BaseHandler):
    """
    Handler for result page.

    This is the final page of this app. It contains a list of documents to be
    provided by an applicant.
    """
    template_filename = 'result.html'

    def get(self):
        d = self.get_session_data(['kompleks_id', 'service_ids'])

        kompleks = models.from_urlsafe(d['kompleks_id'])
        services = models.from_urlsafe(d['service_ids'], multi=True)

        # document id to DocumentToService instances mapping.
        doc_id_to_dts = {}

        # dts == DocumentToService instance.
        for service in services:
            for dts in models.DocumentToService.query(
                    models.DocumentToService.service == service.key):
                doc_id = dts.document.urlsafe()
                # A service may map to different sets of documents -- depending
                # on the kompleks, that was picked in the very beginning.
                if (not dts.kompleks
                        or dts.kompleks.urlsafe() == d['kompleks_id']):
                    if doc_id not in doc_id_to_dts:
                        doc_id_to_dts[doc_id] = [dts]
                    else:
                        doc_id_to_dts[doc_id].append(dts)

        # Constructing context.
        k = lambda e: (e['_class'], e['name'])
        self.context["kompleks"] = kompleks
        self.context["documents"] = sorted(
            [self.prepare(item) for item in doc_id_to_dts.items()], key=k)

        self.render()

    @staticmethod
    def prepare(item):
        doc_id, dts_items = item
        document = models.from_urlsafe(doc_id)
        result = {'name': document.name,
                  'description': document.precompile_description(dts_items),
                  '_class': document.doc_class.get().sort_key,
                  'id': doc_id}

        if not document.is_a_paper_document:
            result.update(n_originals='', n_copies='', o_supply_type='')
        else:
            result.update(
                n_originals=document.count_up('originals', dts_items),
                n_copies=document.count_up('copies', dts_items),
                o_supply_type=document.define_o_supply_type(dts_items))

        return result


class AdminHandler(BaseHandler):
    template_filename = 'admin_home.html'

    def get(self):
        self.render()

    def post(self):
        action = self.request.get('action')
        if action == 'init-db':
            taskqueue.add(url=webapp2.uri_for('datastore-init'))
            self.redirect(webapp2.uri_for('admin'))
        elif action == 'edit-db':
            self.redirect(webapp2.uri_for('admin-list'))


class AdminList(BaseHandler):
    template_filename = "admin_list.html"

    def get(self):
        self.context['kinds'] = []
        for kind in models.iter_datastore_kinds():
            if kind._name is not None:
                self.context['kinds'].append({'name': kind.__name__,
                                              'verbose_name': kind._name[1]})

        self.render()


class AdminEdit(BaseHandler):
    template_filename = "admin_edit.html"

    def get(self):
        action = 'new' if '/new' in self.request.uri else 'edit'
        to_fetch = self.request.get('kind')
        if len(to_fetch) == 0:
            to_fetch = self.request.get('id')
        self.context.update({'action': action, 'to_fetch': to_fetch})
        self.render()


class ApiHandler(webapp2.RequestHandler):
    @staticmethod
    def make_res_obj_for_kind(kind, entity=None):
        fields = []
        choices_dict = {}
        try:
            for p in kind.iter_properties(names_only=True):
                objectified = kind.objectify_property(p, entity=entity)
                if 'choices' in objectified:
                    choices = objectified.pop('choices')
                    choices_name = objectified.pop('choices_name')
                    if choices is not None and choices_name not in choices_dict:
                        choices_dict[choices_name] = choices
                fields.append(objectified)
        except:
            pass

        res_obj = {
            'kind': kind._name[0],
            'kind_plural': kind._name[1],
            'fields': fields
        }
        if len(choices_dict) > 0:
            res_obj['choices'] = choices_dict
        if entity is not None:
            res_obj['label'] = getattr(entity, entity._repr_field)

        return res_obj

    def get(self, **kwargs):
        self.response.headers.add('Content-Type', 'application/json')

        if 'kind_name' in kwargs:
            kind = models.get_kind(kwargs['kind_name'])

            if '/entities' in self.request.uri:
                items = map(lambda e: e.as_tuple('_urlsafe', kind._repr_field),
                            kind.query().iter())
                res_obj = {
                    'kind': kind._name[0],
                    'kind_plural': kind._name[1],
                    'items': [{'id': i, 'value': v} for i, v in items]
                }

                self.response.out.write(json.dumps(res_obj))
            elif '/fields' in self.request.uri:
                res_obj = self.make_res_obj_for_kind(kind)

                self.response.out.write(json.dumps(res_obj))
            else:
                self.response.set_status(300)
        elif 'entity_id' in kwargs:
            entity = models.from_urlsafe(kwargs['entity_id'])
            if entity is None:
                self.abort(404)

            kind = entity.__class__
            res_obj = self.make_res_obj_for_kind(kind, entity=entity)

            self.response.out.write(json.dumps(res_obj))
        else:
            self.response.set_status(300)

    def delete(self, **kwargs):
        # TODO: implement correct error message on attempt to delete an entity
        # which is set as 'required' property somewhere.
        if 'entity_id' in kwargs:
            if '/entities' in self.request.uri:
                entity = models.from_urlsafe(kwargs['entity_id'])
                entity.erase_reverse_references()
                entity.key.delete()
                self.response.set_status(204)
            else:
                self.response.set_status(300)
        else:
            self.response.set_status(300)

    def post(self, **kwargs):
        self.response.headers.add('Content-Type', 'application/json')

        if 'kind_name' in kwargs:
            if '/entities' in self.request.uri:
                req_body = json.loads(self.request.body)
                kind = models.get_kind(kwargs['kind_name'])
                entity = kind()
                for field in req_body:
                    entity.decode_and_set_property(field)
                id_ = entity.put().urlsafe()

                self.response.out.write(json.dumps({'id': id_}))

    def put(self, **kwargs):
        if 'entity_id' in kwargs:
            if '/entities' in self.request.uri:
                entity = models.from_urlsafe(kwargs['entity_id'])
                req_body = json.loads(self.request.body)
                for modification in req_body:
                    entity.decode_and_set_property(modification)
                entity.put()
            else:
                self.response.set_status(300)
        else:
            self.response.set_status(300)


class AdminWorker(webapp2.RequestHandler):
    def post(self):
        initialize_datastore()


config = {'webapp2_extras.sessions': {
    'secret_key': 'O12ZXGyXkE32Fz0kGWd5',
    'session_max_age': 3600 * 24
}}

app_routes = [
    routes.PathPrefixRoute('/admin/api', [
        webapp2.Route('/<kind_name>/entities', handler=ApiHandler),
        webapp2.Route('/<kind_name>/fields', handler=ApiHandler),
        webapp2.Route('/entities/<entity_id>', handler=ApiHandler)
    ]),
    webapp2.Route('/', handler=KompleksHandler, name='start'),
    webapp2.Route('/prerequisites', handler=PrerequisiteChoiceHandler,
                  name='prerequisites'),
    webapp2.Route('/services', handler=ServiceChoiceHandler,
                  name='services'),
    webapp2.Route('/result', handler=ResultHandler, name='result'),
    webapp2.Route('/admin', handler=AdminHandler, name='admin'),
    webapp2.Route('/admin/datastore-init', handler=AdminWorker,
                  name='datastore-init'),
    webapp2.Route('/admin/list', handler=AdminList, name='admin-list'),
    webapp2.Route('/admin/edit', handler=AdminEdit, name='admin-edit'),
    webapp2.Route('/admin/new', handler=AdminEdit, name='admin-new')
]

app = webapp2.WSGIApplication(app_routes, debug=True, config=config)
