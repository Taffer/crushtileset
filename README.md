# crushtileset

Crush a Tiled tileset to only include used tiles.

Tiled is happy using infinity-sized textures as tilesets. You're not likely to
use all of those tiles, and your graphics subsystem will no be co-operative if
you try to render from them (8k x 8k seems like a good rule of thumb for max
texture size).

I needed something like this, and none of the existing tools had been
maintained in approximately forever (in Internet Years at least).

## Requirements

* ElementTree
* PIL

## Limitations

The current version works with *one* tileset and *one* layer only. Future
versions will add support for:

* Map data in formats other than CSV.
* More than one layer.
* More than one tileset.
* ???

## Usage

TBD, but something like:

```sh
crushtileset --out output map.tmx
```

Where `output` is the output directory. It'll load the map in `map.tmx`, any
tilesets used by the maps, and any images used by the tilesets. The `output`
directory will have a new `map.tmx`, new tilesets, and new images written
that only contain the tiles from each tileset that are actually used.

* Initially only works with one tileset and one map layer, will expand as
  necessary in the future.

## Bribe me

Want to bribe me to work on multi-layer and multi-tileset support faster?

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/U7U541Y8C)

## License

This is [MIT licensed](LICENSE.md), so go nuts.
