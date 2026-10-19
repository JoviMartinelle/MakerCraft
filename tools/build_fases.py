# Gera o campus das 10 fases no save superplano do MakerCraft.
import gzip
import math
import os
import shutil
import struct
import uuid
import zlib
from io import BytesIO
from pathlib import Path

import nbtlib
from nbtlib import Byte, ByteArray, Compound, File, Int, List, Long, LongArray, String

SAVE = Path(os.environ.get(
    "MAKERCRAFT_SAVE",
    r"C:\Users\Nicolas\curseforge\minecraft\Instances\MakerCraft (1)\saves\MakerCraft",
))
REGION = SAVE / "region" / "r.0.0.mca"
BACKUP = SAVE / "region" / "r.0.0.mca.pre-fases"

MIN_Y = -64
DIM = "ResourceKey[minecraft:dimension / minecraft:overworld]"

# Planta baixa. O jogador anda para +X.
Z0, Z1 = 18, 32
ZC = 25
FL = -61  # piso dos pavilhões de baixo (bloco)
FU = -52  # piso da ala de cima (bloco)


def signed64(v):
    v &= (1 << 64) - 1
    if v >= (1 << 63):
        v -= 1 << 64
    return v


def pack_values(values, bits):
    if bits == 0:
        return None
    per = 64 // bits
    mask = (1 << bits) - 1
    nlongs = math.ceil(len(values) / per)
    longs = [0] * nlongs
    for i, val in enumerate(values):
        longs[i // per] |= (val & mask) << ((i % per) * bits)
    return [signed64(v) for v in longs]


def unpack_values(longs, bits, count):
    if bits == 0:
        return [0] * count
    per = 64 // bits
    mask = (1 << bits) - 1
    out = []
    for i in range(count):
        word = int(longs[i // per]) & ((1 << 64) - 1)
        out.append((word >> ((i % per) * bits)) & mask)
    return out


def palette_key(name, props):
    items = tuple(sorted((props or {}).items()))
    return (name, items)


def decode_section_blocks(section):
    bs = section["block_states"]
    palette = []
    for entry in bs["palette"]:
        props = {}
        if "Properties" in entry:
            props = {str(k): str(v) for k, v in entry["Properties"].items()}
        palette.append((str(entry["Name"]), props))
    count = 4096
    if len(palette) <= 1 or "data" not in bs:
        indices = [0] * count
    else:
        bits = max(4, math.ceil(math.log2(len(palette))))
        indices = unpack_values(bs["data"], bits, count)
    return palette, indices


def encode_section_blocks(section, palette, indices):
    bs = section["block_states"]
    new_palette = List[Compound]()
    for name, props in palette:
        entry = Compound({"Name": String(name)})
        if props:
            entry["Properties"] = Compound({k: String(v) for k, v in sorted(props.items())})
        new_palette.append(entry)
    bs["palette"] = new_palette
    if "data" in bs:
        del bs["data"]
    if len(palette) > 1:
        bits = max(4, math.ceil(math.log2(len(palette))))
        packed = pack_values(indices, bits)
        bs["data"] = LongArray[Long]([Long(v) for v in packed])


def load_region(path):
    data = path.read_bytes()
    chunks = {}
    for i in range(1024):
        offset = struct.unpack(">I", b"\x00" + data[i * 4 : i * 4 + 3])[0]
        count = data[i * 4 + 3]
        if not offset or not count:
            continue
        start = offset * 4096
        length = struct.unpack(">I", data[start : start + 4])[0]
        comp = data[start + 4]
        raw = data[start + 5 : start + 4 + length]
        if comp == 2:
            body = zlib.decompress(raw)
        elif comp == 1:
            body = gzip.decompress(raw)
        else:
            body = raw
        nbt = File.parse(BytesIO(body))
        chunks[i] = nbt
    return chunks


def save_region(path, chunks):
    blobs = {}
    for i, nbt in chunks.items():
        buf = BytesIO()
        nbt.write(buf)
        blobs[i] = zlib.compress(buf.getvalue())
    header = bytearray(8192)
    payload = bytearray()
    sector = 2
    for i in range(1024):
        if i not in blobs:
            continue
        compressed = blobs[i]
        length = len(compressed) + 1
        count = math.ceil((length + 4) / 4096)
        header[i * 4 : i * 4 + 3] = sector.to_bytes(3, "big")
        header[i * 4 + 3] = count
        ts = int(Path(path).stat().st_mtime) if path.exists() else 0
        header[4096 + i * 4 : 4096 + i * 4 + 4] = struct.pack(">I", ts & 0xFFFFFFFF)
        chunk = struct.pack(">I", length) + bytes([2]) + compressed
        chunk += bytes((count * 4096) - len(chunk))
        payload.extend(chunk)
        sector += count
    path.write_bytes(bytes(header) + bytes(payload))


class World:
    def __init__(self, chunks):
        self.chunks = chunks
        self.edits = {}
        self.block_entities = {}
        self.touched = set()

    def get(self, x, y, z):
        if (x, y, z) in self.edits:
            name, props, _ = self.edits[(x, y, z)]
            return name, props
        chunk = self.chunks[self._index(x, z)]
        section = self._section(chunk, y >> 4)
        palette, indices = decode_section_blocks(section)
        local = ((y - (y >> 4) * 16) * 256) + ((z & 15) * 16) + (x & 15)
        name, props = palette[indices[local]]
        return name, props

    def set(self, x, y, z, name, props=None, be=None):
        props = {k: str(v) for k, v in (props or {}).items()}
        self.edits[(x, y, z)] = (name, props, be)
        self.touched.add(self._index(x, z))

    def fill(self, x0, y0, z0, x1, y1, z1, name, props=None):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, name, props)

    def _index(self, x, z):
        cx, cz = x >> 4, z >> 4
        if cx < 0 or cz < 0 or cx > 31 or cz > 31:
            raise ValueError(f"fora da região: {x} {z}")
        return cx + cz * 32

    def _section(self, chunk, sy):
        for section in chunk["sections"]:
            if int(section["Y"]) == sy:
                return section
        raise KeyError(sy)

    def apply(self):
        grouped = {}
        for (x, y, z), value in self.edits.items():
            grouped.setdefault(self._index(x, z), []).append((x, y, z, value))
        for index, items in grouped.items():
            chunk = self.chunks[index]
            by_section = {}
            for x, y, z, value in items:
                by_section.setdefault(y >> 4, []).append((x, y, z, value))
            for sy, edits in by_section.items():
                section = self._section(chunk, sy)
                palette, indices = decode_section_blocks(section)
                keys = [palette_key(n, p) for n, p in palette]
                for x, y, z, (name, props, _be) in edits:
                    key = palette_key(name, props)
                    if key not in keys:
                        keys.append(key)
                        palette.append((name, props))
                    pi = keys.index(key)
                    local_y = y - sy * 16
                    local = local_y * 256 + (z & 15) * 16 + (x & 15)
                    indices[local] = pi
                encode_section_blocks(section, palette, indices)
                for light_key in ("SkyLight", "BlockLight"):
                    if light_key in section:
                        del section[light_key]
            self._rewrite_block_entities(chunk, index)
            self._rewrite_heightmaps(chunk)
            chunk["isLightOn"] = Byte(0)

    def _rewrite_block_entities(self, chunk, index):
        cx = index % 32
        cz = index // 32
        kept = []
        for be in chunk["block_entities"]:
            x, y, z = int(be["x"]), int(be["y"]), int(be["z"])
            if (x, y, z) in self.edits:
                continue
            if (x >> 4) == cx and (z >> 4) == cz:
                kept.append(be)
        for (x, y, z), (_n, _p, be) in self.edits.items():
            if be is not None and self._index(x, z) == index:
                kept.append(be)
        chunk["block_entities"] = List[Compound](kept)

    def _rewrite_heightmaps(self, chunk):
        columns = [[(None, None, None, None) for _ in range(16)] for _ in range(16)]
        for section in chunk["sections"]:
            if "block_states" not in section:
                continue
            sy = int(section["Y"])
            palette, indices = decode_section_blocks(section)
            for ly in range(16):
                y = sy * 16 + ly
                base = ly * 256
                for lz in range(16):
                    for lx in range(16):
                        name = palette[indices[base + lz * 16 + lx]][0]
                        if name in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
                            continue
                        surface, ocean, motion, no_leaves = columns[lz][lx]
                        if surface is None or y > surface:
                            surface = y
                        if motion is None or y > motion:
                            motion = y
                        if name not in ("minecraft:water", "minecraft:lava") and (ocean is None or y > ocean):
                            ocean = y
                        if "leaves" not in name and (no_leaves is None or y > no_leaves):
                            no_leaves = y
                        columns[lz][lx] = (surface, ocean, motion, no_leaves)
        maps = {
            "WORLD_SURFACE": 0,
            "OCEAN_FLOOR": 1,
            "MOTION_BLOCKING": 2,
            "MOTION_BLOCKING_NO_LEAVES": 3,
        }
        for key, slot in maps.items():
            vals = []
            for lz in range(16):
                for lx in range(16):
                    top = columns[lz][lx][slot]
                    vals.append(0 if top is None else top + 65)
            packed = pack_values(vals, 9)
            chunk["Heightmaps"][key] = LongArray[Long]([Long(v) for v in packed])


def roundtrip_check(chunks):
    chunk = chunks[0]
    section = next(s for s in chunk["sections"] if int(s["Y"]) == -4)
    palette, indices = decode_section_blocks(section)
    # grass local y = -61 - (-64) = 3, index at 0,0
    name = palette[indices[3 * 256]][0]
    if name != "minecraft:grass_block":
        raise SystemExit(f"decoder falhou, y=-61 é {name}")
    encode_section_blocks(section, palette, indices)
    palette2, indices2 = decode_section_blocks(section)
    if indices != indices2 or palette != palette2:
        raise SystemExit("roundtrip do palette falhou")


def be_sign(x, y, z, lines, glowing=False):
    messages = [String(lines[i] if i < len(lines) else "") for i in range(4)]
    empty = [String("") for _ in range(4)]
    return Compound(
        {
            "id": String("minecraft:sign"),
            "x": Int(x),
            "y": Int(y),
            "z": Int(z),
            "is_waxed": Byte(0),
            "keepPacked": Byte(0),
            "front_text": Compound(
                {
                    "has_glowing_text": Byte(1 if glowing else 0),
                    "color": String("white" if glowing else "black"),
                    "messages": List[String](messages),
                }
            ),
            "back_text": Compound(
                {
                    "has_glowing_text": Byte(0),
                    "color": String("black"),
                    "messages": List[String](empty),
                }
            ),
        }
    )


def be_chest(x, y, z, items, title):
    slots = List[Compound]()
    for i, (item_id, count) in enumerate(items):
        slots.append(Compound({"Slot": Byte(i), "id": String(item_id), "count": Int(count)}))
    return Compound(
        {
            "id": String("minecraft:chest"),
            "x": Int(x),
            "y": Int(y),
            "z": Int(z),
            "CustomName": String(title),
            "keepPacked": Byte(0),
            "Items": slots,
        }
    )


def be_dispenser(x, y, z):
    return Compound(
        {
            "id": String("minecraft:dispenser"),
            "x": Int(x),
            "y": Int(y),
            "z": Int(z),
            "Items": List[Compound]([]),
        }
    )


class Builder:
    def __init__(self, world):
        self.w = world
        self.outputs = []
        self.arduinos = []

    def box(self, x0, x1, z0, z1, y0, y1, name, props=None):
        self.w.fill(x0, y0, z0, x1, y1, z1, name, props)

    def air(self, x0, x1, y0, y1, z0, z1):
        self.box(x0, x1, z0, z1, y0, y1, "minecraft:air")

    def sign(self, x, y, z, facing, lines, wood="oak", glowing=False):
        self.w.set(
            x,
            y,
            z,
            f"minecraft:{wood}_wall_sign",
            {"facing": facing},
            be_sign(x, y, z, lines, glowing),
        )

    def chest(self, x, y, z, facing, items, title):
        self.w.set(
            x,
            y,
            z,
            "minecraft:chest",
            {"facing": facing},
            be_chest(x, y, z, items, title),
        )

    def door(self, x, y, z, kind, facing="east"):
        self.w.set(x, y, z, f"minecraft:{kind}_door", {"facing": facing, "half": "lower", "hinge": "left", "open": "false"})
        self.w.set(x, y + 1, z, f"minecraft:{kind}_door", {"facing": facing, "half": "upper", "hinge": "left", "open": "false"})

    def output(self, number, x, y, z):
        self.w.set(x, y, z, "makercraft:arduino_output", {"powered": "false"})
        self.outputs.append((number, x, y, z))

    def arduino(self, x, y, z):
        self.w.set(x, y, z, "makercraft:arduino_block", {"powered": "false"})
        self.arduinos.append((x, y, z))

    def lamp_post(self, x, z, y):
        self.w.set(x, y, z, "minecraft:stone_bricks")
        self.w.set(x, y + 1, z, "minecraft:stone_brick_wall", {"up": "true", "east": "none", "west": "none", "north": "none", "south": "none"})
        self.w.set(x, y + 2, z, "minecraft:stone_brick_wall", {"up": "true", "east": "none", "west": "none", "north": "none", "south": "none"})
        self.w.set(x, y + 3, z, "minecraft:lantern", {"hanging": "false"})

    def tree(self, x, z, y, log, leaves):
        for dy in range(5):
            self.w.set(x, y + dy, z, log, {"axis": "y"})
        leaf_props = {"persistent": "true", "distance": "1", "waterlogged": "false"}
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                for dy in range(3, 6):
                    if abs(dx) + abs(dz) > 3:
                        continue
                    if dx == 0 and dz == 0 and dy < 5:
                        continue
                    self.w.set(x + dx, y + dy, z + dz, leaves, leaf_props)
        self.w.set(x, y + 6, z, leaves, leaf_props)

    def path_strip(self, x0, x1, y, z, block):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.w.set(x, y, z, block)

    def pavilion(self, x0, x1, floor_y, theme, lit=True):
        """Casca de um pavilhão. x0/x1 e Z0/Z1 são as paredes externas, inclusive."""
        ceil = floor_y + 8
        w = self.w
        log = theme["log"]
        plank = theme["plank"]
        trim = theme["trim"]
        floor = theme["floor"]
        accent = theme["accent"]
        # fundação
        if floor_y == FL:
            self.box(x0, x1, Z0, Z1, floor_y - 2, floor_y - 1, "minecraft:stone_bricks")
            self.box(x0 - 1, x1 + 1, Z0 - 1, Z1 + 1, floor_y, floor_y, trim)
        else:
            # sobrado: forro visto por baixo e pilares
            self.box(x0, x1, Z0, Z1, floor_y - 1, floor_y - 1, "minecraft:dark_oak_planks")
            self.box(x0, x1, Z0, Z1, floor_y, floor_y, floor)
            for px in (x0, x1):
                for pz in (Z0, Z1):
                    self.box(px, px, pz, pz, FL, floor_y - 1, "minecraft:stone_bricks")
            for px in range(x0 + 5, x1, 6):
                self.box(px, px, Z0, Z0, FL, floor_y - 1, "minecraft:stone_bricks")
                self.box(px, px, Z1, Z1, FL, floor_y - 1, "minecraft:stone_bricks")
        # piso interno
        self.box(x0 + 1, x1 - 1, Z0 + 1, Z1 - 1, floor_y, floor_y, floor)
        # paredes
        self.box(x0, x1, Z0, Z1, floor_y + 1, ceil, plank)
        # cantos em tronco
        for px, pz in ((x0, Z0), (x0, Z1), (x1, Z0), (x1, Z1)):
            self.box(px, px, pz, pz, floor_y, ceil, log, {"axis": "y"})
        # rodapé e friso
        self.box(x0, x1, Z0, Z0, floor_y + 1, floor_y + 1, trim)
        self.box(x0, x1, Z1, Z1, floor_y + 1, floor_y + 1, trim)
        self.box(x0, x0, Z0, Z1, floor_y + 1, floor_y + 1, trim)
        self.box(x1, x1, Z0, Z1, floor_y + 1, floor_y + 1, trim)
        # teto
        self.box(x0, x1, Z0, Z1, ceil, ceil, theme["roof"])
        # beiral
        slab = theme["slab"]
        self.box(x0 - 1, x1 + 1, Z0 - 1, Z0 - 1, ceil, ceil, slab, {"type": "bottom"})
        self.box(x0 - 1, x1 + 1, Z1 + 1, Z1 + 1, ceil, ceil, slab, {"type": "bottom"})
        self.box(x0 - 1, x0 - 1, Z0, Z1, ceil, ceil, slab, {"type": "bottom"})
        self.box(x1 + 1, x1 + 1, Z0, Z1, ceil, ceil, slab, {"type": "bottom"})
        # platibanda baixa
        self.box(x0, x1, Z0, Z0, ceil + 1, ceil + 1, trim)
        self.box(x0, x1, Z1, Z1, ceil + 1, ceil + 1, trim)
        # esvazia o interior
        self.air(x0 + 1, x1 - 1, floor_y + 1, ceil - 1, Z0 + 1, Z1 - 1)
        # janelas nas paredes norte e sul
        if lit:
            for x in range(x0 + 3, x1 - 2, 4):
                for z, face in ((Z0, "south"), (Z1, "north")):
                    self.w.set(x, floor_y + 3, z, "minecraft:glass_pane", {"east": "true", "west": "true", "north": "false", "south": "false"})
                    self.w.set(x, floor_y + 4, z, "minecraft:glass_pane", {"east": "true", "west": "true", "north": "false", "south": "false"})
                    self.w.set(x, floor_y + 2, z, theme["stair"], {"facing": face, "half": "top", "shape": "straight"})
        # carpete central
        for x in range(x0 + 2, x1 - 1):
            self.w.set(x, floor_y + 1, ZC, theme["carpet"])
        # luminárias
        if lit:
            for x in range(x0 + 4, x1 - 2, 6):
                self.w.set(x, ceil - 1, ZC, "minecraft:iron_chain", {"axis": "y"})
                self.w.set(x, ceil - 2, ZC, theme.get("lantern", "minecraft:lantern"), {"hanging": "true"})
        # detalhe de cobre / acento no eixo
        self.w.set(x0, ceil + 1, ZC, accent)
        self.w.set(x1, ceil + 1, ZC, accent)
        return {"x0": x0, "x1": x1, "floor": floor_y, "ceil": ceil, "feet": floor_y + 1}

    def arch(self, x, floor_y, theme):
        """Abre um vão de 3x4 na parede x, no centro."""
        ceil_clear = floor_y + 5
        for z in (ZC - 1, ZC, ZC + 1):
            for y in range(floor_y + 1, ceil_clear):
                self.w.set(x, y, z, "minecraft:air")
        # moldura
        log = theme["log"]
        for y in range(floor_y + 1, ceil_clear):
            self.w.set(x, y, ZC - 2, log, {"axis": "y"})
            self.w.set(x, y, ZC + 2, log, {"axis": "y"})
        for z in range(ZC - 2, ZC + 3):
            self.w.set(x, ceil_clear, z, log, {"axis": "z"})

    def iron_gate(self, x, floor_y, theme):
        for z in (ZC - 1, ZC, ZC + 1):
            for y in range(floor_y + 1, floor_y + 5):
                self.w.set(x, y, z, "minecraft:air")
        log = theme["log"]
        for y in range(floor_y + 1, floor_y + 5):
            self.w.set(x, y, ZC - 2, log, {"axis": "y"})
            self.w.set(x, y, ZC + 2, log, {"axis": "y"})
        for z in range(ZC - 1, ZC + 2):
            self.w.set(x, floor_y + 4, z, theme["trim"])
            self.w.set(x, floor_y + 1, z, "minecraft:air")
            self.w.set(x, floor_y + 2, z, "minecraft:air")
            self.w.set(x, floor_y + 3, z, "minecraft:air")
        # fecha as laterais do vão e deixa só o centro
        self.w.set(x, floor_y + 1, ZC - 1, theme["trim"])
        self.w.set(x, floor_y + 2, ZC - 1, theme["trim"])
        self.w.set(x, floor_y + 3, ZC - 1, theme["trim"])
        self.w.set(x, floor_y + 1, ZC + 1, theme["trim"])
        self.w.set(x, floor_y + 2, ZC + 1, theme["trim"])
        self.w.set(x, floor_y + 3, ZC + 1, theme["trim"])
        self.door(x, floor_y + 1, ZC, "iron", "east")

    def guide(self, x0, x1, floor_y, z, block="minecraft:red_terracotta"):
        y = floor_y
        for x in range(min(x0, x1), max(x0, x1) + 1):
            self.w.set(x, y, z, block)
            name, _ = self.w.get(x, floor_y + 1, z)
            if name.endswith("carpet"):
                self.w.set(x, floor_y + 1, z, "minecraft:air")

    def guide_z(self, x, z0, z1, floor_y, block="minecraft:red_terracotta"):
        for z in range(min(z0, z1), max(z0, z1) + 1):
            self.w.set(x, floor_y, z, block)
            name, _ = self.w.get(x, floor_y + 1, z)
            if name.endswith("carpet") or name == "minecraft:redstone_wire":
                self.w.set(x, floor_y + 1, z, "minecraft:air")

    def garden(self, x0, x1, ground=FL):
        for x in range(x0, x1 + 1):
            for z in range(Z0, Z1 + 1):
                if ZC - 1 <= z <= ZC + 1:
                    block = "minecraft:polished_andesite" if z == ZC else "minecraft:stone_bricks"
                    self.w.set(x, ground, z, block)
                elif (x + z) % 7 == 0:
                    self.w.set(x, ground, z, "minecraft:mossy_stone_bricks")
                else:
                    self.w.set(x, ground, z, "minecraft:grass_block", {"snowy": "false"})
                    if (x * 3 + z) % 11 == 0:
                        self.w.set(x, ground + 1, z, "minecraft:azure_bluet")
                    elif (x + z * 5) % 13 == 0:
                        self.w.set(x, ground + 1, z, "minecraft:open_eyeblossom")
                    elif (x * 7 + z) % 17 == 0:
                        self.w.set(x, ground + 1, z, "minecraft:firefly_bush")
                    elif (x + z) % 9 == 0:
                        self.w.set(x, ground + 1, z, "minecraft:short_dry_grass")
        self.lamp_post(x0 + 1, Z0 + 1, ground)
        self.lamp_post(x0 + 1, Z1 - 1, ground)

    def bridge(self, x0, x1, floor_y):
        for x in range(x0, x1 + 1):
            for z in range(Z0, Z1 + 1):
                if ZC - 2 <= z <= ZC + 2:
                    self.w.set(x, floor_y, z, "minecraft:stone_bricks")
                    self.w.set(x, floor_y - 1, z, "minecraft:deepslate_bricks")
                if z in (ZC - 2, ZC + 2):
                    self.w.set(x, floor_y + 1, z, "minecraft:stone_brick_wall", {"up": "true", "east": "none", "west": "none", "north": "none", "south": "none"})
        for x in (x0, x1):
            self.w.set(x, floor_y + 1, ZC, "minecraft:lantern", {"hanging": "false"})
            # tira a parede do centro se o poste caiu no corrimão
        for px in (x0, (x0 + x1) // 2, x1):
            self.box(px, px, Z0, Z0, FL, floor_y - 1, "minecraft:stone_bricks")
            self.box(px, px, Z1, Z1, FL, floor_y - 1, "minecraft:stone_bricks")


THEMES = {
    "lobby": dict(log="minecraft:stripped_pale_oak_log", plank="minecraft:pale_oak_planks", floor="minecraft:pale_oak_planks", trim="minecraft:calcite", roof="minecraft:smooth_quartz", accent="minecraft:copper_block", stair="minecraft:pale_oak_stairs", slab="minecraft:pale_oak_slab", carpet="minecraft:white_carpet", lantern="minecraft:lantern"),
    "p1": dict(log="minecraft:stripped_oak_log", plank="minecraft:oak_planks", floor="minecraft:oak_planks", trim="minecraft:stripped_oak_log", roof="minecraft:oak_planks", accent="minecraft:cut_copper", stair="minecraft:oak_stairs", slab="minecraft:oak_slab", carpet="minecraft:orange_carpet", lantern="minecraft:lantern"),
    "p2": dict(log="minecraft:stripped_spruce_log", plank="minecraft:spruce_planks", floor="minecraft:deepslate_tiles", trim="minecraft:polished_deepslate", roof="minecraft:deepslate_tiles", accent="minecraft:redstone_block", stair="minecraft:spruce_stairs", slab="minecraft:spruce_slab", carpet="minecraft:red_carpet", lantern="minecraft:soul_lantern"),
    "p3": dict(log="minecraft:stripped_birch_log", plank="minecraft:smooth_sandstone", floor="minecraft:cut_sandstone", trim="minecraft:smooth_sandstone", roof="minecraft:sandstone", accent="minecraft:gold_block", stair="minecraft:sandstone_stairs", slab="minecraft:sandstone_slab", carpet="minecraft:yellow_carpet", lantern="minecraft:lantern"),
    "p4": dict(log="minecraft:prismarine", plank="minecraft:prismarine_bricks", floor="minecraft:dark_prismarine", trim="minecraft:prismarine", roof="minecraft:prismarine_bricks", accent="minecraft:sea_lantern", stair="minecraft:prismarine_brick_stairs", slab="minecraft:prismarine_brick_slab", carpet="minecraft:cyan_carpet", lantern="minecraft:lantern"),
    "p5": dict(log="minecraft:polished_blackstone", plank="minecraft:blackstone", floor="minecraft:polished_blackstone", trim="minecraft:polished_blackstone_bricks", roof="minecraft:blackstone", accent="minecraft:chiseled_polished_blackstone", stair="minecraft:blackstone_stairs", slab="minecraft:blackstone_slab", carpet="minecraft:black_carpet", lantern="minecraft:lantern"),
    "p6": dict(log="minecraft:stripped_cherry_log", plank="minecraft:cherry_planks", floor="minecraft:calcite", trim="minecraft:cherry_planks", roof="minecraft:cherry_planks", accent="minecraft:copper_bulb", stair="minecraft:cherry_stairs", slab="minecraft:cherry_slab", carpet="minecraft:pink_carpet", lantern="minecraft:lantern"),
    "p7": dict(log="minecraft:stripped_dark_oak_log", plank="minecraft:deepslate_bricks", floor="minecraft:deepslate_bricks", trim="minecraft:polished_deepslate", roof="minecraft:deepslate_bricks", accent="minecraft:copper_grate", stair="minecraft:deepslate_brick_stairs", slab="minecraft:deepslate_brick_slab", carpet="minecraft:gray_carpet", lantern="minecraft:soul_lantern"),
    "p8": dict(log="minecraft:stripped_mangrove_log", plank="minecraft:mud_bricks", floor="minecraft:packed_mud", trim="minecraft:mud_bricks", roof="minecraft:mud_bricks", accent="minecraft:tuff_bricks", stair="minecraft:mud_brick_stairs", slab="minecraft:mud_brick_slab", carpet="minecraft:brown_carpet", lantern="minecraft:lantern"),
    "p9": dict(log="minecraft:purpur_pillar", plank="minecraft:end_stone_bricks", floor="minecraft:purpur_block", trim="minecraft:end_stone_bricks", roof="minecraft:purpur_block", accent="minecraft:crying_obsidian", stair="minecraft:purpur_stairs", slab="minecraft:purpur_slab", carpet="minecraft:purple_carpet", lantern="minecraft:lantern"),
    "p10": dict(log="minecraft:quartz_pillar", plank="minecraft:quartz_block", floor="minecraft:smooth_quartz", trim="minecraft:chiseled_quartz_block", roof="minecraft:quartz_block", accent="minecraft:sea_lantern", stair="minecraft:quartz_stairs", slab="minecraft:quartz_slab", carpet="minecraft:light_gray_carpet", lantern="minecraft:lantern"),
}


def copper_bulb_off():
    return {"lit": "false", "powered": "false"}


def build(world):
    b = Builder(world)
    # praça
    for x in range(2, 18):
        for z in range(14, 37):
            world.set(x, FL, z, "minecraft:stone_bricks")
            if 16 <= z <= 34 and x % 5 == 0 and z % 5 == 0:
                world.set(x, FL, z, "minecraft:mossy_stone_bricks")
    for x in range(6, 16):
        for z in (ZC - 1, ZC, ZC + 1):
            world.set(x, FL, z, "minecraft:polished_andesite" if z == ZC else "minecraft:stone_bricks")
    # fonte
    for x in range(5, 10):
        for z in range(18, 23):
            world.set(x, FL, z, "minecraft:stone_bricks")
            world.set(x, FL + 1, z, "minecraft:stone_brick_wall", {"up": "true", "east": "none", "west": "none", "north": "none", "south": "none"})
    for x in range(6, 9):
        for z in range(19, 22):
            world.set(x, FL, z, "minecraft:stone")
            world.set(x, FL + 1, z, "minecraft:water", {"level": "0"})
    world.set(7, FL + 1, 20, "minecraft:sea_lantern")
    b.tree(12, 18, FL + 1, "minecraft:pale_oak_log", "minecraft:pale_oak_leaves")
    b.tree(12, 32, FL + 1, "minecraft:cherry_log", "minecraft:cherry_leaves")
    b.lamp_post(4, 16, FL)
    b.lamp_post(4, 34, FL)
    b.lamp_post(15, 16, FL)
    b.lamp_post(15, 34, FL)
    # bancos
    for z in (17, 33):
        world.set(8, FL + 1, z, "minecraft:pale_oak_stairs", {"facing": "north" if z == 33 else "south", "half": "bottom", "shape": "straight"})
        world.set(9, FL + 1, z, "minecraft:pale_oak_stairs", {"facing": "north" if z == 33 else "south", "half": "bottom", "shape": "straight"})

    # ----- LOBBY -----
    lobby = b.pavilion(18, 36, FL, THEMES["lobby"])
    b.arch(18, FL, THEMES["lobby"])
    b.arch(36, FL, THEMES["lobby"])
    # mobília
    for z in range(21, 30, 2):
        world.set(19, FL + 1, z, "minecraft:bookshelf")
    world.set(20, FL + 1, 21, "minecraft:lectern", {"facing": "east"})
    world.set(20, FL + 1, 23, "minecraft:cartography_table")
    world.set(20, FL + 1, 27, "minecraft:crafting_table")
    world.set(20, FL + 1, 29, "minecraft:potted_cherry_sapling")
    b.chest(19, FL + 1, 31, "east", [("minecraft:bread", 32), ("minecraft:cooked_beef", 16)], "Despensa")
    b.sign(19, FL + 2, ZC - 3, "east", ["MAKERCRAFT", "Oficina de fuga", "Ande para o leste", "Leia as placas"])
    b.sign(19, FL + 2, ZC + 3, "east", ["Sobrevivência", "Os baús têm", "o que falta", "Não quebre saída"])
    b.sign(19, FL + 3, ZC, "east", ["Sem o Arduino", "o mapa abre", "Saídas ligam só", "com o código"])

    # ----- FASE 1 -----
    b.garden(37, 42)
    p1 = b.pavilion(43, 60, FL, THEMES["p1"])
    b.arch(43, FL, THEMES["p1"])
    b.iron_gate(60, FL, THEMES["p1"])
    b.guide(46, 59, FL, ZC - 3)
    b.guide_z(59, ZC - 3, ZC, FL)
    world.set(46, FL, ZC - 3, "minecraft:chiseled_stone_bricks")
    b.sign(44, FL + 2, ZC, "east", ["Fase 1", "Abra a porta", "Alavanca no quadro", "Pó no chão rosa"])
    b.sign(45, FL + 2, ZC - 4, "south", ["Alavanca", "neste quadro", "", ""])
    b.chest(44, FL + 1, 30, "west", [("minecraft:redstone", 64), ("minecraft:lever", 2)], "Fase 1")
    # quadro da alavanca
    world.set(45, FL + 1, ZC - 4, "minecraft:chiseled_stone_bricks")
    world.set(45, FL + 2, ZC - 4, "minecraft:chiseled_stone_bricks")

    # ----- FASE 2 -----
    b.garden(61, 66)
    b.pavilion(67, 90, FL, THEMES["p2"])
    b.arch(67, FL, THEMES["p2"])
    b.iron_gate(78, FL, THEMES["p2"])
    b.iron_gate(90, FL, THEMES["p2"])
    b.guide(70, 77, FL, ZC - 3)
    b.guide_z(77, ZC - 3, ZC, FL)
    world.set(70, FL, ZC - 3, "minecraft:chiseled_stone_bricks")
    b.guide(82, 89, FL, ZC + 3, "minecraft:red_terracotta")
    b.guide_z(89, ZC + 3, ZC, FL, "minecraft:red_terracotta")
    b.output(1, 81, FL + 1, ZC + 3)
    world.set(81, FL, ZC + 3, "minecraft:chiseled_copper")
    b.sign(68, FL + 2, ZC, "east", ["Fase 2", "1ª porta: alavanca", "2ª porta: Saída 1", "Clique direito nela"])
    b.sign(80, FL + 2, ZC + 4, "north", ["Saída 1", "Pó até a porta", "do fundo", ""])
    b.chest(68, FL + 1, 30, "west", [("minecraft:redstone", 64), ("minecraft:lever", 2)], "Fase 2")
    world.set(70, FL + 1, ZC - 4, "minecraft:chiseled_stone_bricks")
    world.set(70, FL + 2, ZC - 4, "minecraft:chiseled_stone_bricks")
    b.sign(70, FL + 3, ZC - 4, "south", ["Alavanca", "aqui", "", ""])

    # ----- FASE 3 -----
    b.garden(91, 96)
    b.pavilion(97, 128, FL, THEMES["p3"])
    b.arch(97, FL, THEMES["p3"])
    b.iron_gate(106, FL, THEMES["p3"])
    b.iron_gate(128, FL, THEMES["p3"])
    b.guide(100, 105, FL, ZC - 3, "minecraft:yellow_terracotta")
    b.guide_z(105, ZC - 3, ZC, FL, "minecraft:yellow_terracotta")
    world.set(100, FL, ZC - 3, "minecraft:chiseled_stone_bricks")
    world.set(100, FL + 1, ZC - 4, "minecraft:chiseled_stone_bricks")
    world.set(100, FL + 2, ZC - 4, "minecraft:chiseled_stone_bricks")
    b.guide(112, 127, FL, ZC + 3, "minecraft:yellow_terracotta")
    b.guide_z(127, ZC + 3, ZC, FL, "minecraft:yellow_terracotta")
    b.output(2, 111, FL + 1, ZC + 3)
    world.set(111, FL, ZC + 3, "minecraft:gold_block")
    # end rods como relógios de luz, nas laterais, sem atravessar o caminho
    for x in range(110, 124, 6):
        world.set(x, FL + 1, 21, "minecraft:end_rod", {"facing": "up"})
        world.set(x, FL + 1, 29, "minecraft:end_rod", {"facing": "up"})
    b.sign(98, FL + 2, ZC, "east", ["Fase 3", "A 1ª porta fica", "aberta. A 2ª", "fecha sozinha"])
    b.sign(109, FL + 2, ZC + 4, "north", ["Saída 2", "Aumente o delay", "até atravessar", "o corredor"])
    b.chest(98, FL + 1, 30, "west", [("minecraft:redstone", 64), ("minecraft:lever", 2)], "Fase 3")

    # ----- FASE 4 torre -----
    b.garden(129, 132)
    tx0, tx1 = 133, 149
    b.pavilion(tx0, tx1, FL, THEMES["p4"])
    b.arch(tx0, FL, THEMES["p4"])
    # tubo de vidro no centro
    tube_x, tube_z = 141, ZC
    # coluna até furar o telhado; o piso de cima fica em FU
    for y in range(FL + 1, FU):
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx == 0 and dz == 0:
                    world.set(tube_x, y, tube_z, "minecraft:air")
                else:
                    world.set(tube_x + dx, y, tube_z + dz, "minecraft:glass")
    world.set(tube_x, FL, tube_z, "minecraft:soul_sand")
    world.set(tube_x, FL + 1, tube_z + 1, "minecraft:air")
    world.set(tube_x, FL + 2, tube_z + 1, "minecraft:air")
    world.set(
        tube_x,
        FL + 1,
        tube_z - 1,
        "minecraft:dispenser",
        {"facing": "south"},
        be_dispenser(tube_x, FL + 1, tube_z - 1),
    )
    b.output(3, tube_x, FL + 1, tube_z - 3)
    world.set(tube_x, FL, tube_z - 3, "minecraft:dark_prismarine")
    world.set(tube_x, FL, tube_z - 2, "minecraft:cyan_terracotta")
    # sala no telhado, com o buraco da coluna no centro
    for xx in range(tx0 + 1, tx1):
        for zz in range(Z0 + 1, Z1):
            if not (xx == tube_x and zz == tube_z):
                world.set(xx, FU, zz, "minecraft:dark_prismarine")
            world.set(xx, FU + 1, zz, "minecraft:air")
            world.set(xx, FU + 2, zz, "minecraft:air")
            world.set(xx, FU + 3, zz, "minecraft:air")
    for xx in range(tx0, tx1 + 1):
        for zz in (Z0, Z1):
            for yy in range(FU, FU + 5):
                world.set(xx, yy, zz, "minecraft:prismarine_bricks")
    for zz in range(Z0, Z1 + 1):
        for yy in range(FU, FU + 5):
            world.set(tx0, yy, zz, "minecraft:prismarine_bricks")
            world.set(tx1, yy, zz, "minecraft:prismarine_bricks")
    world.set(tube_x, FU, tube_z, "minecraft:air")
    for dx, dz in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
        world.set(tube_x + dx, FL + 1, tube_z + dz, "minecraft:sea_lantern")
        world.set(tube_x + dx, FU + 1, tube_z + dz, "minecraft:sea_lantern")
    for z in (ZC - 1, ZC, ZC + 1):
        for y in range(FU + 1, FU + 4):
            world.set(tx1, y, z, "minecraft:air")
    world.set(tube_x, FU + 4, ZC, "minecraft:sea_lantern")
    b.sign(tx0 + 1, FL + 2, 21, "east", ["Fase 4", "Balde no ejetor", "Dispare a Saída 3", "Plante a alga"])
    b.sign(tx0 + 1, FL + 2, 29, "east", ["Farinha de osso", "até o topo", "Quebre a alga", "Suba nas bolhas"], glowing=True)
    b.chest(
        tx0 + 1,
        FL + 1,
        30,
        "west",
        [("minecraft:redstone", 32), ("minecraft:water_bucket", 1), ("minecraft:kelp", 32), ("minecraft:bone_meal", 32)],
        "Fase 4",
    )
    # ponte de saída no alto, do lado leste da torre até a fase 5
    # o arco de cima está em tx1. A ponte começa em tx1+1.

    # ----- ALA DE CIMA -----
    # Fase 5 começa depois de uma ponte curta
    bridge_start = tx1 + 1
    b.bridge(bridge_start, bridge_start + 5, FU)
    # abertura já feita na parede leste da torre na altura do sobrado

    x = bridge_start + 7
    # FASE 5 sala escura
    p5 = b.pavilion(x, x + 22, FU, THEMES["p5"], lit=False)
    b.arch(x, FU, THEMES["p5"])
    b.iron_gate(x + 22, FU, THEMES["p5"])
    # vestíbulo iluminado só nos primeiros 4 blocos
    for lx in range(x + 1, x + 5):
        world.set(lx, p5["ceil"] - 1, ZC, "minecraft:iron_chain", {"axis": "y"})
        world.set(lx, p5["ceil"] - 2, ZC, "minecraft:lantern", {"hanging": "true"})
    # curva: parede no meio para a luz não chegar no fundo
    for z in range(21, 30):
        world.set(x + 8, FU + 1, z, "minecraft:polished_blackstone")
        world.set(x + 8, FU + 2, z, "minecraft:polished_blackstone")
        world.set(x + 8, FU + 3, z, "minecraft:polished_blackstone")
    world.set(x + 8, FU + 1, 21, "minecraft:air")
    world.set(x + 8, FU + 2, 21, "minecraft:air")
    # lâmpadas no chão do trecho escuro
    for lx in range(x + 11, x + 21, 2):
        world.set(lx, FU + 1, ZC + 1, "minecraft:redstone_lamp", {"lit": "false"})
        world.set(lx, FU, ZC + 1, "minecraft:polished_blackstone")
    b.guide(x + 10, x + 21, FU, ZC + 2, "minecraft:gray_terracotta")
    b.output(4, x + 9, FU + 1, ZC + 2)
    world.set(x + 9, FU, ZC + 2, "minecraft:chiseled_polished_blackstone")
    b.sign(x + 1, FU + 2, ZC, "east", ["Fase 5", "Sala escura", "Ligue a Saída 4", "às lâmpadas"], glowing=True)
    b.chest(x + 1, FU + 1, 30, "west", [("minecraft:redstone", 64)], "Fase 5")
    x = x + 22

    def upper_gap(a, c):
        b.bridge(a, c, FU)

    # FASE 6
    upper_gap(x + 1, x + 5)
    x = x + 7
    p6 = b.pavilion(x, x + 18, FU, THEMES["p6"])
    b.arch(x, FU, THEMES["p6"])
    b.iron_gate(x + 18, FU, THEMES["p6"])
    # alavanca -> arduino, sem chegar na porta
    b.guide(x + 3, x + 8, FU, ZC - 3, "minecraft:pink_terracotta")
    world.set(x + 3, FU, ZC - 3, "minecraft:chiseled_stone_bricks")
    world.set(x + 3, FU + 1, ZC - 4, "minecraft:chiseled_stone_bricks")
    world.set(x + 3, FU + 2, ZC - 4, "minecraft:chiseled_stone_bricks")
    b.arduino(x + 8, FU + 1, ZC - 3)
    world.set(x + 8, FU, ZC - 3, "minecraft:copper_block")
    # saída 5 até a porta, outro caminho
    b.guide(x + 10, x + 17, FU, ZC + 3, "minecraft:pink_terracotta")
    b.guide_z(x + 17, ZC + 3, ZC, FU, "minecraft:pink_terracotta")
    b.output(5, x + 9, FU + 1, ZC + 3)
    world.set(x + 9, FU, ZC + 3, "minecraft:copper_block")
    b.sign(x + 1, FU + 2, ZC, "east", ["Fase 6", "A alavanca avisa", "o Arduino", "Não abre a porta"])
    b.sign(x + 1, FU + 3, ZC + 2, "east", ["O código lê", "REDSTONE_LEVEL", "e liga a", "Saída 5"])
    b.chest(x + 1, FU + 1, 30, "west", [("minecraft:redstone", 64), ("minecraft:lever", 2)], "Fase 6")
    x = x + 18

    # FASE 7
    upper_gap(x + 1, x + 5)
    x = x + 7
    b.pavilion(x, x + 20, FU, THEMES["p7"])
    b.arch(x, FU, THEMES["p7"])
    b.iron_gate(x + 10, FU, THEMES["p7"])
    b.iron_gate(x + 20, FU, THEMES["p7"])
    b.output(6, x + 4, FU + 1, ZC - 3)
    world.set(x + 4, FU, ZC - 3, "minecraft:chiseled_copper")
    b.guide(x + 5, x + 9, FU, ZC - 3, "minecraft:gray_terracotta")
    b.guide_z(x + 9, ZC - 3, ZC, FU, "minecraft:gray_terracotta")
    b.output(7, x + 14, FU + 1, ZC + 3)
    world.set(x + 14, FU, ZC + 3, "minecraft:chiseled_copper")
    b.guide(x + 15, x + 19, FU, ZC + 3, "minecraft:gray_terracotta")
    b.guide_z(x + 19, ZC + 3, ZC, FU, "minecraft:gray_terracotta")
    b.sign(x + 1, FU + 2, ZC, "east", ["Fase 7", "Saída 6 primeiro", "Saída 7 depois", "A ordem importa"])
    b.chest(x + 1, FU + 1, 30, "west", [("minecraft:redstone", 64)], "Fase 7")
    x = x + 20

    # FASE 8 fosso
    upper_gap(x + 1, x + 5)
    x = x + 7
    b.pavilion(x, x + 20, FU, THEMES["p8"])
    b.arch(x, FU, THEMES["p8"])
    b.iron_gate(x + 20, FU, THEMES["p8"])
    # fosso de 1 bloco, x+8 até x+12, z 23-27
    for fx in range(x + 8, x + 13):
        for fz in range(23, 28):
            world.set(fx, FU, fz, "minecraft:air")
            world.set(fx, FU - 1, fz, "minecraft:tuff_bricks")
    # borda
    world.set(
        x + 7,
        FU + 1,
        ZC,
        "minecraft:dispenser",
        {"facing": "east"},
        be_dispenser(x + 7, FU + 1, ZC),
    )
    b.output(8, x + 4, FU + 1, ZC)
    world.set(x + 4, FU, ZC, "minecraft:tuff_bricks")
    b.guide(x + 5, x + 6, FU, ZC, "minecraft:brown_terracotta")
    b.output(9, x + 15, FU + 1, ZC + 3)
    world.set(x + 15, FU, ZC + 3, "minecraft:tuff_bricks")
    b.guide(x + 16, x + 19, FU, ZC + 3, "minecraft:brown_terracotta")
    b.guide_z(x + 19, ZC + 3, ZC, FU, "minecraft:brown_terracotta")
    b.sign(x + 1, FU + 2, ZC - 2, "east", ["Fase 8", "Saída 8: pulso", "Balde no ejetor", "Encha o fosso"])
    b.sign(x + 1, FU + 2, ZC + 2, "east", ["Saída 9: segure", "a porta aberta", "Pulso curto", "fecha cedo"])
    b.chest(x + 1, FU + 1, 30, "west", [("minecraft:redstone", 64), ("minecraft:water_bucket", 1)], "Fase 8")
    x = x + 20

    # FASE 9 combinação
    upper_gap(x + 1, x + 5)
    x = x + 7
    b.pavilion(x, x + 22, FU, THEMES["p9"])
    b.arch(x, FU, THEMES["p9"])
    # três portas
    b.iron_gate(x + 8, FU, THEMES["p9"])
    b.iron_gate(x + 15, FU, THEMES["p9"])
    b.iron_gate(x + 22, FU, THEMES["p9"])
    # saídas ao sul, guias até cada porta
    b.output(10, x + 4, FU + 1, ZC - 4)
    world.set(x + 4, FU, ZC - 4, "minecraft:purpur_pillar", {"axis": "y"})
    b.guide(x + 5, x + 7, FU, ZC - 4, "minecraft:purple_terracotta")
    b.guide_z(x + 7, ZC - 4, ZC, FU, "minecraft:purple_terracotta")
    b.output(12, x + 18, FU + 1, ZC - 4)
    world.set(x + 18, FU, ZC - 4, "minecraft:purpur_pillar", {"axis": "y"})
    b.guide(x + 19, x + 21, FU, ZC - 4, "minecraft:purple_terracotta")
    b.guide_z(x + 21, ZC - 4, ZC, FU, "minecraft:purple_terracotta")
    # saída 11 com inversor visível: pilar + tocha que segura a porta do meio aberta
    b.output(11, x + 11, FU + 1, ZC - 4)
    world.set(x + 12, FU + 1, ZC - 4, "minecraft:purpur_pillar", {"axis": "y"})
    world.set(x + 12, FU, ZC - 4, "minecraft:purpur_block")
    # tocha na face leste do pilar, apontando para a porta (leste)
    world.set(x + 13, FU + 1, ZC - 4, "minecraft:redstone_wall_torch", {"facing": "east", "lit": "true"})
    # pó do inversor até a porta do meio (x+15)
    for z in range(ZC - 4, ZC + 1):
        world.set(x + 14, FU, z, "minecraft:purple_terracotta")
        north = "side" if z > ZC - 4 else "none"
        south = "side" if z < ZC else "none"
        world.set(x + 14, FU + 1, z, "minecraft:redstone_wire", {"east": "none", "west": "side" if z == ZC - 4 else "none", "north": north, "south": south, "power": "0"})
    # padrão na parede norte
    world.set(x + 10, FU + 2, 30, "minecraft:gold_block")
    world.set(x + 12, FU + 2, 30, "minecraft:coal_block")
    world.set(x + 14, FU + 2, 30, "minecraft:gold_block")
    b.sign(x + 10, FU + 3, 30, "north", ["LIGADA", "", "", ""])
    b.sign(x + 12, FU + 3, 30, "north", ["DESLIGADA", "", "", ""])
    b.sign(x + 14, FU + 3, 30, "north", ["LIGADA", "", "", ""])
    b.sign(x + 1, FU + 2, ZC, "east", ["Fase 9", "10 ligada", "11 desligada", "12 ligada"])
    b.sign(x + 1, FU + 3, ZC + 2, "east", ["A porta do meio", "já tem fiação", "Deixe a 11", "desligada"])
    b.chest(x + 1, FU + 1, 20, "east", [("minecraft:redstone", 64)], "Fase 9")
    # porta do meio começa aberta, porque a tocha está acesa
    world.set(x + 15, FU + 1, ZC, "minecraft:iron_door", {"facing": "east", "half": "lower", "hinge": "left", "open": "true"})
    world.set(x + 15, FU + 2, ZC, "minecraft:iron_door", {"facing": "east", "half": "upper", "hinge": "left", "open": "true"})
    x = x + 22

    # FASE 10
    upper_gap(x + 1, x + 5)
    x = x + 7
    b.pavilion(x, x + 28, FU, THEMES["p10"], lit=False)
    b.arch(x, FU, THEMES["p10"])
    # vestíbulo claro
    for lx in range(x + 1, x + 5):
        world.set(lx, FU + 7, ZC, "minecraft:iron_chain", {"axis": "y"})
        world.set(lx, FU + 6, ZC, "minecraft:lantern", {"hanging": "true"})
    for lx in range(x + 8, x + 16, 2):
        world.set(lx, FU + 1, ZC + 2, "minecraft:redstone_lamp", {"lit": "false"})
        world.set(lx, FU, ZC + 2, "minecraft:smooth_quartz")
    b.output(13, x + 6, FU + 1, ZC + 3)
    world.set(x + 6, FU, ZC + 3, "minecraft:chiseled_quartz_block")
    b.guide(x + 7, x + 16, FU, ZC + 3, "minecraft:light_gray_terracotta")
    col_x = x + 20
    my = FU + 4
    for yy in range(FU + 1, my):
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx == 0 and dz == 0:
                    world.set(col_x, yy, ZC, "minecraft:water", {"level": "0"})
                else:
                    world.set(col_x + dx, yy, ZC + dz, "minecraft:glass")
    world.set(col_x, FU, ZC, "minecraft:soul_sand")
    world.set(col_x - 1, FU + 1, ZC, "minecraft:air")
    world.set(col_x - 1, FU + 2, ZC, "minecraft:air")
    b.door(col_x - 1, FU + 1, ZC, "iron", "east")
    b.output(14, col_x - 3, FU + 1, ZC + 2)
    world.set(col_x - 3, FU, ZC + 2, "minecraft:chiseled_quartz_block")
    b.guide(col_x - 2, col_x - 2, FU, ZC + 2, "minecraft:light_gray_terracotta")
    b.guide_z(col_x - 2, ZC + 2, ZC, FU, "minecraft:light_gray_terracotta")
    for xx in range(col_x - 1, x + 30):
        for zz in range(Z0 + 1, Z1):
            if xx == col_x and zz == ZC:
                world.set(xx, my, zz, "minecraft:water", {"level": "0"})
            else:
                world.set(xx, my, zz, "minecraft:smooth_quartz")
            world.set(xx, my + 1, zz, "minecraft:air")
            world.set(xx, my + 2, zz, "minecraft:air")
    for xx in range(col_x - 1, x + 30):
        world.set(xx, my + 1, Z0 + 1, "minecraft:quartz_pillar", {"axis": "y"})
        world.set(xx, my + 1, Z1 - 1, "minecraft:quartz_pillar", {"axis": "y"})
    b.arduino(x + 24, my + 1, ZC - 3)
    world.set(x + 24, my, ZC - 3, "minecraft:copper_block")
    world.set(x + 24, my, ZC - 4, "minecraft:chiseled_stone_bricks")
    world.set(x + 24, my + 1, ZC - 4, "minecraft:chiseled_stone_bricks")
    world.set(x + 24, my + 2, ZC - 4, "minecraft:chiseled_stone_bricks")
    world.set(x + 28, my + 1, ZC - 1, "minecraft:quartz_pillar", {"axis": "y"})
    world.set(x + 28, my + 2, ZC - 1, "minecraft:quartz_pillar", {"axis": "y"})
    world.set(x + 28, my + 1, ZC + 1, "minecraft:quartz_pillar", {"axis": "y"})
    world.set(x + 28, my + 2, ZC + 1, "minecraft:quartz_pillar", {"axis": "y"})
    b.door(x + 28, my + 1, ZC, "iron", "east")
    b.output(15, x + 26, my + 1, ZC + 3)
    world.set(x + 26, my, ZC + 3, "minecraft:chiseled_quartz_block")
    b.guide(x + 27, x + 28, my, ZC + 3, "minecraft:light_gray_terracotta")
    b.guide_z(x + 28, ZC + 3, ZC, my, "minecraft:light_gray_terracotta")
    for tx in range(x + 29, x + 36):
        for tz in range(ZC - 3, ZC + 4):
            world.set(tx, my, tz, "minecraft:smooth_quartz")
            world.set(tx, my - 1, tz, "minecraft:quartz_block")
            if tz in (ZC - 3, ZC + 3):
                world.set(tx, my + 1, tz, "minecraft:quartz_pillar", {"axis": "y"})
    world.set(x + 33, my + 1, ZC, "minecraft:potted_open_eyeblossom")
    b.chest(x + 33, my + 1, ZC + 2, "west", [("minecraft:golden_apple", 1), ("minecraft:cookie", 16), ("minecraft:cake", 1)], "Prêmio")
    b.sign(x + 1, FU + 2, ZC, "east", ["Fase 10", "Luz: Saída 13", "Porta d'água: 14", "Final: Saída 15"], glowing=True)
    b.sign(x + 24, my + 2, ZC - 2, "south", ["Alavanca aqui", "Desligue a da", "fase 6 antes", ""])
    b.sign(x + 32, my + 2, ZC - 1, "west", ["Você conseguiu", "A oficina", "está aberta", ""])
    b.chest(x + 1, FU + 1, 30, "west", [("minecraft:redstone", 64), ("minecraft:lever", 2)], "Fase 10")
    for px in (x + 24, x + 33):
        b.box(px, px, Z0, Z0, FL, my - 1, "minecraft:quartz_pillar", {"axis": "y"})
        b.box(px, px, Z1, Z1, FL, my - 1, "minecraft:quartz_pillar", {"axis": "y"})

    return b


def write_saved_data(outputs):
    entries = List[Compound]()
    for number, x, y, z in outputs:
        oid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"makercraft-output-{number}"))
        entries.append(
            Compound(
                {
                    "Id": String(oid),
                    "Number": Int(number),
                    "X": Int(x),
                    "Y": Int(y),
                    "Z": Int(z),
                    "Dimension": String(DIM),
                }
            )
        )
    root = File({"data": Compound({"Outputs": entries}), "DataVersion": Int(4671)})
    path = SAVE / "data" / "makercraft_arduino_output.dat"
    path.parent.mkdir(parents=True, exist_ok=True)
    root.save(path, gzipped=True)


def write_datapack(outputs, arduinos):
    root = SAVE / "datapacks" / "makercraft_setup"
    func = root / "data" / "makercraft_setup" / "function"
    tag = root / "data" / "minecraft" / "tags" / "function"
    func.mkdir(parents=True, exist_ok=True)
    tag.mkdir(parents=True, exist_ok=True)
    (root / "pack.mcmeta").write_text(
        """{
  "pack": {
    "description": "Numera as saídas do MakerCraft na primeira abertura",
    "min_format": [94, 0],
    "max_format": [94, 1]
  }
}
""",
        encoding="utf-8",
    )
    (tag / "load.json").write_text(
        '{ "values": ["makercraft_setup:load"] }\n',
        encoding="utf-8",
    )
    lines = [
        "scoreboard objectives add makercraft_setup dummy",
    ]
    for number, x, y, z in outputs:
        lines.append(
            f"execute if block {x} {y} {z} minecraft:air run setblock {x} {y} {z} makercraft:arduino_output"
        )
    for x, y, z in arduinos:
        lines.append(
            f"execute if block {x} {y} {z} minecraft:air run setblock {x} {y} {z} makercraft:arduino_block"
        )
    lines.append("scoreboard players set #done makercraft_setup 1")
    (func / "place.mcfunction").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (func / "load.mcfunction").write_text(
        "\n".join(
            [
                "scoreboard objectives add makercraft_setup dummy",
                "execute unless score #done makercraft_setup matches 1 run function makercraft_setup:place",
                "",
            ]
        ),
        encoding="utf-8",
    )


def update_level(spawn):
    level_path = SAVE / "level.dat"
    f = File.load(level_path, gzipped=True)
    data = f["Data"]
    data["GameType"] = Int(0)
    data["Difficulty"] = Byte(0)
    data["DayTime"] = Long(6000)
    data["spawn"]["pos"] = nbtlib.IntArray([Int(spawn[0]), Int(spawn[1]), Int(spawn[2])])
    data["spawn"]["yaw"] = nbtlib.Float(-90.0)
    data["spawn"]["pitch"] = nbtlib.Float(0.0)
    rules = data["game_rules"]
    rules["minecraft:advance_time"] = Byte(0)
    rules["minecraft:advance_weather"] = Byte(0)
    rules["minecraft:spawn_monsters"] = Byte(0)
    rules["minecraft:keep_inventory"] = Byte(1)
    rules["minecraft:mob_griefing"] = Byte(0)
    player = data["Player"]
    _set_player(player, spawn)
    f.save(level_path, gzipped=True)

    pdata = SAVE / "playerdata" / "27c81885-ed4a-483b-8312-2f79b93d2c09.dat"
    pf = File.load(pdata, gzipped=True)
    _set_player(pf, spawn)
    pf.save(pdata, gzipped=True)


def _set_player(player, spawn):
    player["playerGameType"] = Int(0)
    player["Pos"] = List[nbtlib.Double]([nbtlib.Double(spawn[0] + 0.5), nbtlib.Double(float(spawn[1])), nbtlib.Double(spawn[2] + 0.5)])
    player["Rotation"] = List[nbtlib.Float]([nbtlib.Float(-90.0), nbtlib.Float(0.0)])
    player["Motion"] = List[nbtlib.Double]([nbtlib.Double(0.0), nbtlib.Double(0.0), nbtlib.Double(0.0)])
    abilities = player["abilities"]
    abilities["invulnerable"] = Byte(0)
    abilities["mayfly"] = Byte(0)
    abilities["instabuild"] = Byte(0)
    abilities["flying"] = Byte(0)
    abilities["mayBuild"] = Byte(1)
    player["Inventory"] = List[Compound]([])
    player["foodLevel"] = Int(20)
    player["foodSaturationLevel"] = nbtlib.Float(5.0)
    player["Health"] = nbtlib.Float(20.0)


def main():
    if not BACKUP.exists():
        shutil.copy2(REGION, BACKUP)
    chunks = load_region(REGION)
    roundtrip_check(chunks)
    world = World(chunks)
    builder = build(world)
    builder.outputs.sort(key=lambda item: item[0])
    numbers = [n for n, *_ in builder.outputs]
    if numbers != list(range(1, 16)):
        raise SystemExit(f"saídas fora de ordem: {numbers}")
    world.apply()
    save_region(REGION, chunks)
    write_datapack(builder.outputs, builder.arduinos)
    update_level((8, -60, ZC))
    print("pavilhões gravados")
    print("saídas", len(builder.outputs), "arduinos", len(builder.arduinos))
    print("spawn", 8, -60, ZC)


if __name__ == "__main__":
    main()
