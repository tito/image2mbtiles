# Convert an image into a mbtiles

This script intend is to split an image into tiles in order to build a
deep-zoom image. The result will go into a mbtiles, ready to be embed on
mobiles for example.


## Requirements

- Python 3
- Pillow >= 7.1.2

## Installation

```
pip install -r requirements.txt
```

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
