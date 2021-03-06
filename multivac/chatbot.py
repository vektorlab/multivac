import abc
import logging
from time import sleep
from concurrent.futures import ThreadPoolExecutor

from multivac.db import JobsDB
from multivac.util import format_time

log = logging.getLogger('multivac')


class ChatBot(object):
    """
    Generic base class for chatbots. Subclasses must provide
    a reply method and a messages property generator
    """

    def __init__(self, redis_host, redis_port):
        self.db = JobsDB(redis_host, redis_port)
        self.builtins = { 'help': self._help,
                          'jobs': self._jobs,
                          'logs': self._logs,
                          'cancel': self._cancel,
                          'confirm': self._confirm,
                          'workers': self._workers }

        self.executor = ThreadPoolExecutor(max_workers=20)
        log.debug('set max chatbot workers: %s' % self.executor._max_workers)

        self._message_worker()

    @abc.abstractmethod
    def reply(self, text, channel):
        """
        Method to send a message to a specified channel
        """
        raise NotImplementedError

    @abc.abstractproperty
    def messages(self):
        """
        Generator yielding message tuples in the form (text,user,channel)
        """
        raise NotImplementedError

    def _print_queue(self):
        while True:
            print('work queue: %s' % self.executor._work_queue.qsize())
            sleep(1)

    def _message_worker(self):
        for msg in self.messages:
            try:
                self._process_msg(*msg)
            except Exception as e:
                log.error(e)

    def _process_msg(self, text, user, channel):
        """
        """
        command, args = self._parse_command(text)

        if command in self.builtins:
            self.reply(self.builtins[command](args), channel)
            self.reply('EOF', channel)
        else:
            ok, result = self.db.create_job(command, args=args, initiator=user)
            if not ok:
                self.reply(result, channel)
                self.reply('EOF', channel)
                return

            job_id = result
            log.info('Created job %s' % job_id)

            job = self.db.get_job(job_id)
            if job['status'] == 'pending':
                self.reply('%s needs confirmation' % str(job_id), channel)
                self.reply('EOF', channel)

            if job['chatbot_stream'] != 'False':
                self.executor.submit(self._output_handler, job_id, channel)

        return

    @staticmethod
    def _parse_command(text):
        """ Parse message text; return command and arguments """
        words = text.split(' ')
        cmd = words.pop(0)
        args = ' '.join(words)

        return cmd, args

    def _output_handler(self, job_id, channel, stream=True):
        """
        Worker to send the output of a given job_id to a given channel
        params:
         - stream(bool): Toggle streaming output as it comes in
           vs posting when a job finishes. Default True.
        """
        active = False
        prefix = '[%s]' % job_id[-8:]
        log.debug('output handler spawned for job %s' % job_id)

        # sleep on jobs awaiting confirmation
        while not active:
            job = self.db.get_job(job_id)
            if job['status'] == 'canceled':
                return
            if job['status'] != 'pending':
                active = True
            else:
                sleep(1)

        if stream:
            for line in self.db.get_log(job_id, timestamp=False):
                self.reply(prefix + line, channel)
        else:
            msg = ''
            for line in self.db.get_log(job_id, timestamp=False):
                msg += prefix + line + '\n'
            self.reply(msg, channel)

        self.reply('EOF', channel)

    ######
    # Builtin command methods
    ######

    def _confirm(self, arg):
        """ Confirm a pending job """
        job = self.db.get_job(arg)
        if not job:
            return 'no such job id'
        if job['status'] != 'pending':
            return 'job not awaiting confirm'

        self.db.update_job(arg, 'status', 'ready')
        return 'job confirmed'

    def _cancel(self, arg):
        """ Cancel a pending job """
        job = self.db.get_job(arg)
        if not job:
            return 'no such job id'

        ok, result = self.db.cancel_job(arg)
        if not ok:
            return result

        return 'job %s canceled' % job['id']

    def _workers(self, arg):
        """ Show registered job workers """
        workers = self.db.get_workers()
        if not workers:
            return 'no registered workers'
        else:
            return [('%s(%s)' % (w['name'], w['host'])) for w in workers]

    def _jobs(self, arg):
        """ Show jobs by currrent state """
        subcommands = ['pending', 'running', 'completed', 'all']
        if arg not in subcommands:
            return 'argument must be one of %s' % ','.join(subcommands)

        jobs = self.db.get_jobs(status=arg)

        if not jobs:
            return 'no matching jobs found'

        formatted = []
        for j in jobs:
            created = format_time(j['created'])
            formatted.append('%s %s(%s) %s' %
                             (created, j['id'], j['name'], j['status']))

        return formatted

    def _logs(self, args):
        """ Show logs for a given job id """
        if not self.db.get_job(args):
            return 'no matching jobs found'

        return self.db.get_stored_log(args)

    def _help(self, args):
        """ Show this help dialog """
        builtin_cmds = ['Builtin commands:']
        for cmd, func in sorted(self.builtins.items()):
            builtin_cmds.append('  [ %s ]%s' % (cmd, func.__doc__))

        action_cmds = ['Action commands:']
        for cmd in sorted([ a['name'] for a in self.db.get_actions() ]):
            action_cmds.append('  [ %s ]' % cmd)

        return builtin_cmds + action_cmds
        replace('\n', '').replace('  ', '')
