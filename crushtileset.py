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

    def save(self, filename):
        self.tree.write(filename, encoding='UTF-8', xml_declaration=True)

    def get_tileset_filename(self):
        tilesets = self.root.findall('.//tileset')
        if len(tilesets) > 1:
            raise RuntimeError('Only single tileset maps are currently supported, found {0}.'.format(len(tilesets)))

        return tilesets[0].attrib['source']

    def get_data(self, layer=1):
        ''' Currently only one layer is supported, CSV only.
        '''
        layers = self.root.findall('.//layer')
        if len(layers) > 1:
            raise RuntimeError('Only single layer maps are currently supported, found {0}.'.format(len(layers)))

        the_layer = layers[0]

        layer_id = the_layer.attrib['id']
        layer_width = int(the_layer.attrib['width'])
        layer_height = int(the_layer.attrib['height'])

        data = the_layer.find('data')
        if data.attrib['encoding'] != 'csv':
            raise RuntimeError('Unable to parse layer data in {0} format'.format(data.attrib['encoding']))

        # CSV data is going to be "height" lines of "width" ints separated by
        # commas.
        lines = data.text.split()
        data = []
        for line in lines:
            data.append([int(c) for c in line.split(',') if c != ''])

        return data

    def set_tileset_source(self, source):
        self.root.find('tileset').attrib['source'] = source

    def set_data(self, data, mapping, layer=1):
        ''' Currently only one layer is supported.
        '''
        for y in range(len(data)):
            for x in range(len(data[y])):
                data[y][x] = mapping[data[y][x]]

        lines = []
        for row in data:
            line = ','.join([str(x) for x in row])
            lines.append(line)
        new_data = ',\n'.join(lines)
        new_data = new_data + '\n'

        the_layer = self.root.find('layer')
        data = the_layer.find('data')
        if data.attrib['encoding'] != 'csv':
            raise RuntimeError('Unable to write layer data in {0} format'.format(data.attrib['encoding']))

        layers = self.root.findall('.//layer')
        if len(layers) > 1:
            raise RuntimeError('Only single layer maps are currently supported, found {0}.'.format(len(layers)))

        the_layer = layers[0]
        the_data = the_layer.find('data')
        the_data.text = new_data


class Tileset:
    def __init__(self, filename):
        self.tree = ElementTree.parse(filename)
        self.root = self.tree.getroot()
        self.width = int(self.root.attrib['tilewidth'])
        self.height = int(self.root.attrib['tileheight'])
        self.columns = int(self.root.attrib['columns'])

    def save(self, filename):
        self.tree.write(filename, encoding='UTF-8', xml_declaration=True)

    def get_texture_filename(self):
        return self.root.find('image').attrib['source']

    def get_tile_width(self):
        return self.width

    def get_tile_height(self):
        return self.height

    def count_tiles(self):
        return int(self.root.attrib['tilecount'])

    def count_columns(self):
        return int(self.root.attrib['columns'])

    def find_tile(self, index):
        ''' Find the given tile using its 1-based index. Return x, y offsets.
        '''
        x = index % self.columns
        y = index // self.columns

        return x * self.width, y * self.height

    def set_name(self, filename):
        parts = os.path.splitext(filename)
        self.root.attrib['name'] = parts[0]

    def set_columns(self, columns):
        self.root.attrib['columns'] = str(columns)

    def set_source(self, source, width, height):
        image = self.root.find('image')
        image.attrib['source'] = source
        image.attrib['width'] = str(width)
        image.attrib['height'] = str(height)

    def remove_terrains(self, used_tiles):
        # Delete <terraintypes>, remove "terrain" attribute from all <tile>.
        terraintypes = self.root.find('terraintypes')
        self.root.remove(terraintypes)

        for tile in self.root.findall('tile'):
            tile_id = int(tile.attrib['id'])
            if tile_id in used_tiles:
                new_attrib = {key: value for (key, value) in tile.attrib.items() if key != 'terrain' and key != 'probability'}
                tile.attrib = new_attrib
                tile.attrib['id'] = str(used_tiles.index(tile_id) + 1)
            else:
                self.root.remove(tile)  # Tile not used.


