FROM baptwaels/image2mbtiles_dependencies

COPY image2mbtiles.py /usr/src/

ENTRYPOINT [ "python", "image2mbtiles.py" ]
