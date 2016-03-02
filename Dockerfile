#multivac

FROM vektorlab/python:3

ENV CONFIG_PATH /config.yml
ENV PYTHONUNBUFFERED true

COPY requirements.txt /
RUN apk --no-cache add build-base python3-dev && \
    pip install -r requirements.txt && \
    apk del build-base python3-dev

COPY . /app
WORKDIR /app

RUN python setup.py install

ENTRYPOINT [ "multivac" ]
