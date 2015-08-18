from redis import StrictRedis
from datetime import datetime
from uuid import uuid4

class JobsDB(object):
    job_prefix = 'multivac_job'
    log_prefix = 'multivac_log'
    action_prefix = 'multivac_action'

    def __init__(self,redis_host,redis_port):
        self.redis = StrictRedis(host=redis_host, port=redis_port)

    #######
    # Job Methods 
    #######

    def create_job(self, action_name, args=None):
        """
        Create a new job with unique ID
        params:
         - action_name(str): Name of the action this job uses
        """
        job = self.get_action(action_name)
        if not job:
            return None

        job['id'] = str(uuid4().hex)
        job['args'] = args

        if job['confirm_required'] == "True":
            job['status'] = 'pending'
        else:
            job['status'] = 'ready'

        self.redis.hmset(self._jobkey(job['id']), job)

        return job['id']

    def update_job(self, job_id, field, value):
        """
        Update an arbitrary field for a job
        """
        job = self.get_job(job_id)
        job[field] = value
        self.redis.hmset('multivac_job:' + job_id, job)

    def get_job(self, job_id):
        return self.redis.hgetall(self._jobkey(job_id))

    def get_jobs(self, status=None):
        jobs = [ self.redis.hgetall(k) for k in \
                 self.redis.keys(pattern=self._jobkey('*')) ]
        if status:
            return [ j for j in jobs if j['status'] == status ]
        else:
            return [ j for j in jobs ]

    def get_log(self, job_id):
        logs = self.redis.lrange(self._logkey(job_id),0,-1)
        return [ l for l in reversed(logs) ]

    def append_log(self, job_id, line):
        self.redis.lpush(self._logkey(job_id), self._append_ts(line))

    def _append_ts(self, msg):
        ts = datetime.utcnow().strftime('%a %b %d %H:%M:%S %Y')
        return '[%s] %s' % (ts,msg)

    #######
    # Action Methods 
    #######

    def get_action(self, action_name):
        return self.redis.hgetall(self._actionkey(action_name))

    def get_actions(self):
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

