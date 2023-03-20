FROM docker.io/python:3-slim as python
ENV PYTHONUNBUFFERED=true
WORKDIR /app

RUN apt-get update && \
    apt-get -y install \
    libgit2-1.1 \
    libssh-4 \
    && rm -rf /var/lib/apt/lists/*


RUN useradd -md /usr/src/app quit
WORKDIR /usr/src/app




FROM python as builder

RUN apt-get update && \
    apt-get -y install \
    git \
    gcc \
    libffi-dev \
    libssh-dev \
    python3-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY dist/quit-*.whl .
RUN pip install --progress-bar=off quit-*.whl

RUN ln -s $( python -c "import site; print(site.getsitepackages()[0])" ) /usr/local/python-site-packages

USER quit

# Set default git user
RUN git config --global user.name QuitStore && git config --global user.email quitstore@example.org




FROM python as runtime

LABEL org.opencontainers.image.title="Quit Store" \
      org.opencontainers.image.authors="Norman Radtke <radtke@informatik.uni-leipzig.de>, Natanael Arndt <arndt@informatik.uni-leipzig.de>" \
      org.opencontainers.image.source="https://github.com/AKSW/QuitStore/"



RUN ln -s $( python -c "import site; print(site.getsitepackages()[0])" ) /usr/local/python-site-packages
COPY --from=builder /usr/local/python-site-packages /usr/local/python-site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/src/app/.gitconfig .
RUN mkdir /data && chown quit /data

COPY quit/ /usr/src/app/quit

USER quit

ENV PATH="/usr/src/app/.local/bin:${PATH}"
ENV SSH_AUTH_SOCK="/var/run/ssh-agent.sock"

VOLUME /data
VOLUME /etc/quit
EXPOSE 8080

CMD uwsgi --http 0.0.0.0:8080 -w quit.run -b 40960 --pyargv "-vv -t /data"
