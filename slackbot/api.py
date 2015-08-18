import itertools
import time
from flask import Flask, Response, redirect, request, url_for
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
def index():
    if request.headers.get('accept') == 'text/event-stream':
        def events():
            pubsub = redis.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe('slackbot')
            for e in pubsub.listen():
                yield('data: %s\n\n' % e['data'])

        return Response(events(), content_type='text/event-stream')
    return redirect(url_for('static', filename='index.html'))

if __name__ == "__main__":
    app.logger.info('Starting slackbot v%s' % version)
    app.run(host='localhost', port=8000, debug=True)
