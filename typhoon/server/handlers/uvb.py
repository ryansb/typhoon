from tornado.gen import coroutine

from typhoon.server.handlers import base


class CountingHandler(base.BaseHandler):
    @coroutine
    def get(self):
        self.application._counters[self.get_argument('name')] += 1
        self.write("yolo")
