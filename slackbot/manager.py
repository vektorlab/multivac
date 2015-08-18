import logging
import yaml
from time import sleep
from datetime import datetime
from redis import StrictRedis
from multiprocessing import Process,Pipe

from util import unix_time
from models import JobsDB

log = logging.getLogger('slackbot')

class Manager(object):
    def __init__(self, redis_host, redis_port, config_path='config.yml'):
        self.config_path = config_path
        self.db = JobsDB(redis_host, redis_port)
        self.procs = {} #dict of job_id:(process obj,process pipe object)

        self._load_actions()
        self.run()

    def run(self):
        log.info('Starting SlackBot Manager')
        while True:
            
            #spawn ready jobs
            for job in self.db.get_jobs(status='ready'):
                self._start_job(job)

            #collect ended processes
            collected = []
            for job_id in self.procs:
                proc,pipe = self.procs[job_id]
                if not proc.is_alive():
                    self.db.append_log(job_id, pipe.recv())
                    self.db.update_job(job_id, 'status', 'completed')
                    collected.append(job_id)
                    log.info('Collected finished job %s' % (job_id))

            for i in collected:
                del self.procs[i]

            sleep(1)

    def _load_actions(self):
        with open(self.config_path, 'r') as of:
            actions = yaml.load(of.read())['actions']

        self.db.purge_actions()

        for action in actions:
            if 'confirm_required' not in action:
                action['confirm_required'] = False
            if 'args_required' not in action:
                action['args_required'] = None

            self.db.add_action(action)
            log.info('loaded action %s' % (action['name']))

    def _start_job(self, job):
        job_id = job['id']

        parent_conn, child_conn = Pipe()
        proc = Process(target=self._worker,args=(job, child_conn))
        self.procs[job_id] = (proc, parent_conn)

        now = unix_time(datetime.utcnow())
        self.db.update_job(job_id, 'start_time', now)
        self.db.update_job(job_id, 'status', 'running')

        proc.start()

    def _worker(self, job, conn):
        """ Worker to run jobs """
        log.info('Worker spawned for job %s' % (job['id']))

        #output = job.action._run()
        conn.send('test')
        sleep(5)

        return
