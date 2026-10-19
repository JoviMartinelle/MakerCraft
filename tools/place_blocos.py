# Coloca os blocos do mod nas posições já numeradas do save MakerCraft.
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_fases import World, load_region, save_region

SAVE = Path(os.environ.get(
    "MAKERCRAFT_SAVE",
    r"C:\Users\Nicolas\curseforge\minecraft\Instances\MakerCraft\saves\MakerCraft",
))
REGION = SAVE / "region" / "r.0.0.mca"
BACKUP = SAVE / "region" / "r.0.0.mca.pre-blocos"

OUTPUTS = [
    (1, 82, -60, 25),
    (2, 112, -60, 24),
    (3, 141, -53, 24),
    (4, 163, -52, 21),
    (5, 198, -51, 25),
    (6, 214, -51, 25),
    (7, 224, -51, 25),
    (8, 243, -52, 25),
    (9, 241, -50, 19),
    (10, 269, -51, 21),
    (11, 276, -51, 21),
    (12, 283, -51, 21),
    (13, 300, -51, 28),
    (14, 309, -51, 23),
    (15, 316, -47, 28),
]
ARDUINOS = [(194, -51, 22), (318, -47, 22)]

REPLACEABLE = {
    "minecraft:air",
    "minecraft:cave_air",
    "minecraft:gold_block",
    "minecraft:iron_block",
    "minecraft:black_concrete",
}

DUST = "minecraft:redstone_wire"
OUTPUT = "makercraft:arduino_output"
ARDUINO = "makercraft:arduino_block"


def dust_line(points):
    return [("d", x, y, z) for x, y, z in points]


def main():
    if not REGION.exists():
        raise SystemExit(f"região não encontrada: {REGION}")
    shutil.copy2(REGION, BACKUP)
    world = World(load_region(REGION))

    for number, x, y, z in OUTPUTS:
        world.set(x, y, z, OUTPUT, {"powered": "false"})
        print(f"saida {number:2} -> ({x}, {y}, {z})")

    for x, y, z in ARDUINOS:
        world.set(x, y, z, ARDUINO, {"powered": "false"})
        print(f"arduino    -> ({x}, {y}, {z})")

    # O apoio debaixo dos dois leitores vira cobre, como o texto da fase descreve.
    for x, y, z in ((194, -52, 22), (318, -48, 22)):
        world.set(x, y, z, "minecraft:copper_block")

    # Alavanca que estava em cima da Saída 8 ligava o pistão sem o Arduino.
    if world.get(243, -51, 25)[0] == "minecraft:lever":
        world.set(243, -51, 25, "minecraft:air")
        print("alavanca removida de cima da saida 8")

    # Alavanca da fase 6, se tiver sumido.
    if world.get(191, -51, 22)[0] == "minecraft:air":
        world.set(191, -51, 22, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})
        print("alavanca da fase 6 recolocada")

    wires = [
        dust_line([(x, -60, 25) for x in range(83, 88)]),
        [("d", x, -60, 24) if x != 120 else ("r", x, -60, 24, "east") for x in range(113, 128)]
        + [("d", 127, -60, 25)],
        dust_line([(x, -51, 25) for x in range(199, 202)]),
        dust_line([(x, -51, 25) for x in range(215, 221)]),
        dust_line([(x, -51, 25) for x in range(225, 231)]),
        [
            ("d", 241, -50, 18),
            ("d", 242, -50, 18),
            ("d", 243, -49, 18),
            ("d", 244, -48, 18),
            ("d", 245, -47, 18),
            ("d", 246, -46, 18),
            ("d", 247, -45, 18),
            ("d", 248, -45, 18),
            ("r", 249, -45, 18, "east"),
            ("d", 250, -45, 18),
            ("d", 251, -45, 18),
            ("d", 252, -45, 18),
            ("d", 253, -45, 18),
            ("d", 254, -45, 18),
            ("d", 255, -45, 18),
            ("d", 254, -46, 18),
            ("d", 253, -47, 18),
            ("d", 253, -48, 19),
            ("d", 253, -49, 20),
            ("d", 253, -50, 21),
            ("d", 253, -51, 22),
            ("d", 253, -52, 23),
            ("d", 252, -52, 23),
            ("r", 252, -52, 24, "south"),
        ],
        dust_line([(270, -51, 21), (271, -51, 21), (272, -51, 21), (272, -51, 22), (272, -51, 23), (272, -51, 24), (272, -51, 25)]),
        dust_line([(284, -51, 21), (285, -51, 21), (286, -51, 21), (286, -51, 22), (286, -51, 23), (286, -51, 24), (286, -51, 25)]),
        dust_line([(x, -51, 28) for x in range(301, 311)]),
        dust_line([(310, -51, 23), (311, -51, 23), (312, -51, 23), (312, -51, 24), (312, -51, 25)]),
        dust_line(
            [(317, -47, 28), (318, -47, 28), (319, -47, 28), (320, -47, 28), (321, -47, 28),
             (321, -47, 27), (321, -47, 26), (321, -47, 25)]
        ),
    ]

    placed_dust = 0
    skipped = []
    for seq in wires:
        for item in seq:
            kind, x, y, z = item[0], item[1], item[2], item[3]
            current = world.get(x, y, z)[0]
            if current not in ("minecraft:air", "minecraft:cave_air"):
                if current not in (DUST, "minecraft:repeater"):
                    skipped.append((x, y, z, current))
                continue
            below = world.get(x, y - 1, z)[0]
            if below in ("minecraft:air", "minecraft:cave_air", "minecraft:water"):
                skipped.append((x, y, z, f"sem apoio ({below})"))
                continue
            if kind == "r":
                world.set(
                    x, y, z,
                    "minecraft:repeater",
                    {"facing": item[4], "delay": "1", "locked": "false", "powered": "false"},
                )
            else:
                world.set(
                    x, y, z, DUST,
                    {"north": "side", "south": "side", "east": "side", "west": "side", "power": "0"},
                )
            placed_dust += 1

    # Lâmpadas da fase 10, só onde ainda está vazio.
    lamps = 0
    for x in range(302, 311, 2):
        if world.get(x, -51, 27)[0] == "minecraft:air":
            if world.get(x, -52, 27)[0] in ("minecraft:air", "minecraft:cave_air"):
                world.set(x, -52, 27, "minecraft:smooth_quartz")
            world.set(x, -51, 27, "minecraft:redstone_lamp", {"lit": "false"})
            lamps += 1

    world.apply()
    save_region(REGION, world.chunks)
    print(f"fio colocado em {placed_dust} blocos; lampadas novas: {lamps}")
    if skipped:
        print("células que já tinham outra coisa e foram mantidas:")
        for x, y, z, name in skipped:
            print(f"  ({x}, {y}, {z}) {name}")


if __name__ == "__main__":
    main()
