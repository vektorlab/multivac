# Multivac

<p align="center">
  <img width="500px" src="https://raw.githubusercontent.com/bcicen/multivac/master/logo.png" alt="multivac"/>
</p>

Extensible ChatOps framework with an integrated job queue, RESTful API, and built-in support for Slack.

# Quickstart

To get started quickly using Docker:
- Clone the repo and create a copy of the sample config
```bash
git clone https://github.com/bcicen/multivac.git
cd multivac
cp -v sample_config.yml config.yml
```

- Update config.yml with a Slack token created under "Bots" in the integration section of Slack

- Update docker-compose.yml with your config path:
```bash
sed "s|/path/to|$(pwd)|g" docker-compose.yml
```
- And bring up the container stack:
```bash
docker-compose up
```

That's it! You're ready to start talking to Multivac.

Invite Multivac to your channel and type `@multivac: help` to get available commands. Navigate to [http://localhost:8000](http://localhost:8000) to view the real-time dashboard.

Full docs are available [here](http://multivac.vektor.nyc/)
