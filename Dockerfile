FROM python:3-alpine as builder

MAINTAINER Norman Radtke <radtke@informatik.uni-leipzig.de>
MAINTAINER Natanael Arndt <arndt@informatik.uni-leipzig.de>

RUN apk --no-cache add \
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

# Set default git user
RUN git config --global user.name QuitStore && git config --global user.email quitstore@example.org

COPY requirements.txt /usr/src/app/

RUN git apply requirements.txt.windows.patch \
    && pip install --no-cache-dir -r requirements.txt \
    && ln -s /usr/src/app/quit/run.py /usr/src/app/.local/bin/quit

FROM python:3-alpine

RUN apk --no-cache add \
     libgit2 \
     libssh2 \
     uwsgi

RUN adduser -h /usr/src/app -S quit
WORKDIR /usr/src/app

COPY quit/ /usr/src/app/quit
COPY docker/config.ttl /etc/quit/
COPY --from=builder /usr/src/app/.local ./.local
COPY --from=builder /usr/src/app/.gitconfig .
RUN mkdir /data && chown quit /data

USER quit

ENV PATH="/usr/src/app/.local/bin:${PATH}"
ENV SSH_AUTH_SOCK="/var/run/ssh-agent.sock"
ENV QUIT_CONFIGFILE="/etc/quit/config.ttl"

VOLUME /data
VOLUME /etc/quit
EXPOSE 8080

CMD uwsgi --http 0.0.0.0:8080 -w quit.run -b 40960 --pyargv "-vv"
