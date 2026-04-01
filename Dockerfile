FROM python:3.8-slim-bullseye as build-stage

ARG DEBIAN_FRONTEND=noninteractive
ENV PIP_ROOT_USER_ACTION=ignore

COPY asr_client /asr-client-python/asr_client/
COPY pyproject.toml /asr-client-python/

WORKDIR /asr-client-python

# hadolint ignore=DL3005,DL3008
RUN apt-get update \
    && apt-get dist-upgrade -y \
    && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        portaudio19-dev \
        libportaudio2 \
        python3-pip \
        python3-dev \
    && apt-get clean \
	&& rm -fr /var/lib/apt/lists/* \
	&& rm -fr /var/cache/apt/*

# hadolint ignore=DL3013
RUN pip install --upgrade --no-cache-dir pip \
    && pip install --no-cache-dir .


FROM python:3.8-slim-bullseye

LABEL maintainer="<jan.wozniak@techmo.pl>"

# hadolint ignore=DL3005,DL3008
RUN apt-get update \
    && apt-get dist-upgrade -y \
    && apt-get install -y --no-install-recommends \
        portaudio19-dev \
        libportaudio2 \
    && apt-get clean \
	&& rm -fr /var/lib/apt/lists/* \
	&& rm -fr /var/cache/apt/*

COPY --from=build-stage /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages
COPY --from=build-stage /asr-client-python/asr_client/ /asr-client-python/asr_client/

WORKDIR /asr-client-python

COPY ./docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
