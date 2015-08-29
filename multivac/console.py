import sys
from time import sleep
from termcolor import colored

from multivac.chatbot import ChatBot
from multivac.version import version
from multivac.util import format_time

class ConsoleBot(ChatBot):
    def __init__(self, redis_host, redis_port):
        self.prompt = colored('multivac> ','cyan',attrs=['bold']) 
        self.resprompt = colored('> ','red',attrs=['bold'])
        self._messages =  []
        self._wait = False

        super().__init__(redis_host, redis_port)
        self.run()

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
            [ self._output(l) for l in msg ]
        else:
            self._output(msg)

    def run(self):
        print('Multivac version %s' % (version))
        while True:
            cmdline = input(self.prompt)
            if cmdline.split(' ')[0] == 'exit':
                sys.exit(0)

            self._messages.append((cmdline,'console','console'))
            self._wait = True

            while self._wait:
                sleep(.1)

    def _output(self, text):
        print(self.resprompt + text)

    @staticmethod
    def _print_column(data, has_header=True):
        col_width = max(len(word) for row in data for word in row) + 2
        for row in data:
            print(''.join(word.ljust(col_width) for word in row))

if __name__ == '__main__':
    c = ConsoleBot('localhost', 6379)