def lookup_size(num_tiles, tile_width, tile_height):
    ''' Look up the texture size suitable for this many tiles of this size.
    '''
    if tile_width != tile_height:
        raise RuntimeError('Tile width must match tile height, got {0} x {1}'.format(tile_width, tile_height))

    tile_square = math.ceil(math.sqrt(num_tiles))
    texture_size = tile_square * tile_width

    # Brute force! These are expected to be small (less than 1,000,000, right?)
    # so this isn't too horrible. There's probably a smarter, more complex
    # way to do this.
    size = 1
    while size < texture_size:
        size = size << 1

    return size


def crush_filename(filename):
    ''' Crushing in progress...
    '''
    parts = os.path.splitext(filename)
    return parts[0] + '-crushed' + parts[1]


def do_crushing(input_filename, output_filename):
    input_map = Map(input_filename)
    input_tileset = Tileset(input_map.get_tileset_filename())
    input_texture = Image.open(input_tileset.get_texture_filename())

    parts = os.path.splitext(output_filename)
    output_tileset_filename = parts[0] + '.tsx'
    output_texture_filename = parts[0] + '.png'

    print('Loaded {0}, tileset is {1}, texture is {2}'.format(input_filename,
                                                              input_map.get_tileset_filename(),
                                                              input_tileset.get_texture_filename()))

    # BUG: The tileset file and tile atlas paths are relative to the map file;
    #      we need to open them with the path to the map file instead.

    used_tiles = []
    data = input_map.get_data()
    for row in data:
        for column in row:
            if column not in used_tiles:
                used_tiles.append(column)
    used_tiles.sort()

    print('{0} used tiles out of {1}'.format(len(used_tiles), input_tileset.count_tiles()))

    # Find the best texture size. We need a power-of-two texture that'll fit
    # the ceil(sqrt(used_tiles)) * tile_width pixels.
    new_image_size = lookup_size(len(used_tiles), input_tileset.get_tile_width(), input_tileset.get_tile_height())

    print('Building a new {0} x {0} texture'.format(new_image_size))

    output_texture = Image.new(input_texture.mode, (new_image_size, new_image_size))

    # Go through each used_tiles:
    # - find its image in input_texture
    # - copy it to output_texture
    # - record its location
    # Write output_texture.
    tile_width = input_tileset.get_tile_width()
    tile_height = input_tileset.get_tile_height()

    dx = 0  # Offset to write the next tile at.
    dy = 0

    for item in used_tiles:
        tx, ty = input_tileset.find_tile(item)
        region = (tx, ty, tx + tile_width, ty + tile_height)
        with input_texture.crop(region) as chunk:
            target = (dx, dy, dx + tile_width, dy + tile_height)
            output_texture.paste(chunk, target)

        dx = dx + tile_width
        if dx + tile_width > new_image_size:
            dx = 0
            dy = dy + tile_height

    output_texture.save(output_texture_filename, 'PNG')

    # Go through .tsx file:
    # - remove terrains
    # - update columns
    # - update image source, width, height
    # Write output .tsx file.
    input_tileset.remove_terrains(used_tiles)
    input_tileset.set_columns(new_image_size // tile_width)
    input_tileset.set_source(output_texture_filename, new_image_size, new_image_size)
    input_tileset.set_name(output_tileset_filename)
    input_tileset.save(output_tileset_filename)

    # Go through .tmx file:
    # - update tileset source
    # - update data: old index -> new index
    # Write output .tmx file.
    input_map.set_tileset_source(output_tileset_filename)

    mapping = {}
    idx = 1
    for item in used_tiles:
        mapping[item] = idx
        idx = idx + 1

    input_map.set_data(data, mapping)
    input_map.save(output_filename)


def main():
    ''' This is too long for a "real" program.
    '''
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
        args.out = crush_filename(args.input_map)

    print('Crushing in progress, {0} ➜ {1}...'.format(args.input_map, args.out))

    try:
        do_crushing(args.input_map, args.out)
    except RuntimeError as error:
        print('Error: {0}'.format(error))


if __name__ == '__main__':
    main()
