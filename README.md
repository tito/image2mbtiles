# Convert an image into a mbtiles

This script intend is to split an image into tiles in order to build a
deep-zoom image. The result will go into a mbtiles, ready to be embed on
mobiles for example.


## Requirements

- Pillow >= 2.8

## Usage

Syntax:

	$ python image2mbtiles.py source.png output.mbtiles
	
For example, here is the output of a test:

	$ python image2mbtiles.py 001_Baratta_Vue Naples_BnF.tif output.mbtiles
	Analyse: /Users/tito/Downloads/001_Baratta_Vue Naples_BnF.tif
	Size: 30192x10500
	Mode: YCbCr
	Maximum zoom: 7
	Estimated tiles: 6334
	-> Y offset: 22268
	-> Generate zoom 7 (step is 32768)
	  - 1/6334	 zoom:7	ix:0	iy:0	(0x0) step:32768
	-> Y offset: 22268
	-> Generate zoom 6 (step is 16384)
	  - 2/6334	 zoom:6	ix:0	iy:0	(0x0) step:16384
	  - 3/6334	 zoom:6	ix:0	iy:1	(0x16384) step:16384
	  - 4/6334	 zoom:6	ix:1	iy:0	(16384x0) step:16384
	  - 5/6334	 zoom:6	ix:1	iy:1	(16384x16384) step:16384
    ...

Please note that the very first image loading can be slow until the whole image
is loaded. This is a Pillow behavior, and completly normal.


## Using fabric

You can use Fabric in order to automate the conversion. It include a command to
spawn a Digitalocean droplet, install the requirements, copy the image, convert,
and get back the result to your computer.

### Spawn and convert

In order to spawn a droplet, you need to give 2 informations:

- the SSH fingerprint of your computer: you need first to upload your SSH key
  to Digitalocean, and get the fingerprint here. It need to be exported into
  `DO_FINGERPRINT`
- the Digitalocean API Token: create one and export it into `DO_TOKEN`:


	$ DO_FINGERPRINT=XX:XX:XX:XX:XX... DO_TOKEN=8765367828... fab spawn:~/Downloads/IMAG0412.png


The result will saved into output.mbtiles on your local computer. Any existing
result will be replaced.

### Convert

You can also manually convert on any other computer:

	$ fab -H root@1.2.3.4 convert:~/Downloads/IMAG0412.png

Or if needed, you can install requirements and then convert:

	$ fab -H root@1.2.3.4 provision convert:~/Downloads/IMAG0412.png
