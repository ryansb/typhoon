import logging
from tornado.gen import coroutine

from typhoon.server.handlers import base
from typhoon.server.settings import settings
from typhoon.server.clients.mongo_client import BaseMongoClient


class CountingHandler(base.BaseHandler):
    def initialize(self):
        assert settings.get('db', None) is not None
        self.client = BaseMongoClient('test', settings)

    @coroutine
    def on_finish(self):
        if self.name is not None:
            self.client.update(self.get_argument('name'), {'$inc': {'c': 1}}, upsert=True, attribute="n")


    @coroutine
    def get(self):
        self.name = self.get_argument("name", None, True)
        self.write("yolo")
