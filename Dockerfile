FROM python:3-alpine

MAINTAINER Norman Radtke <radtke@informatik.uni-leipzig.de>
MAINTAINER Natanael Arndt <arndt@informatik.uni-leipzig.de>
ENV SSH_AUTH_SOCK /var/run/ssh-agent.sock

RUN apk update && apk add \
    git \
    gcc \
    musl-dev \
    libgit2-dev \
    libffi-dev \
    libressl-dev \
    libssh2-dev

RUN adduser -h /usr/src/app -S quit
USER quit
WORKDIR /usr/src/app

COPY quit/ /usr/src/app/quit
COPY requirements.txt /usr/src/app/

USER root
COPY docker/config.ttl /etc/quit/
RUN mkdir /data && chown quit /data
USER quit

RUN pip install --no-cache-dir -r requirements.txt \
    && ln -s /usr/src/app/quit/run.py /usr/src/app/.local/bin/quit

ENV QUIT_CONFIGFILE="/etc/quit/config.ttl"

VOLUME /data
VOLUME /etc/quit
EXPOSE 8080

# Set default git user
RUN git config --global user.name QuitStore && git config --global user.email quitstore@example.org

CMD uwsgi --http 0.0.0.0:8080 -w quit.run -b 40960 --pyargv "-vv"
