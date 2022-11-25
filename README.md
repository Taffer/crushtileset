# Moved

This repo is has been replaced by: https://codeberg.org/Taffer/crushtileset

![Logo of the GiveUpGitHub campaign](https://sfconservancy.org/img/GiveUpGitHub.png)

Everything in this repo should be considered out of date.

# crushtileset

Crush a Tiled tileset to only include used tiles.

Tiled is happy using infinity-sized textures as tilesets. You're not likely to
use all of those tiles, and your graphics subsystem will not be co-operative if
you try to render from them (8k x 8k seems like a good rule of thumb for max
texture size? maybe it's higher these days?).

I needed something like this, and none of the existing tools had been
maintained in approximately forever (in Internet Years at least).

## Requirements

Python 3 and:

* ElementTree (this might come standard)
* PIL (try `sudo pip3 install pil` or `sudo apt install python3-pil` or your OS'
  equivalent; advanced users can do it via `virtualenv` or something)
* zstandard (`sudo pip3 install zstandard`)

## Features

* Writes out a new map, new tileset, and new tile atlas.
* Supports multiple layers. Non-tile layers (like object layers) are
  preserved untouched.
* Supports layer data encoded in CSV and base64, as well as base64 encoded
  layers compressed with zlib, gzip, or zstandard.
* Can use `pngcrush` (if it's in your `PATH`) to save more space by crushing
  the tile atlas using *brute force*.

## Limitations

The current version works with *one* tileset only. Future versions will add
support for:

* More than one tileset.
* ???

## Usage

```sh
chrish@skelly$ ./crushtileset.py --help
usage: crushtileset.py [-h] [-o output_map] input_map

Create a texture atlas of only the tiles used in a map.

positional arguments:
  input_map             input Map name

optional arguments:
  -h, --help            show this help message and exit
  -o output_map, --out output_map
                        output Map name; default is input_map-crushed

Textures are read out of the map file.
```

Where `output_map` is the output map file. It'll load the map in `input_map`,
any tilesets used by the map, and any images used by the tilesets. The
`output_map.tmx` will be accompanied by an `output_map.tsx` for the tileset and
an `output_map.png` for the texture atlas. The new files only reference and
include tiles hat were actually used in the `input_map`.

## Bribe me

Want to bribe me to work on multi-layer and multi-tileset support faster?

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/U7U541Y8C)

## License

This is [MIT licensed](LICENSE.md), so go nuts.
