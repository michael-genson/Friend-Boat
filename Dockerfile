###############################################
# Base Image
###############################################
FROM python:3.12-slim as python-base

ENV PROJECT_HOME="/app"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=. \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

###############################################
# Builder Image
###############################################
FROM python-base as builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential \
    gnupg gnupg2 gnupg1

###############################################
# Production Image
###############################################
FROM python-base as production
ENV PRODUCTION=true
ENV TESTING=false

ARG COMMIT
ENV GIT_COMMIT_HASH=$COMMIT

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    ffmpeg

RUN pip install uv

# copy app
COPY ./friend_boat $PROJECT_HOME/friend_boat
COPY ./uv.lock ./pyproject.toml $PROJECT_HOME/

# install runtime deps
WORKDIR $PROJECT_HOME
RUN uv sync --no-dev

VOLUME [ "$PROJECT_HOME/data/" ]
ENV APP_PORT=9000

EXPOSE ${APP_PORT}

COPY ./docker_entry.sh $PROJECT_HOME/run.sh
RUN chmod +x $PROJECT_HOME/run.sh
ENTRYPOINT $PROJECT_HOME/run.sh
