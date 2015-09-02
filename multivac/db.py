import logging
import redis.exceptions

from redis import StrictRedis
from datetime import datetime
from uuid import uuid4
from time import sleep

from multivac.util import unix_time

log = logging.getLogger('multivac')

class JobsDB(object):
    job_prefix = 'multivac_job'
    log_prefix = 'multivac_log'
    action_prefix = 'multivac_action'
    worker_prefix = 'multivac_worker'

    def __init__(self,redis_host,redis_port):
        self.redis = StrictRedis(
                host=redis_host,
                port=redis_port,
                decode_responses=True)
        self.subs = {}

        #TODO: add connection test with r.config_get('port')

    #######
    # Job Methods 
    #######

    def create_job(self, action_name, args=None, initiator=None):
        """
        Create a new job with unique ID and subscribe to log channel
        params:
         - action_name(str): Name of the action this job uses
         - args(str): Optional space-delimited series of arguments to be
           appended to the job command
         - initiator(str): Optional name of the user who initiated this job
        """
        job = self.get_action(action_name)

        #validation
        if not job:
            return (False, 'No such action')

        job['id'] = str(uuid4().hex)
        job['args'] = args
        job['created'] = unix_time(datetime.utcnow())

        if job['confirm_required'] == "True":
            job['status'] = 'pending'
        else:
            job['status'] = 'ready'

        sub = self.redis.pubsub(ignore_subscribe_messages=True)
        sub.subscribe(self._logkey(job['id']))
        self.subs[job['id']] = sub

        log.debug('Subscribed to log channel: %s' % self._logkey(job['id']))

        if initiator:
            self.append_job_log(job['id'], 'Job initiated by %s' % initiator)

        self.redis.hmset(self._jobkey(job['id']), job)

        return (True, job['id'])

    def update_job(self, job_id, field, value):
        """
        Update an arbitrary field for a job
        """
        self.redis.hset(self._jobkey(job_id), field, value)
        return (True, )

    def cleanup_job(self, job_id):
        """
        Cleanup log subscriptions for a given job id and mark completed
        """
        #send EOF signal to streaming clients
        self.redis.publish(self._logkey(job_id), 'EOF')

        if job_id in self.subs:
            self.subs[job_id].unsubscribe()
            del self.subs[job_id]
            log.debug('Unsubscribed from log channel: %s' % \
                      self.logkey(job_id))

        self.update_job(job_id, 'status', 'completed')

    def get_job(self, job_id):
        """
        Return single job dict given a job id
        """
        return self.redis.hgetall(self._jobkey(job_id))

    def get_jobs(self, status='all'):
        """
        Return all jobs dicts, optionally filtered by status 
        via the 'status' param
        """
        jobs = [ self.redis.hgetall(k) for k in \
                 self.redis.keys(pattern=self._jobkey('*')) ]
        if status != 'all':
            return [ j for j in jobs if j['status'] == status ]
        else:
            return [ j for j in jobs ]

    def get_log(self, job_id):
        """
        Return stored log for a given job id if finished,
        otherwise return streaming log generator
        """
        job = self.get_job(job_id)

        if not job:
            return (False, 'no such job id')

        if job['status'] == 'completed':
            return self.get_stored_log(job_id)
        else:
            return self.get_logstream(job_id)

    def get_logstream(self, job_id):
        """
        Returns a generator object to stream all job output
        until the job has completed 
        """
        key = self._logkey(job_id)
        sub = self.subs[job_id]

        for msg in sub.listen():
            if str(msg['data']) == 'EOF':
                break
            else:
                yield msg['data']

    def get_stored_log(self, job_id):
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
    # Job Worker Methods 
    #######
    def register_worker(self, name, hostname):
        key = self._workerkey(name)
        worker = { 'name': name, 'host': hostname }

        self.redis.hmset(key, worker)
        self.redis.expire(key, 15)

    def get_workers(self):
        return [ self.redis.hgetall(k) for k in \
                 self.redis.keys(pattern=self._workerkey('*')) ]

    #######
    # Keyname Methods 
    #######

    def _logkey(self,id):
        return self.log_prefix + ':' + id

    def _actionkey(self,id):
        return self.action_prefix + ':' + id

    def _jobkey(self,id):
        return self.job_prefix + ':' + id

    def _workerkey(self,id):
        return self.worker_prefix + ':' + id
