from webapp2 import Route, RequestHandler
from webapp2_extras import routes

class RESTTree(object):
    def __init__(self, raw_tree):
        self.tree = self.generate_tree(raw_tree)
        self.routes = None

    def get_routes(self):
        if self.routes is None:
            self.generate_routes()

        return self.routes

    def generate_tree(self, raw_tree):
        # TODO: implement this (graph of RESTNode objects)
        pass

    def generate_routes(self):
        # TODO: implement this so that routes are actually generated
        self.routes = [
            routes.PathPrefixRoute('/admin/api', [
                Route('/<kind_name>/entities', handler='main.ApiHandler'),
                Route('/<kind_name>/fields', handler='main.ApiHandler'),
                Route('/entities/<entity_id>', handler='main.ApiHandler'),
                Route('/entities/<entity_id>/relatives',
                      handler='main.ApiHandler')
           ])
        ]