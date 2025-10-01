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
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# prepend poetry to path
ENV PATH="$POETRY_HOME/bin:$PATH"

###############################################
# Builder Image
###############################################
FROM python-base as builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential \
    gnupg gnupg2 gnupg1

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
ENV POETRY_VERSION=1.5.1
RUN curl -sSL https://install.python-poetry.org | python -

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

# copying poetry and venv into image
COPY --from=builder-base $POETRY_HOME $POETRY_HOME

# copy app
COPY ./friend_boat $PROJECT_HOME/friend_boat
COPY ./poetry.lock ./pyproject.toml $PROJECT_HOME/

# install runtime deps
WORKDIR $PROJECT_HOME
RUN poetry install --only main

VOLUME [ "$PROJECT_HOME/data/" ]
ENV APP_PORT=9000

EXPOSE ${APP_PORT}

COPY ./docker_entry.sh $PROJECT_HOME/run.sh
RUN chmod +x $PROJECT_HOME/run.sh
ENTRYPOINT $PROJECT_HOME/run.sh
