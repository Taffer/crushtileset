#!/usr/bin/env python3
#
# Crush a Tiled map's tilesets to only include tiles present in the map.
#
# MIT License, see LICENSE.md for details.
#
# Copyright (c) 2021 Chris Herborth (https://github.com/Taffer/)

import argparse
import math
import os

from PIL import Image
from xml.etree import ElementTree


class Map:
    def __init__(self, filename):
        self.tree = ElementTree.parse(filename)
        self.root = self.tree.getroot()

    def get_tileset_filename(self):
        return self.root.find('tileset').attrib['source']

    def get_data(self, layer=1):
        the_layer = self.root.find('layer')

        layer_id = the_layer.attrib['id']
        layer_width = int(the_layer.attrib['width'])
        layer_height = int(the_layer.attrib['height'])

        data = the_layer.find('data')
        if data.attrib['encoding'] != 'csv':
            raise RuntimeError('Unable to parse layer data in {0} format'.format(data.attrib['encoding']))

        # CSV data is going to be "height" lines of "width" ints separated by
        # commas.
        lines = data.text.split()
        data = [[int(c) for c in l.split(',')[:-1]] for l in lines]

        return data


class Tileset:
    def __init__(self, filename):
        self.tree = ElementTree.parse(filename)
        self.root = self.tree.getroot()

    def get_texture_filename(self):
        return self.root.find('image').attrib['source']

    def get_tile_width(self):
        return int(self.root.attrib['tilewidth'])

    def get_tile_height(self):
        return int(self.root.attrib['tileheight'])

    def count_tiles(self):
        return int(self.root.attrib['tilecount'])

    def count_columns(self):
        return int(self.root.attrib['columns'])


def lookup_size(num_tiles, tile_width, tile_height):
    if tile_width != tile_height:
        raise RuntimeError('Tile width must match tile height, got {0} x {1}'.format(tile_width, tile_height))

    tile_square = math.ceil(math.sqrt(num_tiles))
    texture_size = tile_square * tile_width

    size = 1
    while size < texture_size:
        size = size << 1

    return size


def main():
    parser = argparse.ArgumentParser(description='Create a texture atlas of only the tiles used in a map.',
                                     epilog='Textures are read out of the map file.')
    parser.add_argument('-o', '--out', metavar='output_map', help='output Map name; default is input_map-crushed', default=None)
    parser.add_argument('input_map', help='input Map name')
    args = parser.parse_args()

    # Sanity checking.
    parts = os.path.splitext(args.input_map)
    if parts[-1] != '.tmx':
        raise SystemExit('Unknown file extension "{0}"'.format(parts[-1]))
    if args.out is None:
        args.out = parts[0] + '-crushed' + parts[1]

    print('Crushing in progress, {0} ➜ {1}...'.format(args.input_map, args.out))

    input_map = Map(args.input_map)
    input_tileset = Tileset(input_map.get_tileset_filename())
    input_texture = Image.open(input_tileset.get_texture_filename())

    print('Loaded {0}, tileset is {1}, texture is {2}'.format(args.input_map,
                                                              input_map.get_tileset_filename(),
                                                              input_tileset.get_texture_filename()))

    used_tiles = []
    for row in input_map.get_data():
        for column in row:
            if column not in used_tiles:
                used_tiles.append(column)
    used_tiles.sort()

    print('{0} used tiles out of {1}'.format(len(used_tiles), input_tileset.count_tiles()))

    # Find the best texture size. We need a power-of-two texture that'll fit
    # the ceil(sqrt(used_tiles)) * tile_width pixels.
    new_image_size = lookup_size(len(used_tiles), input_tileset.get_tile_width(), input_tileset.get_tile_height())

    print('Building a new {0}x{0} texture'.format(new_image_size))

    output_texture = Image.new(input_texture.mode, (new_image_size, new_image_size))

    # Go through each used_tiles:
    # - find its image in input_texture
    # - copy it to output_texture
    # - record its location
    # Write output_texture.

    # Go through .tsx file:
    # - remove terrains
    # - update columns
    # - update image source, width, height
    # Write output .tsx file.

    # Go through .tmx file:
    # - update tileset source
    # - update data: old index -> new index
    # Write output .tmx file.


if __name__ == '__main__':
    main()
