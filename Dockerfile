# Adapted from https://github.com/orgs/python-poetry/discussions/1879#discussioncomment-216865

FROM python:3.12.3-slim AS python-base

ENV \
    # Python
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    \
    # Pip
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    \
    # Poetry
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    \
    # Paths
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    \
    # User
    APP_UID=1000 \
    APP_GID=1000

# Prepend Poetry and virtual environment to path
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Setup app user
RUN groupadd appgroup -g $APP_GID
RUN useradd appuser -u $APP_UID -g $APP_GID -m
USER appuser:appgroup

# --------------------
# Stage: builder-base
# --------------------

FROM python-base AS builder-base

# Install needed packages as root
USER root
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        curl \
        build-essential

# Install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python -

# Copy project requirement files here to ensure they will be cached.
USER appuser:appgroup
WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./

# Install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry install --no-dev

# -------------------
# Stage: development
# -------------------

FROM python-base AS development
ENV FASTAPI_ENV=development

# Copy in our built poetry and virtual environment
COPY --from=builder-base $POETRY_HOME $POETRY_HOME
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
COPY ./docker/entrypoint.sh /usr/bin/prbot

# Quicker install as runtime deps are already installed
WORKDIR $PYSETUP_PATH
RUN poetry install

# Will become mountpoint of our code
WORKDIR /app
EXPOSE 8000
CMD ["prbot", "dev"]

# ------------------
# Stage: production
# ------------------

FROM python-base AS production
ENV FASTAPI_ENV=production

COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH
# Copy the pyproject.toml file so the version is in sync.
COPY ./pyproject.toml /app/pyproject.toml
COPY ./manage.py /app/manage.py
COPY ./prbot /app/prbot
COPY ./docker/entrypoint.sh /usr/bin/prbot

# Try to optimize startup times
RUN python -m compileall $PYSETUP_PATH
USER root
RUN python -m compileall /app && chown appuser:appgroup -R /app 
USER appuser:appgroup

WORKDIR /app
EXPOSE 8000
CMD ["prbot", "serve"]