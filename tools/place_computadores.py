# Coloca um computador em cada fase, com o programa da sala já gravado.
import os
import shutil
import sys
from pathlib import Path

from nbtlib import Byte, Compound, Int, String

sys.path.insert(0, str(Path(__file__).parent))
from build_fases import World, load_region, save_region

SAVE = Path(os.environ.get(
    "MAKERCRAFT_SAVE",
    r"C:\Users\Nicolas\curseforge\minecraft\Instances\MakerCraft\saves\MakerCraft",
))
REGION = SAVE / "region" / "r.0.0.mca"
BACKUP = SAVE / "region" / "r.0.0.mca.pre-computadores"

SOFT = {
    "minecraft:air",
    "minecraft:cave_air",
    "minecraft:water",
    "minecraft:lava",
    "minecraft:redstone_wire",
}


def code(*lines):
    return "\n".join(lines)


ROOMS = [
    (
        "Fase 1",
        46, 58, -60,
        code(
            "# Fase 1 nao usa o Arduino.",
            "# Ligue a alavanca e coloque o po de redstone.",
        ),
    ),
    (
        "Fase 2",
        68, 80, -60,
        code("ligar 1"),
    ),
    (
        "Fase 3",
        98, 110, -60,
        code(
            "ligar 2",
            "esperar 6000",
            "desligar 2",
            "esperar 2000",
            "repetir",
        ),
    ),
    (
        "Fase 4",
        134, 139, -60,
        code(
            "ligar 3",
            "esperar 200",
            "desligar 3",
        ),
    ),
    (
        "Fase 5",
        156, 162, -51,
        code("ligar 4"),
    ),
    (
        "Fase 6",
        186, 192, -51,
        code(
            "quando sinal",
            "ligar 5",
            "senao",
            "desligar 5",
            "fim",
            "repetir",
        ),
    ),
    (
        "Fase 7",
        206, 212, -51,
        code(
            "ligar 6",
            "esperar 500",
            "ligar 7",
        ),
    ),
    (
        "Fase 8",
        232, 240, -51,
        code(
            "ligar 8",
            "ligar 9",
        ),
    ),
    (
        "Fase 9",
        258, 266, -51,
        code(
            "ligar 10",
            "desligar 11",
            "ligar 12",
        ),
    ),
    (
        "Fase 10",
        292, 298, -51,
        code(
            "ligar 13",
            "ligar 14",
            "quando sinal",
            "ligar 15",
            "senao",
            "desligar 15",
            "fim",
            "repetir",
        ),
    ),
]


def solid(name):
    if name in SOFT or name.endswith("_carpet") or "sign" in name or name.endswith("_door"):
        return False
    return True


def find_spot(world, x0, x1, y):
    for z in (19, 20, 21):
        for x in range(x0, x1 + 1):
            here, _ = world.get(x, y, z)
            below, _ = world.get(x, y - 1, z)
            north, _ = world.get(x, y, z - 1)
            if here == "minecraft:air" and solid(below) and solid(north):
                return x, y, z
    return None


def block_entity(x, y, z, title, program):
    return Compound(
        {
            "id": String("makercraft:computer"),
            "x": Int(x),
            "y": Int(y),
            "z": Int(z),
            "keepPacked": Byte(0),
            "Code": String(program),
            "Title": String(title),
        }
    )


def main():
    world = World(load_region(REGION))
    spots = []
    for title, x0, x1, y, program in ROOMS:
        spot = find_spot(world, x0, x1, y)
        if spot is None:
            raise SystemExit(f"sem lugar livre para {title} em x {x0}-{x1} y {y}")
        spots.append((title, spot, program))
        print(f"{title}: {spot}")

    shutil.copy2(REGION, BACKUP)
    world = World(load_region(REGION))
    for title, (x, y, z), program in spots:
        world.set(
            x, y, z,
            "makercraft:computer",
            {"facing": "south"},
            block_entity(x, y, z, title, program),
        )
    world.apply()
    save_region(REGION, world.chunks)
    print(f"backup em {BACKUP.name}")


if __name__ == "__main__":
    main()
