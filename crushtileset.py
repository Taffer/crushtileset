#!/usr/bin/env python3
#
# Crush a Tiled map's tilesets to only include tiles present in the map.
#
# MIT License, see LICENSE.md for details.
#
# Copyright (c) 2021 Chris Herborth (https://github.com/Taffer/)

import argparse
import base64
import gzip
import math
import os
import os.path
import shutil
import struct
import zlib
import zstandard

from PIL import Image
from xml.etree import ElementTree


class Map:
    def __init__(self, filename):
        self.tree = ElementTree.parse(filename)
        self.root = self.tree.getroot()

    def discover_used(self):
        ''' Discover the used Tile IDs in a given map.
        '''
        used_tiles = []
        data = self.get_data()
        for k in data.keys():
            for row in data[k]:
                for column in row:
                    if column not in used_tiles:
                        used_tiles.append(column)
        used_tiles.sort()

        return used_tiles

    def crush(self, used_tiles, output_tileset_filename):
        # Go through .tmx file:
        # - update tileset source
        # - update data: old index -> new index
        # Write output .tmx file.
        self.set_tileset_source(output_tileset_filename)

        mapping = {}
        idx = 1
        for item in used_tiles:
            mapping[item] = idx
            idx = idx + 1

        self.set_data(mapping)

    def save(self, filename):
        self.tree.write(filename, encoding='UTF-8', xml_declaration=True)

    def get_tileset_filename(self):
        tilesets = self.root.findall('.//tileset')
        if len(tilesets) > 1:
            raise RuntimeError('Only single tileset maps are currently supported, found {0}.'.format(len(tilesets)))

        return tilesets[0].attrib['source']

    def decode_csv(self, data):
        ''' Decode layer data in CSV format.

        CSV data is going to be "height" lines of "width" ints separated
        by commas.
        '''
        the_data = []
        lines = data.text.split()
        for line in lines:
            the_data.append([int(c) for c in line.split(',') if c != ''])

        return the_data

    def decode_base64(self, data):
        ''' Decode layer data in base64 encoded format.
        '''
        the_data = base64.b64decode(data.text)

        # CSV data is organized into rows, so we make this one big row.
        return [[x[0] for x in struct.iter_unpack('<I', the_data)]]

    def decode_base64zlib(self, data):
        ''' Decode layer data in zlib-compressed base64 encoded format.
        '''
        the_data = base64.b64decode(data.text)

        # CSV data is organized into rows, so we make this one big row.
        return [[x[0] for x in struct.iter_unpack('<I', zlib.decompress(the_data))]]

    def decode_base64gzip(self, data):
        ''' Decode layer data in gzip-compressed base64 encoded format.
        '''
        the_data = base64.b64decode(data.text)

        # CSV data is organized into rows, so we make this one big row.
        return [[x[0] for x in struct.iter_unpack('<I', gzip.decompress(the_data))]]

    def decode_base64zstd(self, data):
        ''' Decode layer data in zstandard-compressed base64 encoded format.
        '''
        the_data = base64.b64decode(data.text)

        # CSV data is organized into rows, so we make this one big row.
        return [[x[0] for x in struct.iter_unpack('<I', zstandard.decompress(the_data))]]

    def get_data(self):
        ''' CSV only.
        '''
        layer_data = {}
        for the_layer in self.root.findall('.//layer'):
            layer_id = the_layer.attrib['id']
            layer_width = int(the_layer.attrib['width'])
            layer_height = int(the_layer.attrib['height'])

            data = the_layer.find('data')
            if data.attrib['encoding'] == 'csv':
                layer_data[layer_id] = self.decode_csv(data)
            elif data.attrib['encoding'] == 'base64':
                compression = data.attrib.get('compression', 'none')
                if compression == 'none':
                    layer_data[layer_id] = self.decode_base64(data)
                elif compression == 'zlib':
                    layer_data[layer_id] = self.decode_base64zlib(data)
                elif compression == 'gzip':
                    layer_data[layer_id] = self.decode_base64gzip(data)
                elif compression == 'zstd':
                    layer_data[layer_id] = self.decode_base64zstd(data)
                else:
                    raise RuntimeError('Unsupported compression {0} on layer {1}'.format(compression, layer_id))
            else:
                raise RuntimeError('Unable to parse layer data in {0} format'.format(data.attrib['encoding']))

        return layer_data

    def set_tileset_source(self, source):
        self.root.find('tileset').attrib['source'] = source

    def encode_csv(self, layer):
        lines = []
        for row in layer:
            line = ','.join([str(x) for x in row])
            lines.append(line)
        new_data = ',\n'.join(lines)
        new_data = new_data + '\n'

        return new_data

    def encode_base64(self, layer):
        ''' base64 layers are one huge row, thanks to CSV assuming row data.
        '''
        format = '<' + 'I' * len(layer[0])
        data = struct.pack(format, *(layer[0]))
        return base64.b64encode(data).decode('utf-8')

    def encode_base64zlib(self, layer):
        ''' base64 layers are one huge row, thanks to CSV assuming row data.
        '''
        format = '<' + 'I' * len(layer[0])
        data = zlib.compress(struct.pack(format, *(layer[0])), level=9)
        return base64.b64encode(data).decode('utf-8')

    def encode_base64gzip(self, layer):
        ''' base64 layers are one huge row, thanks to CSV assuming row data.
        '''
        format = '<' + 'I' * len(layer[0])
        data = gzip.compress(struct.pack(format, *(layer[0])), compresslevel=9)
        return base64.b64encode(data).decode('utf-8')

    def encode_base64zstd(self, layer):
        ''' base64 layers are one huge row, thanks to CSV assuming row data.
        '''
        format = '<' + 'I' * len(layer[0])
        data = zstandard.compress(struct.pack(format, *(layer[0])))
        return base64.b64encode(data).decode('utf-8')

    def set_data(self, mapping):
        some_data = self.get_data()

        for the_layer in self.root.findall('.//layer'):
            layer_id = the_layer.attrib['id']
            layer_name = the_layer.attrib['name']
            print('Layer "{0}" (ID: {1})'.format(layer_name, layer_id))

            orig_data = some_data[layer_id]

            for y in range(len(orig_data)):
                for x in range(len(orig_data[y])):
                    orig_data[y][x] = mapping[orig_data[y][x]]

            data = the_layer.find('data')
            if data.attrib['encoding'] == 'csv':
                new_data = self.encode_csv(orig_data)
            elif data.attrib['encoding'] == 'base64':
                compression = data.attrib.get('compression', 'none')
                if compression == 'none':
                    new_data = self.encode_base64(orig_data)
                elif compression == 'zlib':
                    new_data = self.encode_base64zlib(orig_data)
                elif compression == 'gzip':
                    new_data = self.encode_base64gzip(orig_data)
                elif compression == 'zstd':
                    new_data = self.encode_base64zstd(orig_data)
                else:
                    raise RuntimeError('Unsupported compression {0} on layer {1}'.format(compression, layer_id))
            else:
                raise RuntimeError('Unable to write layer {0} data in {1} format'.format(layer_id, data.attrib['encoding']))

            data.text = new_data


