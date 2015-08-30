# Multivac

<p align="center">
  <img src="https://raw.githubusercontent.com/bcicen/multivac/master/logo.png" alt="Statsquid"/>
</p>

A ChatOps bot for Slack with a integrated job queue and RESTful API

# Quickstart

To get started quickly using Docker:
```bash
git clone https://github.com/bcicen/multivac.git
cd multivac
cp -v sample_config.yml config.yml
```

Create a token for Multivac under "Bots" in the integration section of Slack.
update config.yml with your Slack token and update docker-compose.yml with your config path:
```bash
sed "s|/path/to|$(pwd)|g" docker-compose.yml
```
and bring up the container stack:
```bash
docker-compose up
```

That's it! You're ready to start talking to Multivac. Invite Multivac to your channel and type "@multivac: help" to get available commands. Navigate to http://localhost:8000 to view the real-time dashboard.

# Running

Multivac has three components to launch:

## Job Worker

Performs jobs, collecting and storing their output

```
multivac -c /path/to/config.yml worker
```

## Slackbot

Connects to Slacks Real Time Streaming websocket and watches for mentions, adding predefined jobs to the queue and streaming their output back to Slack.

```
multivac -c /path/to/config.yml slackbot
```

## API

RESTful API that can be used to create and view jobs and their respective logs. Also provides the web interface.

```
multivac -c /path/to/config.yml api
```
