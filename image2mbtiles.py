# coding=utf-8

import argparse
import sys
from PIL import Image, ImageDraw, ImageFont
from math import log, ceil, cos, pi, tan, atan, exp, floor
from io import BytesIO
from os.path import join, dirname, exists
from os import makedirs
import sqlite3


MIN_LATITUDE = -90.
MAX_LATITUDE = 90.
MIN_LONGITUDE = -180.
MAX_LONGITUDE = 180.
DEBUG_TILES = False
RESAMPLE = Image.BOX


def export_level(c, im, max_zoom, zoom, tile_size, counter, max_tiles,
                 tilesdir):
    w, h = im.size
    step = tile_size * (2**zoom)
    max_h = tile_size * (2**max_zoom)
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
            im2 = im2.resize((tile_size, tile_size), RESAMPLE)
            #im2.save("output_{}_{}_{}.png".format(max_zoom - zoom, ix, iy))
            sio = BytesIO()
            im2.save(sio, format="PNG")
            c.execute("INSERT INTO tiles VALUES (?, ?, ?, ?)",
                      [max_zoom - zoom, ix, iy, sio.getvalue()])
            counter += 1

            if tilesdir is not None:
                current_zoom = max_zoom - zoom
                filename = join(tilesdir,
                                str(current_zoom),
                                str(ix),
                                "{}.png".format(flip_y(iy, current_zoom)))
                directory = dirname(filename)
                if not exists(directory):
                    makedirs(directory)
                im2.save(filename, format="PNG")

    return counter


def _estimate_tiles(w, h, max_zoom, tile_size):
    count = 0
    for zoom in range(max_zoom + 1):
        step = tile_size * (2**zoom)
        count += (w // step) * (h // step)
    return count


def export(source, dest, tilesdir, tile_size=256):
    print("Analyse: {}".format(source))
    im = Image.open(source).convert("RGBA")
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
        'CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)'
    )
    # indicies aren't necessary but for large databases with many zoom levels
    # may increase performance
    c.execute(
        'CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)'
    )
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
        counter = export_level(
            c,
            im,
            max_zoom,
            zoom,
            tile_size,
            counter,
            max_tiles,
            tilesdir=tilesdir)
        conn.commit()
    conn.close()


def meters_per_pixel(lat, zoom):
    return 156543.03392 * cos(lat * pi / 180.) / pow(2, zoom)


def clamp(x, minimum, maximum):
    return max(minimum, min(x, maximum))


def get_x(zoom, lon, tile_size):
    """Get the x position on the map using this map source's projection
    (0, 0) is located at the top left.
    """
    lon = clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE)
    return ((lon + 180.) / 360. * pow(2., zoom)) * tile_size


def get_y(zoom, lat, tile_size):
    """Get the y position on the map using this map source's projection
    (0, 0) is located at the top left.
    """
    lat = clamp(-lat, MIN_LATITUDE, MAX_LATITUDE)
    lat = lat * pi / 180.
    return ((1.0 - log(tan(lat) + 1.0 / cos(lat)) / pi) / 2. * pow(2., zoom)
            ) * tile_size


def get_lon(zoom, x, tile_size):
    """Get the longitude to the x position in the map source's projection
    """
    dx = x / float(tile_size)
    lon = dx / pow(2., zoom) * 360. - 180.
    return clamp(lon, MIN_LONGITUDE, MAX_LONGITUDE)


def get_lat(zoom, y, tile_size):
    """Get the latitude to the y position in the map source's projection
    """
    dy = y / float(tile_size)
    n = pi - 2 * pi * dy / pow(2., zoom)
    lat = -180. / pi * atan(.5 * (exp(n) - exp(-n)))
    return clamp(lat, MIN_LATITUDE, MAX_LATITUDE)


def get_row_count(zoom):
    """Get the number of tiles in a row at this zoom level
    """
    if zoom == 0:
        return 1
    return 2 << (zoom - 1)


def get_col_count(zoom):
    """Get the number of tiles in a col at this zoom level
    """
    if zoom == 0:
        return 1
    return 2 << (zoom - 1)


def flip_y(y, z):
    return 2**z - 1 - y