class Tileset:
    def __init__(self, filename):
        self.tree = ElementTree.parse(filename)
        self.root = self.tree.getroot()
        self.width = int(self.root.attrib['tilewidth'])
        self.height = int(self.root.attrib['tileheight'])

        if 'columns' in self.root.attrib:
            self.columns = int(self.root.attrib['columns'])
        else:
            self.columns = int(self.root.find('image').attrib['width']) // self.width

    def create_output_texture(self, used_tiles, new_image_size):
        input_texture = Image.open(self.get_texture_filename())
        output_texture = Image.new(input_texture.mode, (new_image_size, new_image_size))

        # Go through each used_tiles:
        # - find its image in input_texture
        # - copy it to output_texture
        # - record its location
        # Write output_texture.
        tile_width = self.get_tile_width()
        tile_height = self.get_tile_height()

        dx = 0  # Offset to write the next tile at.
        dy = 0

        for item in used_tiles:
            tx, ty = self.find_tile(item)
            region = (tx, ty, tx + tile_width, ty + tile_height)
            with input_texture.crop(region) as chunk:
                target = (dx, dy, dx + tile_width, dy + tile_height)
                output_texture.paste(chunk, target)

            dx = dx + tile_width
            if dx + tile_width > new_image_size:
                dx = 0
                dy = dy + tile_height

        return output_texture

    def crush(self, used_tiles, new_image_size, output_texture_filename, output_tileset_filename):
        # Go through .tsx file:
        # - remove terrains
        # - update columns
        # - update image source, width, height
        # Write output .tsx file.
        tile_width = self.get_tile_width()
        tile_height = self.get_tile_height()

        self.remove_terrains(used_tiles)
        self.set_columns(new_image_size // tile_width)
        self.set_source(output_texture_filename, new_image_size, new_image_size)
        self.set_tile_count(len(used_tiles))
        self.set_name(output_tileset_filename)

    def save(self, filename):
        self.tree.write(filename, encoding='UTF-8', xml_declaration=True)

    def get_texture_filename(self):
        return self.root.find('image').attrib['source']

    def get_tile_width(self):
        return self.width

    def get_tile_height(self):
        return self.height

    def count_tiles(self):
        if 'tilecount' in self.root.attrib:
            return int(self.root.attrib['tilecount'])

        return self.columns * int(self.root.find('image').attrib['height']) // self.height

    def count_columns(self):
        if 'columns' in self.root.attrib:
            return int(self.root.attrib['columns'])

        return int(self.root.find('image').attrib['width']) // self.width

    def find_tile(self, index):
        ''' Find the given tile using its 1-based index. Return x, y offsets.
        '''
        index = index - 1
        x = index % self.columns
        y = index // self.columns

        return x * self.width, y * self.height

    def set_name(self, filename):
        parts = os.path.splitext(filename)
        self.root.attrib['name'] = parts[0]

    def set_tile_count(self, count):
        self.root.attrib['tilecount'] = str(count)

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


def backup_filename(filename):
    if os.path.exists(filename):
        shutil.move(filename, filename + '.bak')


def do_crush_png(filename):
    ''' More crushing!
    '''
    orig_size = os.path.getsize(filename)
    crushed_filename = '{0}.crushed'.format(filename)
    os.system('pngcrush -brute {0} {1} > /dev/null 2>&1'.format(filename, crushed_filename))
    crushed_size = os.path.getsize(crushed_filename)
    if crushed_size > 0 and crushed_size < orig_size:
        print('pngcrush succeeded, saved {0} bytes'.format(orig_size - crushed_size))
        os.unlink(filename)
        os.rename(crushed_filename, filename)
    else:
        print('pngcrush failed, keeping existing atlas')


def do_crushing(input_filename, output_filename, crush_pngs):
    input_map = Map(input_filename)
    input_tileset = Tileset(input_map.get_tileset_filename())

    parts = os.path.splitext(output_filename)
    output_tileset_filename = parts[0] + '.tsx'
    output_texture_filename = parts[0] + '.png'

    print('Loaded {0}, tileset is {1}, texture is {2}'.format(input_filename,
                                                              input_map.get_tileset_filename(),
                                                              input_tileset.get_texture_filename()))

    # BUG: The tileset file and tile atlas paths are relative to the map file;
    #      we need to open them with the path to the map file instead.

    used_tiles = input_map.discover_used()

    print('{0} used tiles out of {1}'.format(len(used_tiles), input_tileset.count_tiles()))

    # Find the best texture size. We need a power-of-two texture that'll fit
    # the ceil(sqrt(used_tiles)) * tile_width pixels.
    new_image_size = lookup_size(len(used_tiles), input_tileset.get_tile_width(), input_tileset.get_tile_height())

    print('Building a new {0} x {0} texture'.format(new_image_size))

    output_texture = input_tileset.create_output_texture(used_tiles, new_image_size)

    print('Building new tileset...')
    input_tileset.crush(used_tiles, new_image_size, output_texture_filename, output_tileset_filename)

    print('Building new map...')
    input_map.crush(used_tiles, output_tileset_filename)

    print('Saving files...')
    backup_filename(output_texture_filename)
    output_texture.save(output_texture_filename, 'PNG')
    if crush_pngs:
        do_crush_png(output_texture_filename)

    backup_filename(output_tileset_filename)
    input_tileset.save(output_tileset_filename)

    backup_filename(output_filename)
    input_map.save(output_filename)


def main():
    ''' This is too long for a "real" program.
    '''
    parser = argparse.ArgumentParser(description='Create a texture atlas of only the tiles used in a map.',
                                     epilog='Textures are read out of the map file.')
    parser.add_argument('-o', '--out', metavar='output_map', help='output Map name; default is input_map-crushed', default=None)
    parser.add_argument('--pngcrush', help='Crush the tile atlas with pngcrush.', action='store_true')
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
        do_crushing(args.input_map, args.out, args.pngcrush)
    except RuntimeError as error:
        print('Error: {0}'.format(error))


if __name__ == '__main__':
    main()
