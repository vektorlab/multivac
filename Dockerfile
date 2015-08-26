#multivac

FROM python:3
MAINTAINER Bradley Cicenas <bradley@vektor.nyc>

ENV CONFIG_PATH /config.yml
ENV PYTHONUNBUFFERED true

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

RUN python setup.py install

ENTRYPOINT [ "multivac" ]
