from typhoon.server.handlers import uvb

url_patterns = [
    (r'/', uvb.SimpleHandler),
    (r'/c/?', uvb.CountingHandler),
]
