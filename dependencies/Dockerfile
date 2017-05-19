FROM python:2.7

# Ghostscript deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ghostscript \
        imagemagick \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/src/
WORKDIR /usr/src/

COPY requirements.txt /usr/src/
RUN pip install -r requirements.txt