def export_lnglat(source,
                  dest,
                  center,
                  meterswidth,
                  rotation,
                  tilesdir,
                  tile_size=256,
                  px=False):
    lng, lat = map(float, center.split(","))
    print("Analyse: {}".format(source))
    im = Image.open(source).convert("RGBA")
    w, h = im.size
    print("Size: {}x{}".format(w, h))
    print("Current position: {},{}".format(lng, lat))
    im_mpx = meterswidth / float(w)
    print("Current meter per pixels: {}".format(im_mpx))

    if rotation:
        print("Rotation: {}".format(rotation))
        im = im.rotate(rotation, resample=Image.BICUBIC, expand=True)
        w, h = im.size
        print("New size: {}x{}".format(w, h))

    # search for the maximum zoom that would fit the current mpx
    for zoom in range(32, -1, -1):
        target_mpx = meters_per_pixel(lat, zoom)
        if target_mpx > im_mpx:
            break
    target_zoom = zoom + 1
    print("Closest accurate zoom is {}".format(target_zoom))
    if px:
        print("PX mode: activated, adjust image width from the current zoom")
        im_mpx = meters_per_pixel(lat, target_zoom)
        meterswidth = w * im_mpx
        print("PX mode: calculated width: {} meters".format(meterswidth))

    conn = sqlite3.connect(dest)
    c = conn.cursor()

    # create database schema
    c.execute('CREATE TABLE metadata (name text, value text)')
    c.execute(
        'CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)'
    )
    # indicies aren't necessary but for large databases with many zoom levels
    # may increase performance
    c.execute(
        'CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)'
    )
    c.execute('CREATE UNIQUE INDEX name ON metadata (name)')

    # fill metadata table with some basic info
    c.execute("INSERT INTO metadata VALUES ('name', ?)", [dest])
    c.execute("INSERT INTO metadata VALUES ('type', 'baselayer')")
    c.execute("INSERT INTO metadata VALUES ('version', '1.0')")
    c.execute("INSERT INTO metadata VALUES ('description', '')")
    c.execute("INSERT INTO metadata VALUES ('format', 'png')")

    min_zoom = target_zoom
    for zoom in range(target_zoom, -1, -1):
        print("Process zoom {}".format(zoom))
        target_mpx = meters_per_pixel(lat, zoom)
        print("  - Target meter per pixels: {}".format(target_mpx))
        zoom_ratio = im_mpx / target_mpx
        tw = int(w * zoom_ratio)
        th = int(h * zoom_ratio)
        if min(tw, th) <= 1:
            print("  - Stopped now, image less than 1 px")
            min_zoom = zoom + 1
            break
        print("  - Image size: {}x{}".format(tw, th))

        im2 = im.resize((tw, th), RESAMPLE)

        cols = get_col_count(zoom)
        rows = get_row_count(zoom)
        print("  - Maximum number of cols/rows: {}x{}".format(cols, rows))
        center_x = get_x(zoom, lng, tile_size=tile_size)
        center_y = get_y(zoom, lat, tile_size=tile_size)
        print("  - Center in pixels is: {}x{}".format(center_x, center_y))
        x_min = int(center_x - (tw / 2))
        y_min = int(center_y - (th / 2))
        print("  - Minimum x/y: {}x{}".format(x_min, y_min))
        x_max = x_min + tw
        y_max = y_min + th
        print("  - Maximum x/y: {}x{}".format(x_max, y_max))
        tile_col_min = int(floor(x_min / float(tile_size)))
        tile_row_min = int(floor(y_min / float(tile_size)))
        tile_col_max = int(floor(x_max / float(tile_size)))
        tile_row_max = int(floor(y_max / float(tile_size)))
        tile_col_count = max(1, tile_col_max - tile_col_min)
        tile_row_count = max(1, tile_row_max - tile_row_min)
        print("  - Tile range: {}x{} to {}x{}".format(
            tile_col_min, tile_row_min, tile_col_max, tile_row_max))
        print("  - Cols count: {}".format(tile_col_count))
        print("  - Rows count: {}".format(tile_row_count))

        count = tile_col_count * tile_row_count
        index = 0
        if DEBUG_TILES:
            font = ImageFont.truetype("/usr/share/fonts/TTF/Arimo-Regular.ttf",
                                      14)
        for tile_col in range(tile_col_min, tile_col_max + 1):
            for tile_row in range(tile_row_min, tile_row_max + 1):
                index += 1
                print("  - {}/{}\tcol:{} row:{}".format(
                    index, count, tile_col, tile_row))

                tile_x = tile_col * tile_size
                tile_y = tile_row * tile_size

                crop_x = max(0, tile_x - x_min)
                crop_y = max(0, tile_y - y_min)
                crop_x2 = min(tile_x + tile_size, tile_x + tile_size - x_min)
                crop_y2 = min(tile_y + tile_size, tile_y + tile_size - y_min)
                print("  - Crop {}x{} to {}x{}".format(crop_x, crop_y, crop_x2,
                                                       crop_y2))
                crop_w = crop_x2 - crop_x
                crop_h = crop_y2 - crop_y
                print("  - Crop size: {}x{}".format(crop_w, crop_h))

                im3 = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
                if DEBUG_TILES:
                    draw = ImageDraw.Draw(im3)
                    draw.rectangle(
                        (0, 0, tile_size, tile_size),
                        outline="#0000ffff",
                        fill="#ff000066")
                    draw.text(
                        (10, 10),
                        "ZOOM {} - {}x{}".format(zoom, tile_col, tile_row),
                        font=font,
                        fill=(0, 0, 0, 255))
                imc = im2.crop((crop_x, th - crop_y2, crop_x2, th - crop_y))

                box_x = max(0, x_min - tile_x)
                box_y = max(0, y_min - tile_y)
                box_y = 0
                print("  - Box: {}x{}".format(box_x, box_y))
                im3.paste(imc, box=(box_x, box_y), mask=imc)
                sio = BytesIO()
                im3.save(sio, format="PNG")
                c.execute("INSERT INTO tiles VALUES (?, ?, ?, ?)",
                          [zoom, tile_col, tile_row, buffer(sio.getvalue())])
                conn.commit()

                if tilesdir is not None:
                    filename = join(tilesdir,
                                    str(zoom),
                                    str(tile_col),
                                    "{}.png".format(flip_y(tile_row, zoom)))
                    directory = dirname(filename)
                    if not exists(directory):
                        makedirs(directory)
                    im3.save(filename, format="PNG")

    # save metadata
    c.execute("INSERT INTO metadata VALUES ('minzoom', ?)", [min_zoom])
    c.execute("INSERT INTO metadata VALUES ('maxzoom', ?)", [target_zoom])
    c.execute("INSERT INTO metadata VALUES ('center', ?)",
              ["{},{},{}".format(lng, lat, target_zoom - 1)])
    conn.commit()
    conn.close()

