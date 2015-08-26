import abc
import logging

from time import sleep
from threading import Thread

from multivac.models import JobsDB
from multivac.util import format_time

log = logging.getLogger('multivac')

class ChatBot(object):
    """
    Generic base class for chatbots. Subclasses must provide 
    a reply method and a messages generator
    """
    def __init__(self, redis_host, redis_port):
        self.db  = JobsDB(redis_host, redis_port)
        self.builtins = { 'confirm' : self._confirm,
                          'workers' : self._workers,
                          'jobs'    : self._jobs,
                          'help'    : self._help }
        self.message_queue = []

        t = Thread(target=self._message_worker)
        t.daemon = True
        t.start()

    @abc.abstractmethod
    def reply(self, text, channel):
        raise NotImplementedError

    @abc.abstractmethod
    def messages(self):
        """
        Generator yielding message tuples
        in the form (text,user,channel)
        """
        raise NotImplementedError

    def _message_worker(self):
        for msg in self.messages():
            self._process_msg(*msg)

    def _process_msg(self, text, user, channel):
        """
        """
        command,args = self._parse_command(text)
        
        if command in self.builtins:
            self.reply(self.builtins[command](args), channel)
        else:
            ok,result = self.db.create_job(command, args=args, initiator=user)
            if not ok:
                self.reply(result, channel)
                return

            job_id = result
            log.info('Created job %s' % job_id)

            if self.db.get_job(job_id)['status'] == 'pending':
                self.reply('%s needs confirmation' % str(job_id), channel)

            t = Thread(target=self._output_handler,args=(job_id, channel))
            t.daemon = True
            t.start()

    @staticmethod
    def _parse_command(text):
        """
        Parse message text; return command and arguments
        """
        words = text.split(' ')
        cmd = words.pop(0)
        args = ' '.join(words)

        return cmd, args

    def _output_handler(self, job_id, channel, stream=True):
        """
        Worker to send the output of a given job_id to a given channel
        params:
         - stream(bool): Toggle streaming output as it comes in
           vs posting when a job finishes. Default False.
        """
        active = False
        prefix = '[%s]' % job_id

        #sleep on jobs awaiting confirmation
        while not active:
            job = self.db.get_job(job_id)
            if job['status'] != 'pending':
                active = True
            else:
                sleep(1)

        self.reply('%s running' % str(job_id), channel)

        if stream:
            for line in self.db.get_log(job_id):
                self.reply(prefix + line, channel)
        else:
            msg = ''
            for line in self.db.get_log(job_id):
                msg += prefix + line + '\n'
            self.reply(msg, channel)

        self.reply(prefix + ' Done', channel)

    ######
    # Builtin command methods
    ######

    def _confirm(self, arg):
        job = self.db.get_job(arg)
        if not job:
            return 'no such job id'
        if job['status'] != 'pending':
            return 'job not awaiting confirm'

        self.db.update_job(job_id, 'status', 'ready')

        return 'confirmed job: %s' % job_id

    def _workers(self, arg):
        workers = self.db.get_workers()
        if not workers:
            return 'no registered workers'
        else:
            return [ ('%s(%s)' % (w['name'],w['host'])) for w in workers ]

    def _jobs(self, arg):
        subcommands = [ 'pending', 'running', 'completed', 'all' ]
        if arg not in subcommands:
            return 'argument must be one of %s' % ','.join(subcommands)

        jobs = self.db.get_jobs(status=arg)

        if not jobs:
            return 'no matching jobs found'

        formatted = []
        for j in jobs:
            created = format_time(j['created'])
            formatted.append('%s %s(%s) %s' % \
                        (created, j['id'], j['name'], j['status']))

            return formatted

    def _help(self, args):
        actions = self.db.get_actions()

        builtin_cmds = [ 'Builtin commands:' ] + [ c for c in self.builtins ] 
        action_cmds = [ 'Action commands:' ] + [ a['name'] for a in actions ]

        return builtin_cmds + action_cmds