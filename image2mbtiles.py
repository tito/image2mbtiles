import argparse
from PIL import Image
from math import log, ceil, floor
from StringIO import StringIO
import sqlite3
Image.MAX_IMAGE_PIXELS = None


def export_level(c, im, max_zoom, zoom, tile_size, counter, max_tiles):
    w, h = im.size
    step = tile_size * (2 ** zoom)
    max_h = tile_size * (2 ** max_zoom)
    y_offset = max_h - h
    print("-> Y offset: {}".format(y_offset))

    print("-> Generate zoom {} (step is {})".format(zoom, step))
    for x in range(0, w, step):
        ix = x // step
        for y in range(0, y_offset, step):
            iy = y // step
            print("  - {}/{}\t zoom:{}\tix:{}\tiy:{}\t({}x{}) step:{}".format(
                counter, max_tiles, zoom, ix, iy, x, y, step))

            cx = max(0, min(w, x))
            cy = max(0, min(h, max_h - y_offset - y - step))
            cx2 = max(0, min(w, x + step))
            cy2 = max(0, min(h, max_h - y_offset - y))

            im2 = im.crop((cx, cy, cx2, cy2))
            dw, dh = im2.size
            if dw < step or dh < step or cy < 0 or cy2 < 0:
                im3 = Image.new("RGBA", (step, step), (0, 0, 0, 0))
                im3.paste(im2, (0, step - dh, dw, step))
                im2 = im3
            elif im.mode not in ("RGBA", "RGB"):
                im3 = Image.new("RGBA", (step, step), (0, 0, 0, 0))
                im3.paste(im2, (0, 0, step, step))
                im2 = im3
            im2 = im2.resize((tile_size, tile_size), Image.BILINEAR)
            #im2.save("output_{}_{}_{}.png".format(max_zoom - zoom, ix, iy))
            sio = StringIO()
            im2.save(sio, format="PNG")
            c.execute("INSERT INTO tiles VALUES (?, ?, ?, ?)",
                      [max_zoom - zoom, ix, iy, buffer(sio.getvalue())])
            counter += 1
    return counter


def _estimate_tiles(w, h, max_zoom, tile_size):
    count = 0
    for zoom in range(max_zoom + 1):
        step = tile_size * (2 ** zoom)
        count += (w // step) * (h // step)
    return count


def export(source, dest, tile_size=256):
    print("Analyse: {}".format(source))
    im = Image.open(source)
    w, h = im.size
    print("Size: {}x{}".format(w, h))
    side = max(w, h)
    print("Mode: {}".format(im.mode))
    max_zoom = int(ceil(log(side / float(tile_size), 2)))
    print("Maximum zoom: {}".format(max_zoom))
    max_tiles = _estimate_tiles(w, h, max_zoom, tile_size)
    counter = 1
    print("Estimated tiles: {}".format(max_tiles))

    conn = sqlite3.connect(dest)
    c = conn.cursor()

    # create database schema
    c.execute('CREATE TABLE metadata (name text, value text)')
    c.execute(
        'CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)')
    # indicies aren't necessary but for large databases with many zoom levels may increase performance
    c.execute(
        'CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)')
    c.execute('CREATE UNIQUE INDEX name ON metadata (name)')

    # fill metadata table with some basic info
    c.execute("INSERT INTO metadata VALUES ('name', ?)", [dest])
    c.execute("INSERT INTO metadata VALUES ('type', 'baselayer')")
    c.execute("INSERT INTO metadata VALUES ('version', '1.0')")
    c.execute("INSERT INTO metadata VALUES ('description', '')")
    c.execute("INSERT INTO metadata VALUES ('format', 'png')")
    c.execute("INSERT INTO metadata VALUES ('minzoom', '0')")
    c.execute("INSERT INTO metadata VALUES ('maxzoom', ?)", [max_zoom])
    c.execute("INSERT INTO metadata VALUES ('projection', 'xy')")

    for zoom in range(max_zoom, -1, -1):
        counter = export_level(c, im, max_zoom, zoom, tile_size, counter,
                               max_tiles)
        conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Convert image to mbtiles")
    parser.add_argument("image", help="Source image")
    parser.add_argument("mbtiles", help="Destination mbtiles")
    args = parser.parse_args()
    export(args.image, args.mbtiles)


if __name__ == "__main__":
    main()
