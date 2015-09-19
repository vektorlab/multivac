import logging
import redis.exceptions

from redis import StrictRedis
from datetime import datetime
from uuid import uuid4
from time import sleep

from multivac.util import unix_time

log = logging.getLogger('multivac')

class JobsDB(object):
    prefix = { 'job' : 'multivac_job',
               'log' : 'multivac_log',
               'group' : 'multivac_group',
               'action' : 'multivac_action',
               'worker' : 'multivac_worker' }

    def __init__(self, redis_host, redis_port):
        self.redis = StrictRedis(
            host=redis_host,
            port=redis_port,
            decode_responses=True)
        self.subs = {}

        # TODO: add connection test with r.config_get('port')

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

        if not job:
            return (False, 'No such action')

        if not self.check_user(initiator, job['allow_groups'].split(',')):
            return (False, 'Invalid user command')

        job['id'] = str(uuid4().hex)
        job['args'] = args
        job['created'] = unix_time(datetime.utcnow())

        if job['confirm_required'] == "True":
            job['status'] = 'pending'
        else:
            job['status'] = 'ready'

        self._subscribe_to_log(job['id'])

        if initiator:
            self.append_job_log(job['id'], 'Job initiated by %s' % initiator)

        self.redis.hmset(self._key('job', job['id']), job)

        return (True, job['id'])

    def cancel_job(self, job_id):
        """ Cancel and cleanup a pending job by ID """
        job = self.get_job(job_id)
        if job['status'] != 'pending':
            return (False, 'Cannot cancel job in %s state' % job['status'])

        self.cleanup_job(job_id, canceled=True)

        return (True, '')

    def update_job(self, job_id, field, value):
        """ Update an arbitrary field for a job """
        self.redis.hset(self._key('job', job_id), field, value)
        return (True,)

    def cleanup_job(self, job_id, canceled=False):
        """
        Cleanup log subscriptions for a given job id and mark completed
        params:
         - canceled(bool): If True, mark job as canceled instead of completed
        """
        logkey = self._key('log', job_id)

        # send EOF signal to streaming clients
        self.redis.publish(logkey, 'EOF')

        if job_id in self.subs:
            self.subs[job_id].unsubscribe()
            del self.subs[job_id]
            log.debug('Unsubscribed from log channel: %s' % logkey)

        if canceled:
            self.update_job(job_id, 'status', 'canceled')
        else:
            self.update_job(job_id, 'status', 'completed')

    def get_job(self, job_id):
        """
        Return single job dict given a job id
        """
        return self.redis.hgetall(self._key('job', job_id))

    def get_jobs(self, status='all'):
        """
        Return all jobs dicts, optionally filtered by status
        via the 'status' param
        """
        jobs = [self.redis.hgetall(k) for k in
                self.redis.keys(pattern=self._key('job', '*'))]
        if status != 'all':
            return [j for j in jobs if j['status'] == status]
        else:
            return [j for j in jobs]

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
        key = self._key('log', job_id)
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
        logs = self.redis.lrange(self._key('log', job_id), 0, -1)
        return [l for l in reversed(logs)]

    def append_job_log(self, job_id, line):
        """
        Append a line of job output to a redis list and
        publish to relevant channel
        """
        key = self._key('log', job_id)
        prefixed_line = self._append_ts(line)

        self.redis.publish(key, prefixed_line)
        self.redis.lpush(key, prefixed_line)

    def _append_ts(self, msg):
        ts = datetime.utcnow().strftime('%a %b %d %H:%M:%S %Y')
        return '[%s] %s' % (ts, msg)

    def _subscribe_to_log(self, job_id):
        """ Subscribe this db object to a jobs log channel by ID """
        key = self._key('log', job_id)

        sub = self.redis.pubsub(ignore_subscribe_messages=True)
        sub.subscribe(key)
        self.subs[job_id] = sub

        log.debug('Subscribed to log channel: %s' % key)

    #######
    # Action Methods
    #######

    def get_action(self, action_name):
        """
        Return a single action dict, given the action name
        """
        return self.redis.hgetall(self._key('action', action_name))

    def get_actions(self):
        """
        Return all configured actions
        """
        return [self.redis.hgetall(k) for k in
                self.redis.keys(pattern=self._key('action', '*'))]

    def add_action(self, action):
        self.redis.hmset(self._key('action', action['name']), action)

    def purge_actions(self):
        [self.redis.delete(k) for k in
         self.redis.keys(pattern=self._key('action', '*'))]

    #######
    # Usergroup Methods
    #######

    def check_user(self, user, groups):
        """
        Check a list of groups to see if a user is a member to any
        params:
         - user(str): user name
         - groups(list): list of group names
        """
        if 'all' in groups:
            return True
        for group in groups:
            log.debug('checking group %s' % (group))
            if user in self.get_group(group):
                return True
        return False

    def get_group(self, group_name):
        """
        Return a list of usernames belonging to a group
        """
        return self.redis.lrange(self._key('group', group_name), 0, -1)

    def get_groups(self):
        """
        Return all configured groups
        """
        key = self._key('group', '*')
        groups = [ g.split(':')[1] for g in self.redis.keys(pattern=key) ]
        return { g:self.get_group(g) for g in groups }

    def add_group(self, group_name, members):
        key = self._key('group', group_name)
        for m in members:
            self.redis.lpush(key, m)

    def purge_groups(self):
        [ self.redis.delete(k) for k in \
          self.redis.keys(pattern=self._key('group', '*')) ]

    #######
    # Job Worker Methods 
    #######

    def register_worker(self, name, hostname):
        key = self._key('worker', name)
        worker = {'name': name, 'host': hostname}

        self.redis.hmset(key, worker)
        self.redis.expire(key, 15)

    def get_workers(self):
        return [self.redis.hgetall(k) for k in
                self.redis.keys(pattern=self._key('worker', '*'))]

    #######
    # Keyname Methods
    #######

    def _key(self, keytype, id):
        return self.prefix[keytype] + ':' + id
