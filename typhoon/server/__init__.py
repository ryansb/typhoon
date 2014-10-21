import logging
from collections import defaultdict

import tornado.ioloop
from tornado.options import options
import tornado.httpserver
import tornado.web

from typhoon.server.clients.mongo_client import BaseMongoClient
from typhoon.server.settings import settings
from typhoon.server.url_patterns import url_patterns


class App(tornado.web.Application):

    _counters = defaultdict(int)
    _client = None

    def __init__(self):
        """App wrapper constructor, global objects within our Tornado platform
        should be managed here."""
        self.logger = logging.getLogger(self.__class__.__name__)

        tornado.web.Application.__init__(self, url_patterns, **settings)

        assert settings.get('db', None) is not None
        self.client = BaseMongoClient('test', settings)

        tornado.ioloop.PeriodicCallback(self.write_counter, 5000).start()

    def write_counter(self):
        self.client = BaseMongoClient('test', settings)
        keys = list(self._counters.keys())
        for k in keys:
            self.logger.info("Writing %s" % k)
            self.client.update(
                k,
                {
                    '$inc': {
                        'c': self._counters.pop(k),
                    },
                },
                upsert=True,
                attribute="n"
            )


def main():
    """Main function for running stand alone"""

    logger = logging.getLogger()
    tornado.options.parse_command_line()
    app = App()
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    http_server.listen(options.port)

    logger.info('Tornado server started on port %s', options.port)

    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        logger.info("Stopping server on port %s",  options.port)
