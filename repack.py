#!/usr/bin/env python3
#
# Use PIL to repack a ridiculous PNG into something texture sized.
#
# Assumes the PNG is full of 32x32 tiles.

from PIL import Image


def main():
    im = Image.open('terrain-map-v7.png')

    result = Image.new(im.mode, (4096, 4096))
    result_x = 0
    result_y = 0

    y = 0
    while y < im.height:
        x = 0
        while x < im.width:
            region = (x, y, x + 32, y + 32)
            with im.crop(region) as chunk:
                target = (result_x, result_y, result_x + 32, result_y + 32)
                result.paste(chunk, target)

            result_x = result_x + 32
            if result_x >= 4096:
                result_x = 0
                result_y = result_y + 32

            x = x + 32
        y = y + 32

    result.save('result.png', 'PNG')


if __name__ == '__main__':
    main()
