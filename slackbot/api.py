import itertools
import time
import json
from flask import Flask, Response, redirect, request, url_for, stream_with_context
from flask_restful import Api,abort
from redis import StrictRedis

from version import version
from models import JobsDB
from resources import Jobs,Actions,Hello,Confirm

app = Flask('slackbot')
api = Api(app)

app.config['db'] = JobsDB('localhost', 6379)

resource_map = { Hello   : '/',
                 Jobs    : '/jobs',
                 Actions : '/actions',
                 Confirm : '/confirm' }

for resource,path in resource_map.iteritems(): 
    api.add_resource(resource, path)

@app.route('/logs')
def logs():
    if not request.args.has_key('id'):
        return json.dumps({'error':'no id provided'}), 400

    logstream = app.config['db'].get_logstream(request.args['id'], append_newline=True)
    return Response(stream_with_context(logstream))

if __name__ == "__main__":
    app.logger.info('Starting slackbot v%s' % version)
    app.run(host='localhost', port=8000, debug=True)
