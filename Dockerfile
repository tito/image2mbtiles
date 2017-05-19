FROM python:2.7

RUN mkdir -p /usr/src/data/
WORKDIR /usr/src/data/

COPY image2mbtiles.py /usr/src/
RUN pip install Pillow

VOLUME /usr/src/data/

ENTRYPOINT [ "python", "../image2mbtiles.py" ]
