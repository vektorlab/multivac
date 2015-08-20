import logging

from redis import StrictRedis
from datetime import datetime
from uuid import uuid4
from time import sleep

log = logging.getLogger('multivac')

class JobsDB(object):
    job_prefix = 'multivac_job'
    log_prefix = 'multivac_log'
    action_prefix = 'multivac_action'

    def __init__(self,redis_host,redis_port):
        self.redis = StrictRedis(
                host=redis_host,
                port=redis_port,
                decode_responses=True)
        self.sub = self.redis.pubsub(ignore_subscribe_messages=True)

    #######
    # Job Methods 
    #######

    def create_job(self, action_name, args=None):
        """
        Create a new job with unique ID and subscribe to log channel
        params:
         - action_name(str): Name of the action this job uses
        """
        job = self.get_action(action_name)

        #validation
        if not job:
            return (False, 'No such action')

        job['id'] = str(uuid4().hex)
        job['args'] = args

        if job['confirm_required'] == "True":
            job['status'] = 'pending'
        else:
            job['status'] = 'ready'

        self.sub.subscribe(self._logkey(job['id']))
        log.debug('Subscribed to log channel: %s' % self._logkey(job['id']))

        self.redis.hmset(self._jobkey(job['id']), job)

        return (True, job['id'])

    def update_job(self, job_id, field, value):
        """
        Update an arbitrary field for a job
        """
        self.redis.hset(self._jobkey(job_id), field, value)

    def get_job(self, job_id):
        """
        Return single job dict given a job id
        """
        return self.redis.hgetall(self._jobkey(job_id))

    def get_jobs(self, status=None):
        """
        Return all jobs dicts, optionally filtered by status 
        via the 'status' param
        """
        jobs = [ self.redis.hgetall(k) for k in \
                 self.redis.keys(pattern=self._jobkey('*')) ]
        if status:
            return [ j for j in jobs if j['status'] == status ]
        else:
            return [ j for j in jobs ]

    def get_logstream(self, job_id, append_newline=False):
        """
        Returns a generator object to stream all job output
        until the job has completed 
        """
        key = self._logkey(job_id)

        for msg in self.sub.listen():
            print(msg)
            if msg['channel'] == key:
                # unsubscribe from channel and return upon job completion
                if str(msg['data']) == 'EOF': 
                    self.sub.unsubscribe(key)
                    log.debug('Unsubscribed from log channel: %s' % key)
                    break
                else:
                    if append_newline:
                        yield msg['data'] + '\n'
                    else:
                        yield msg['data']

    def get_job_log(self, job_id):
        """
        Return the stored output of a given job id
        """
        logs = self.redis.lrange(self._logkey(job_id), 0, -1)
        return [ l for l in reversed(logs) ]

    def append_job_log(self, job_id, line):
        """
        Append a line of job output to a redis list and 
        publish to relevant channel
        """
        key = self._logkey(job_id)
        prefixed_line = self._append_ts(line)

        self.redis.publish(key, prefixed_line)
        self.redis.lpush(key, prefixed_line)

    def end_job_log(self, job_id):
        self.redis.publish(self._logkey(job_id), 'EOF')

    def _append_ts(self, msg):
        ts = datetime.utcnow().strftime('%a %b %d %H:%M:%S %Y')
        return '[%s] %s' % (ts,msg)

    #######
    # Action Methods 
    #######

    def get_action(self, action_name):
        """
        Return a single action dict, given the action name
        """
        return self.redis.hgetall(self._actionkey(action_name))

    def get_actions(self):
        """
        Return all configured actions
        """
        return [ self.redis.hgetall(k) for k in \
                 self.redis.keys(pattern=self._actionkey('*')) ]

    def add_action(self, action):
        self.redis.hmset(self._actionkey(action['name']), action)

    def purge_actions(self):
        [ self.redis.delete(k) for k in \
          self.redis.keys(pattern=self._actionkey('*')) ]

    #######
    # Keyname Methods 
    #######

    def _logkey(self,id):
        return self.log_prefix + ':' + id

    def _actionkey(self,id):
        return self.action_prefix + ':' + id

    def _jobkey(self,id):
        return self.job_prefix + ':' + id