def export_lnglat_svg(source,
                      dest,
                      center,
                      meterswidth,
                      tilesdir,
                      minzoom,
                      maxzoom,
                      background_color,
                      tile_size=256):
    lng, lat = map(float, center.split(","))
    print("Analyse: {}".format(source))
    w = float(sh.inkscape("-f", source, "-W"))
    h = float(sh.inkscape("-f", source, "-H"))
    print("Size: {}x{}".format(w, h))
    print("Center: {},{}".format(lng, lat))
    im_mpx = meterswidth / float(w)

    conn = sqlite3.connect(dest)
    c = conn.cursor()

    # create database schema
    c.execute('CREATE TABLE metadata (name text, value text)')
    c.execute(
        'CREATE TABLE tiles (zoom_level integer, tile_column integer, tile_row integer, tile_data blob)'
    )
    # indicies aren't necessary but for large databases with many zoom levels
    # may increase performance
    c.execute(
        'CREATE UNIQUE INDEX tile_index ON tiles (zoom_level, tile_column, tile_row)'
    )
    c.execute('CREATE UNIQUE INDEX name ON metadata (name)')

    # fill metadata table with some basic info
    c.execute("INSERT INTO metadata VALUES ('name', ?)", [dest])
    c.execute("INSERT INTO metadata VALUES ('type', 'baselayer')")
    c.execute("INSERT INTO metadata VALUES ('version', '1.0')")
    c.execute("INSERT INTO metadata VALUES ('description', '')")
    c.execute("INSERT INTO metadata VALUES ('format', 'png')")

    import subprocess
    process = subprocess.Popen([
        "inkscape", "--shell"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    while True:
        ret = process.stdout.read(1)
        if ret != "\n":
            continue
        ret = process.stdout.read(1)
        if ret != ">":
            continue
        break

    for zoom in range(minzoom, maxzoom + 1):
        print("Process zoom {}".format(zoom))

        target_mpx = meters_per_pixel(lat, zoom)

        print("  - Target meter per pixels: {}".format(target_mpx))
        zoom_ratio = im_mpx / target_mpx
        tw = w * zoom_ratio
        th = h * zoom_ratio
        print("  - Image size: {}x{}".format(tw, th))

        cols = get_col_count(zoom)
        rows = get_row_count(zoom)
        print("  - Maximum number of cols/rows: {}x{}".format(cols, rows))
        center_x = get_x(zoom, lng, tile_size=tile_size)
        center_y = get_y(zoom, lat, tile_size=tile_size)
        print("  - Center in pixels is: {}x{}".format(center_x, center_y))
        x_min = center_x - (tw / 2)
        y_min = center_y - (th / 2)
        print("  - Minimum x/y: {}x{}".format(x_min, y_min))
        x_max = x_min + tw
        y_max = y_min + th
        print("  - Maximum x/y: {}x{}".format(x_max, y_max))
        tile_col_min = int(floor(x_min / float(tile_size)))
        tile_row_min = int(floor(y_min / float(tile_size)))
        tile_col_max = int(floor(x_max / float(tile_size)))
        tile_row_max = int(floor(y_max / float(tile_size)))
        tile_col_count = max(1, tile_col_max - tile_col_min)
        tile_row_count = max(1, tile_row_max - tile_row_min)
        print("  - Tile range: {}x{} to {}x{}".format(
            tile_col_min, tile_row_min, tile_col_max, tile_row_max))
        print("  - Cols count: {}".format(tile_col_count))
        print("  - Rows count: {}".format(tile_row_count))

        count = (tile_col_count + 1) * (tile_row_count + 1)
        index = 0
        for tile_col in range(tile_col_min, tile_col_max + 1):
            for tile_row in range(tile_row_min, tile_row_max + 1):
                index += 1
                print("  - {}/{}\tcol:{} row:{}".format(
                    index, count, tile_col, tile_row))

                tile_x = tile_col * tile_size
                tile_y = tile_row * tile_size

                crop_x = tile_x - x_min
                crop_y = tile_y - y_min
                crop_x2 = tile_x + tile_size - x_min
                crop_y2 = tile_y + tile_size - y_min
                print("  - Crop {}x{} to {}x{}".format(crop_x, crop_y, crop_x2,
                                                       crop_y2))
                filename = join(tilesdir,
                                str(zoom),
                                str(tile_col),
                                "{}.png".format(flip_y(tile_row, zoom)))
                directory = dirname(filename)
                if not exists(directory):
                    makedirs(directory)

                ratio = 1 / zoom_ratio
                crop_x *= ratio
                crop_y *= ratio
                crop_x2 *= ratio
                crop_y2 *= ratio

                export_area = "{}:{}:{}:{}".format(
                    crop_x, crop_y, crop_x2, crop_y2)

                cmd = "-f '{}' -e {} -a {} -w {} -h {} -b '{}'\n".format(
                    source, filename, export_area, tile_size, tile_size, background_color
                )
                process.stdin.write(cmd)
                while True:
                    ret = process.stdout.read(1)
                    if ret != "\n":
                        continue
                    ret = process.stdout.read(1)
                    if ret != ">":
                        continue
                    break
                # sh.inkscape("-f", source, "-e", filename, "-a", export_area,
                #             "-w", tile_size, "-h", tile_size,
                #             "-b", "#030303")

                with open(filename, "rb") as fd:
                    data = buffer(fd.read())

                c.execute("INSERT INTO tiles VALUES (?, ?, ?, ?)",
                          [zoom, tile_col, tile_row, data])
                conn.commit()

    # save metadata
    c.execute("INSERT INTO metadata VALUES ('minzoom', ?)", [minzoom])
    c.execute("INSERT INTO metadata VALUES ('maxzoom', ?)", [maxzoom])
    c.execute("INSERT INTO metadata VALUES ('center', ?)",
              ["{},{},{}".format(lng, lat, maxzoom - 1)])
    conn.commit()
    conn.close()

    process.terminate()


def main():
    parser = argparse.ArgumentParser(description="Convert image to mbtiles")
    parser.add_argument(
        "--center",
        default=None,
        help="Longitude/Latitude center of the image (lng,lat format)")
    parser.add_argument(
        "--meterswidth", type=float, help="Width size in meters")
    parser.add_argument(
        "--rotation",
        type=float,
        default=0.,
        help="Angle of the image (rotation will be applied on the image)")
    parser.add_argument(
        "--tilesdir", type=str, help="Directory where to store tiles")
    parser.add_argument(
        "--px",
        action="store_true",
        help=
        "After finding the zoom level, don't resize the initial image (pixel perfect mode)"
    )
    parser.add_argument(
        "--minzoom", type=int, help="Minimum zoom to generate (svg only)")
    parser.add_argument(
        "--maxzoom", type=int, help="Maximum zoom to generate (svg only)")
    parser.add_argument(
        "--background", type=str, default="#030303", help="Background color of the map (svg only)")
    parser.add_argument("image", help="Source image")
    parser.add_argument("mbtiles", help="Destination mbtiles")
    args = parser.parse_args()

    if args.image.endswith(".svg"):
        if not args.maxzoom or not args.minzoom:
            print("ERROR: an SVG source require a minzoom and maxzoom")
            sys.exit(1)
        export_lnglat_svg(
            args.image,
            args.mbtiles,
            center=args.center,
            meterswidth=args.meterswidth,
            tilesdir=args.tilesdir,
            minzoom=args.minzoom,
            maxzoom=args.maxzoom,
            background_color=args.background)

    elif (args.center or args.meterswidth):
        if not args.center:
            print("ERROR: meterswidth require center option too")
            sys.exit(1)
        if not args.meterswidth:
            print("ERROR: center option requires meterswidth option too")
            sys.exit(1)
        export_lnglat(
            args.image,
            args.mbtiles,
            center=args.center,
            meterswidth=args.meterswidth,
            rotation=args.rotation,
            tilesdir=args.tilesdir,
            px=args.px)
    else:
        export(args.image, args.mbtiles, tilesdir=args.tilesdir)


if __name__ == "__main__":
    main()
