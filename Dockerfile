FROM python:3

MAINTAINER Norman Radtke <radtke@informatik.uni-leipzig.de>
MAINTAINER Natanael Arndt <arndt@informatik.uni-leipzig.de>
ENV SSH_AUTH_SOCK /var/run/ssh-agent.sock

RUN apt-get update && apt-get -y install \
    git \
    cmake \
    libffi-dev \
    libssl-dev \
    libssh2-1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -md /usr/src/app quit
USER quit
WORKDIR /usr/src/app

COPY quit/ /usr/src/app/quit
COPY requirements.txt /usr/src/app/

USER root
RUN pip install --no-cache-dir -r requirements.txt \
    && ln -s /usr/src/app/quit/run.py /usr/local/bin/quit

COPY docker/config.ttl /etc/quit/

ENV QUIT_CONFIGFILE="/etc/quit/config.ttl"
ENV QUIT_LOGFILE="/var/log/quit.log"

RUN mkdir /data && chown quit /data
RUN touch $QUIT_LOGFILE && chown quit $QUIT_LOGFILE

USER quit

VOLUME /data
VOLUME /etc/quit
EXPOSE 8080

# Set default git user
RUN git config --global user.name QuitStore && git config --global user.email quitstore@example.org

CMD uwsgi --http 0.0.0.0:8080 -w quit.run -b 40960 --pyargv "-vv"
