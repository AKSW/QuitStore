FROM python:3-alpine as builder

LABEL org.opencontainers.image.title="Quit Store" \
      org.opencontainers.image.authors="Norman Radtke <radtke@informatik.uni-leipzig.de>, Natanael Arndt <arndt@informatik.uni-leipzig.de>" \
      org.opencontainers.image.source="https://github.com/AKSW/QuitStore/"

RUN apk --no-cache add \
    git \
    gcc \
    musl-dev \
    libgit2-dev \
    libffi-dev \
    libressl-dev \
    libssh2-dev \
    python3-dev \
    openssl-dev \
    cargo \
    curl

RUN adduser -u 1000 -h /usr/src/app -S quit
USER quit
WORKDIR /usr/src/app

ENV PATH="/usr/src/app/.local/bin:$PATH"
ENV POETRY_VERSION=1.1.12

# In contrast to `pip install --prefer-binary poetry` the install script installs poetry in a
# venv in ~/.local/share/pypoetry/ which can be left behind when copying the files from the build stage
RUN curl -sSL https://install.python-poetry.org \
        | python - --version "${POETRY_VERSION}"

COPY poetry.lock pyproject.toml /usr/src/app/

RUN poetry export -f requirements.txt > requirements.txt
RUN rm ./.local/bin/poetry

USER root
RUN pip install --prefer-binary --no-cache-dir -r requirements.txt

RUN ln -s $( python -c "import site; print(site.getsitepackages()[0])" ) /usr/local/python-site-packages

USER quit

# Set default git user
RUN git config --global user.name QuitStore && git config --global user.email quitstore@example.org

FROM python:3-alpine

RUN adduser -u 1000 -h /usr/src/app -S quit
WORKDIR /usr/src/app

RUN apk --no-cache add \
     libgit2 \
     libssh2

RUN ln -s $( python -c "import site; print(site.getsitepackages()[0])" ) /usr/local/python-site-packages
COPY --from=builder /usr/local/python-site-packages /usr/local/python-site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/src/app/.gitconfig .
RUN mkdir /data && chown quit /data

COPY quit/ /usr/src/app/quit
COPY docker/config.ttl /etc/quit/

USER quit

ENV PATH="/usr/src/app/.local/bin:${PATH}"
ENV SSH_AUTH_SOCK="/var/run/ssh-agent.sock"
ENV QUIT_CONFIGFILE="/etc/quit/config.ttl"

VOLUME /data
VOLUME /etc/quit
EXPOSE 8080

CMD uwsgi --http 0.0.0.0:8080 -w quit.run -b 40960 --pyargv "-vv"
