import time
import json
from flask import Flask, Response, redirect, request
from flask_restful import Api, abort
from gevent.wsgi import WSGIServer
from redis import StrictRedis

from multivac.version import version
from multivac.models import JobsDB
from multivac.resources import Job, Jobs, Action, Actions, Hello, Confirm, Logs

resource_map = { Hello   : '/',
                 Jobs    : '/jobs',
                 Actions : '/actions',
                 Confirm : '/confirm',
                 Job     : '/jobs/<string:job_id>',
                 Logs    : '/logs/<string:job_id>',
                 Action  : '/actions/<string:action_name>' }

class MultivacApi(object):
    def __init__(self, redis_host, redis_port):
        self.app = Flask('multivac')
        self.api = Api(self.app)

        self.app.config['db'] = JobsDB(redis_host, redis_port)

        for resource,path in resource_map.items():
            self.api.add_resource(resource, path)

    def start_server(self, listen_port=8000):
        print(('Starting Multivac API v%s' % version))
        http_server = WSGIServer(('', listen_port), self.app)
        http_server.serve_forever()

if __name__ == "__main__":
    self.app.logger.info('Starting multivac v%s' % version)
    self.app.run(host='localhost', port=8000, debug=True)
