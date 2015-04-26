from fabric.api import run, settings, put, get
import digitalocean
import os
from time import sleep
from uuid import uuid4


def spawn(filename):
    rid = str(uuid4())
    fingerprint = os.environ["DO_FINGERPRINT"]
    token = os.environ["DO_TOKEN"]
    droplet = digitalocean.Droplet(
        token=token,
        name="Image2mbtiles-{}".format(rid),
        region="ams3",
        image="ubuntu-14-04-x64",
        size_slug="8gb",
        ssh_keys=[fingerprint],
        private_networking=False,
        ipv6=False,
        backups=False)

    print("create the droplet")
    droplet.create()
    droplet.load()

    print("wait the droplet to be active")
    while droplet.status != "active":
        print("- status: {}".format(droplet.status))
        sleep(10)
        droplet.load()
    print("- active!")

    sleep(10)

    try:
        with settings(
            host_string="root@{}".format(droplet.ip_address),
            use_ssh_config=True,
            disable_known_hosts=True):
            provision()
            transform(filename)
    finally:
        print("destroy the droplet")
        droplet.destroy()


def provision():
    run("apt-get update")
    run("apt-get install -y python-pip "
        "build-essential python-dev libpng-dev libjpeg-dev "
        "libtiff-dev")
    run("pip install pillow")


def transform(filename):
    print("Copy source filename: {}".format(filename))
    put("image2mbtiles.py", ".")
    basefn, ext = filename.rsplit(".", -1)
    put(filename, "source.{}".format(ext))
    run("python image2mbtiles.py source.{} output.mbtiles".format(ext))
    get("output.mbtiles", "output.mbtiles")
