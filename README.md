# Multivac

<p align="center">
  <img src="https://raw.githubusercontent.com/bcicen/multivac/master/logo.png" alt="Statsquid"/>
</p>

Extensible ChatOps framework with an integrated job queue, RESTful API, and built-in support for Slack(with more chat services planned!)

# Quickstart

To get started quickly using Docker:
```bash
git clone https://github.com/bcicen/multivac.git
cd multivac
cp -v sample_config.yml config.yml
```

Create a token for Multivac under "Bots" in the integration section of Slack.

Update config.yml with your Slack token and update docker-compose.yml with your config path:
```bash
sed "s|/path/to|$(pwd)|g" docker-compose.yml
```
and bring up the container stack:
```bash
docker-compose up
```

That's it! You're ready to start talking to Multivac.

Invite Multivac to your channel and type "@multivac: help" to get available commands. Navigate to http://localhost:8000 to view the real-time dashboard.

Full docs are available [here](http://multivac.vektor.nyc/)
