ARG PYTHON_VERSION=3.11
ARG APP_UID=1000
ARG APP_GID=1000
ARG APP_USER=app
ARG APP_HOME=/home/app

FROM python:${PYTHON_VERSION}-slim AS builder

ARG APP_UID=1000
ARG APP_GID=1000
ARG APP_USER=app
ARG APP_HOME=/home/app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=${APP_HOME} \
    PATH=${APP_HOME}/.local/bin:${PATH}

RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -m -d ${APP_HOME} -u ${APP_UID} -g ${APP_GID} -s /bin/bash ${APP_USER} && \
    mkdir -p ${APP_HOME}/dist ${APP_HOME}/Ouroboros && \
    chown -R ${APP_UID}:${APP_GID} ${APP_HOME}

WORKDIR /src

COPY --chown=${APP_UID}:${APP_GID} . .
RUN chown -R ${APP_UID}:${APP_GID} /src

USER ${APP_USER}

RUN python -m pip install --user --no-cache-dir --upgrade pip setuptools wheel
RUN python -m pip wheel . --no-deps --no-build-isolation -w ${APP_HOME}/dist

FROM python:${PYTHON_VERSION}-slim AS runtime

ARG APP_UID=1000
ARG APP_GID=1000
ARG APP_USER=app
ARG APP_HOME=/home/app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=${APP_HOME} \
    PATH=${APP_HOME}/.local/bin:${PATH} \
    OUROBOROS_SERVER_HOST=0.0.0.0 \
    OUROBOROS_SERVER_PORT=8888

RUN apt-get update && \
    apt-get install -y --allow-downgrades --allow-change-held-packages --no-install-recommends \
    git git-lfs vim curl wget && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -m -d ${APP_HOME} -u ${APP_UID} -g ${APP_GID} -s /bin/bash ${APP_USER} && \
    mkdir -p ${APP_HOME}/Ouroboros /tmp/dist && \
    chown -R ${APP_UID}:${APP_GID} ${APP_HOME} /tmp/dist /mnt && \
    ln -s /mnt ${APP_HOME}/mnt

COPY --from=builder --chown=${APP_UID}:${APP_GID} ${APP_HOME}/dist/*.whl /tmp/dist/

USER ${APP_USER}

RUN python -m pip install --user --no-cache-dir /tmp/dist/*.whl

RUN rm -rf /tmp/dist /tmp/*.whl

ENTRYPOINT ["ouroboros-web"]
