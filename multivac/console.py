import os
import sys
import readline
from time import sleep
from termcolor import colored

from multivac.chatbot import ChatBot
from multivac.version import version
from multivac.util import format_time


class ConsoleBot(ChatBot):

    def __init__(self, redis_host, redis_port):
        self._messages = []
        self._wait = False

        super().__init__(redis_host, redis_port)

        self.init_readline()
        self.input_loop()

    @property
    def messages(self):
        while True:
            try:
                yield self._messages.pop(0)
            except IndexError:
                sleep(.1)

    def reply(self, msg, channel):
        if msg == 'EOF':
            self._wait = False
            return
        if isinstance(msg, list):
            [self._output(l) for l in msg]
        else:
            self._output(msg)

    def init_readline(self):
        self.prompt = colored('multivac> ', 'cyan', attrs=['bold'])
        self.resprompt = colored('> ', 'red', attrs=['bold'])

        self._history_file = os.path.expanduser('~/.multivac_console')
        if os.path.isfile(self._history_file):
            readline.read_history_file(self._history_file)

        readline.set_completer(self._autocomplete)
        readline.parse_and_bind('tab: complete')

    def input_loop(self):
        print('Multivac version %s' % (version))
        while True:
            try:
                inputline = input(self.prompt)
                if not inputline:
                    continue

                # append to messages queue for processing
                self._messages.append((inputline, 'console', 'console'))

                # wait until output of command is completed
                self._wait = True
                while self._wait:
                    sleep(.1)

            except (EOFError, KeyboardInterrupt):
                break

        self.exit()

    def exit(self):
        readline.write_history_file(self._history_file)
        print('\n')
        sys.exit(0)

    def _output(self, text):
        print(self.resprompt + text)

    def _autocomplete(self, text, state):
        allcmds = [c for c in self.builtins]
        allcmds += [a['name'] for a in self.db.get_actions()]
        match = [c for c in allcmds if c and c.startswith(text)]
        match.append(None)

        return match[state]

    @staticmethod
    def _print_column(data, has_header=True):
        col_width = max(len(word) for row in data for word in row) + 2
        for row in data:
            print(''.join(word.ljust(col_width) for word in row))

if __name__ == '__main__':
    c = ConsoleBot('localhost', 6379)
