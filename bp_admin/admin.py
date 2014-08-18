# -*- coding: utf-8 -*-
from google.appengine.api import users

from bp_includes.lib.basehandler import BaseHandler


class AdminLogoutHandler(BaseHandler):
    def get(self):
        self.redirect(users.create_logout_url(dest_url=self.uri_for('home')))
