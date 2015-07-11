import logging
import sys
import inspect
from time import sleep

log = logging.getLogger('slackbot')

class Action(object):
    #defaults
    config = { 'needs_confirm': False, 'args_required': None }

    def __init__(self, opts):
        self.name = self.__class__.__name__.lower()

        #override defaults and set as attrs
        self.config.update(opts)
        for k,v in self.config.iteritems():
            self.__setattr__(k,v)

        log.debug('created action %s\n%s' % (self.name,self.config))

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

class Noop(Action):
    opts = {}

    def __init__(self):
        super(self.__class__, self).__init__(self.opts)

    def _run(self):
        sleep(2)
        return 'noop'

def get_actions():
    ret = {}
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj) and name != 'Action':
            ret[name.lower()] = obj

    return ret

all_actions = get_actions()
