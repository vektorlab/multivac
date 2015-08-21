# Multivac

<p align="center">
  <img src="https://raw.githubusercontent.com/bcicen/multivac/master/logo.png" alt="Statsquid"/>
</p>

A ChatOps bot for Slack with a integrated job queue and RESTful API

# Installing

```bash
git clone https://github.com/bcicen/multivac.git
cd multivac
pip3 install -r requirements.txt
python3 setup.py install
```

# Config

See sample_config.yml for reference

# Running

Multivac has three components:

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

RESTful API that can be used to create and view jobs and their respective logs

```
multivac -c /path/to/config.yml api
```
