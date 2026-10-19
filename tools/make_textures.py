import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "main" / "resources" / "assets" / "makercraft" / "textures" / "block"


def write_png(path, pixels):
    height = len(pixels)
    width = len(pixels[0])
    raw = b"".join(b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in pixels)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def fill(color):
    return [[color for _ in range(16)] for _ in range(16)]


def rect(img, x0, y0, x1, y1, color):
    for y in range(y0, y1):
        for x in range(x0, x1):
            img[y][x] = color


def arduino_block():
    teal = (0, 128, 138)
    dark = (0, 84, 92)
    gold = (232, 188, 74)
    silver = (214, 222, 228)
    metal = (150, 160, 168)
    chip = (22, 26, 30)
    pin = (196, 202, 208)
    led = (48, 210, 96)
    white = (236, 248, 246)
    img = fill(teal)
    rect(img, 0, 0, 16, 1, gold)
    rect(img, 0, 15, 16, 16, gold)
    for x in range(0, 16, 2):
        img[1][x] = dark
        img[14][x] = dark
    rect(img, 1, 3, 5, 7, silver)
    rect(img, 1, 4, 4, 6, metal)
    img[3][13] = led
    img[3][14] = white
    rect(img, 5, 5, 12, 12, chip)
    for y in range(6, 11):
        img[y][4] = pin
        img[y][12] = pin
    rect(img, 7, 7, 10, 10, (70, 78, 86))
    img[12][8] = (196, 48, 52)
    return img


def arduino_output(lit):
    body = (32, 36, 44)
    edge = (18, 20, 26)
    screw = (120, 126, 134)
    copper = (184, 112, 58)
    if lit:
        led = (255, 52, 42)
        core = (255, 214, 96)
        ring = (196, 36, 40)
    else:
        led = (122, 28, 36)
        core = (168, 48, 52)
        ring = (72, 18, 24)
    img = fill(body)
    rect(img, 0, 0, 16, 16, edge)
    rect(img, 1, 1, 15, 15, body)
    for x, y in ((2, 2), (13, 2), (2, 13), (13, 13)):
        img[y][x] = screw
    for y in range(4, 12):
        for x in range(4, 12):
            dx, dy = x - 7.5, y - 7.5
            dist = dx * dx + dy * dy
            if dist <= 2.2:
                img[y][x] = core
            elif dist <= 8.5:
                img[y][x] = led
            elif dist <= 13:
                img[y][x] = ring
    img[13][5] = copper
    img[13][6] = copper
    img[13][9] = copper
    img[13][10] = copper
    return img


def computer_front():
    frame = (18, 22, 20)
    bezel = (28, 34, 32)
    screen = (8, 28, 24)
    text = (90, 220, 160)
    img = fill(frame)
    rect(img, 1, 1, 15, 14, bezel)
    rect(img, 2, 2, 14, 12, screen)
    for x, y in ((4, 4), (5, 4), (6, 4), (8, 4), (4, 6), (5, 6), (9, 6), (10, 6), (4, 8), (7, 8), (8, 8)):
        img[y][x] = text
    img[13][7] = (31, 168, 122)
    img[13][8] = (31, 168, 122)
    return img


def computer_side():
    body = (22, 26, 24)
    edge = (12, 14, 13)
    img = fill(body)
    rect(img, 0, 0, 16, 1, edge)
    rect(img, 0, 15, 16, 16, edge)
    rect(img, 0, 0, 1, 16, edge)
    return img


def computer_top():
    body = (26, 32, 30)
    stripe = (31, 168, 122)
    img = fill(body)
    rect(img, 2, 7, 14, 9, stripe)
    return img


write_png(OUT / "arduino_block.png", arduino_block())
write_png(OUT / "arduino_output.png", arduino_output(False))
write_png(OUT / "arduino_output_on.png", arduino_output(True))
write_png(OUT / "computer_front.png", computer_front())
write_png(OUT / "computer_side.png", computer_side())
write_png(OUT / "computer_top.png", computer_top())
print(OUT)
