import logging
from tornado.gen import coroutine

from typhoon.server.handlers import base
from typhoon.server.settings import settings
from typhoon.server.clients.mongo_client import BaseMongoClient

log = logging.getLogger(__name__)


class SimpleHandler(base.BaseHandler):
    def initialize(self):
         pass

    def get(self):
        """Example Handler"""
        self.write("yolo")
        log.info("hey")


class CountingHandler(base.BaseHandler):
    def initialize(self):
        assert settings.get('db', None) is not None
        self.client = BaseMongoClient('test', settings)

    @coroutine
    def get(self):
        if self.get_argument("name", None, True) is not None:
            self.write("yolo")
            self.finish()
            yield self.client.update(self.get_argument('name'), {'$inc': {'c': 1}}, upsert=True, attribute="n")
        else:
            self.write("add ?name=yourname to be counted")

