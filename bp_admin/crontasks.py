from google.appengine.ext import ndb
from bp_includes.lib.basehandler import BaseHandler
from bp_includes.models import User
import datetime


class AdminCleanupTokensHandler(BaseHandler):
    def get(self):
        # parameter in timedelta() assumes that tokens expire ~1 month1 after
        # creation:
        past_date = (
            datetime.datetime.utcnow() - datetime.timedelta(1 * 365 / 12))
        expired_tokens = User.token_model.query(
            User.token_model.created <= past_date)
        tokens_to_delete = expired_tokens.count()
        # delete the tokens in bulks of 100:
        while expired_tokens.count() > 0:
            keys = expired_tokens.fetch(100, keys_only=True)
            ndb.delete_multi(keys)

        self.response.write(
            'looking for tokens <= {d}<br>{t} tokens deleted <br> '
            '<a href={u}>home</a>'.format(d=past_date, t=tokens_to_delete,
                                          u=self.uri_for('home')))