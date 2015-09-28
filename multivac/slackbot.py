import logging

from slacksocket import SlackSocket

from multivac.chatbot import ChatBot

log = logging.getLogger('multivac')


class SlackBot(ChatBot):
    """
    params:
     - slack_token(str):
    """

    def __init__(self, slack_token, redis_host, redis_port):
        print('Starting Slackbot')

        self.slacksocket = SlackSocket(slack_token, event_filters=['message'])
        self.me = self.slacksocket.user

        print('Connected to Slack as %s' % self.me)

        super().__init__(redis_host, redis_port)

    @property
    def messages(self):
        for event in self.slacksocket.events():
            log.debug('saw event %s' % event.json)
            if self.me in event.mentions:
                yield self._parse(event)

    def reply(self, msg, channel):
        # skip any empty messages
        if not msg or msg == 'EOF':
            return

        # make codeblock if message is multiline
        if isinstance(msg, list):
            msg = '```' + '\n'.join(msg) + '```'
        else:
            msg = '`' + msg + '`'

        self.slacksocket.send_msg(msg, channel_name=channel, confirm=False)
        log.debug('sent "%s" to "%s"' % (msg, channel))

    @staticmethod
    def _parse(event):
        """
        Parse slack event, removing @ mention
        """
        words = event.event['text'].split(' ')
        words.pop(0)

        return (' '.join(words), event.event['user'], event.event['channel'])
