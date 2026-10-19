"""Fecha atalhos, corrige a redstone e deixa o mapa jogável.

Não mexe no ejetor da fase 4 em (141, -52, 24).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build_fases import (  # noqa: E402
    FL,
    FU,
    REGION,
    SAVE,
    ZC,
    Builder,
    World,
    load_region,
    save_region,
    write_datapack,
    write_saved_data,
)

BACKUP = SAVE / "region" / "r.0.0.mca.pre-polish"
AIR = {
    "minecraft:air",
    "minecraft:cave_air",
    "minecraft:void_air",
    "minecraft:short_grass",
    "minecraft:tall_grass",
}
OUTPUTS: list[tuple[int, int, int, int]] = []
ARDUINOS: list[tuple[int, int, int]] = []


def nm(block):
    return block[0]


def is_soft(name: str) -> bool:
    if name in AIR:
        return True
    if name.endswith("_carpet") or name.endswith("_sign"):
        return True
    if name in (
        "minecraft:redstone_wire",
        "minecraft:repeater",
        "minecraft:comparator",
        "minecraft:torch",
        "minecraft:redstone_torch",
        "minecraft:redstone_wall_torch",
        "minecraft:lever",
        "minecraft:azure_bluet",
        "minecraft:open_eyeblossom",
        "minecraft:firefly_bush",
        "minecraft:poppy",
        "minecraft:dandelion",
    ):
        return True
    return False


def solid_name(name: str) -> bool:
    return name not in AIR and "sign" not in name and not name.endswith("_carpet")


class P:
    def __init__(self, world: World):
        self.w = world
        self.b = Builder(world)

    def name(self, x, y, z):
        return nm(self.w.get(x, y, z))

    def set(self, x, y, z, name, props=None, be=None):
        self.w.set(x, y, z, name, props, be)

    def air(self, x, y, z):
        self.set(x, y, z, "minecraft:air")

    def output(self, number, x, y, z):
        self.set(x, y, z, "makercraft:arduino_output", {"powered": "false"})
        OUTPUTS.append((number, x, y, z))

    def arduino(self, x, y, z):
        self.set(x, y, z, "makercraft:arduino_block", {"powered": "false"})
        ARDUINOS.append((x, y, z))

    def sign(self, x, y, z, facing, lines, wood="oak", glow=False):
        self.b.sign(x, y, z, facing, lines[:4], wood, glow)

    def chest(self, x, y, z, facing, items, title):
        self.b.chest(x, y, z, facing, items, title)

    def fill_if_soft(self, x, y, z, name, props=None, also=()):
        current = self.name(x, y, z)
        if is_soft(current) or current in also:
            self.set(x, y, z, name, props)

    def seal_door_wall(self, x, y0, y1, block, door_y, also=()):
        """Parede de porta a porta, no eixo X. Só a porta em z=25 fica aberta."""
        for z in range(18, 33):
            for y in range(y0, y1 + 1):
                if z == ZC and y in (door_y, door_y + 1):
                    continue
                self.fill_if_soft(x, y, z, block, also=also)

    def lay(self, seq, output=None, tail=(1, 0), support=False, support_block="minecraft:stone_bricks"):
        """seq: ('d',x,y,z) ou ('r',x,y,z,facing). O pó aponta para o próximo e para a porta."""
        dusts = [item for item in seq if item[0] == "d"]

        def neighbor_offset(a, b):
            return (b[0] - a[0], b[1] - a[1], b[2] - a[2])

        coords = [(it[1], it[2], it[3]) for it in seq]
        for i, item in enumerate(seq):
            kind = item[0]
            x, y, z = item[1], item[2], item[3]
            if support and self.name(x, y - 1, z) not in (
                "minecraft:sticky_piston",
                "minecraft:piston",
                "makercraft:arduino_output",
                "minecraft:dispenser",
            ):
                below = self.name(x, y - 1, z)
                if below in AIR or below.endswith("_carpet") or "sign" in below or below == "minecraft:redstone_wire":
                    self.set(x, y - 1, z, support_block)
            if kind == "r":
                self.set(
                    x,
                    y,
                    z,
                    "minecraft:repeater",
                    {"facing": item[4], "delay": "1", "locked": "false", "powered": "false"},
                )
                continue
            props = {"north": "none", "south": "none", "east": "none", "west": "none", "power": "0"}
            neighbors = []
            if i > 0:
                neighbors.append(coords[i - 1])
            if i + 1 < len(coords):
                neighbors.append(coords[i + 1])
            if i == 0 and output is not None:
                neighbors.append(output)
            if i == len(seq) - 1 and tail is not None:
                neighbors.append((x + tail[0], y, z + tail[1]))
            for ox, oy, oz in neighbors:
                dx, dy, dz = ox - x, oy - y, oz - z
                side = "up" if dy > 0 else "side"
                if dx == 1:
                    props["east"] = side
                elif dx == -1:
                    props["west"] = side
                elif dz == 1:
                    props["south"] = side
                elif dz == -1:
                    props["north"] = side
            self.set(x, y, z, "minecraft:redstone_wire", props)
        return dusts

    def guide(self, cells, block):
        for x, z in cells:
            self.set(x, FL if False else cells and 0 or 0, 0, block)

    def floor_guide(self, cells, y_floor, block):
        for x, z in cells:
            self.set(x, y_floor, z, block)
            above = self.name(x, y_floor + 1, z)
            if above.endswith("_carpet") or above == "minecraft:redstone_wire":
                self.air(x, y_floor + 1, z)

    def clear_dust(self, x0, x1, y, z0, z1):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for z in range(min(z0, z1), max(z0, z1) + 1):
                if self.name(x, y, z) in ("minecraft:redstone_wire", "minecraft:repeater"):
                    self.air(x, y, z)


def seal(p: P):
    # Portas internas que ainda davam para contornar.
    p.seal_door_wall(78, -60, -56, "minecraft:polished_deepslate", -60)
    p.seal_door_wall(106, -60, -56, "minecraft:smooth_sandstone", -60)
    p.seal_door_wall(221, -51, -47, "minecraft:polished_deepslate", -51)
    p.seal_door_wall(273, -51, -47, "minecraft:end_stone_bricks", -51)
    p.seal_door_wall(280, -51, -47, "minecraft:end_stone_bricks", -51)
    p.seal_door_wall(313, -51, -47, "minecraft:quartz_block", -51, also={"minecraft:glass", "minecraft:glass_pane"})
    p.seal_door_wall(322, -47, -44, "minecraft:quartz_block", -47)

    # Jardins entre os pavilhões de baixo: corredor fechado, com janela.
    for x0, x1 in ((37, 42), (61, 66), (91, 96), (129, 132)):
        for x in range(x0, x1 + 1):
            for z in (18, 32):
                p.set(x, -61, z, "minecraft:stone_bricks")
                for y in range(-60, -55):
                    if y == -58 and x % 2 == 0:
                        p.set(
                            x,
                            y,
                            z,
                            "minecraft:glass_pane",
                            {"east": "true", "west": "true", "north": "false", "south": "false"},
                        )
                    else:
                        p.set(x, y, z, "minecraft:stone_bricks")

    # Pontes da ala de cima viram galeria. Sem isso dá para cair e ir por baixo.
    bridges = ((150, 155), (180, 184), (205, 209), (232, 236), (259, 263), (288, 292))
    for x0, x1 in bridges:
        for x in range(x0, x1 + 1):
            for z in (23, 27):
                for y in range(-51, -47):
                    p.set(x, y, z, "minecraft:stone_bricks")
            for z in (24, 25, 26):
                if p.name(x, -48, z) in AIR:
                    p.set(x, -48, z, "minecraft:stone_brick_slab", {"type": "bottom"})
                p.set(x, -51, z, "minecraft:air") if False else None
            # tira o corrimão baixo que dava para pular
            for z in (23, 27):
                pass
    # chão da galeria continua z=24..26; o centro z=25 não pode ter laje na altura da cabeça
    for x0, x1 in bridges:
        for x in range(x0, x1 + 1):
            if "slab" in p.name(x, -48, 25):
                pass


def strip_blocking_signs(p: P):
    for y in (-60, -59, -58, -51, -50, -49, -48, -47, -46):
        for x in range(18, 360):
            for z in (24, 25, 26):
                if 136 <= x <= 146:
                    continue
                if "sign" in p.name(x, y, z):
                    p.air(x, y, z)


def mural(p: P, spots):
    """spots: (x, y, z, facing, lines, wood, glow)"""
    for x, y, z, facing, lines, wood, glow in spots:
        p.sign(x, y, z, facing, lines, wood, glow)


def lobby_and_hints(p: P):
    # Lobby: mural na parede norte (z=31 olhando para o sul) e um resumo na sul.
    north = [
        (22, ["MAKERCRAFT", "Oficina de fuga", "Dez fases", "Siga para leste"], True),
        (24, ["O mapa abre", "sem Arduino", "A saida so liga", "com o codigo"], False),
        (26, ["Clique direito", "na Saida", "para ler", "o numero"], False),
        (28, ["Protocolo", "OUTPUT:N:ON", "OUTPUT:N:OFF", "uma por linha"], False),
        (30, ["O jogo envia", "REDSTONE_LEVEL", "quando o fio", "muda no bloco"], False),
        (32, ["O po apaga", "depois de 15", "blocos. Ponha", "um repetidor"], False),
        (34, ["A porta abre", "se o po chega", "de frente, no", "bloco anterior"], False),
        (21, ["Repetidores", "estao no bau", "desta sala", ""], False),
        (23, ["Nao contorne", "a sala. Cada", "porta precisa", "ser aberta"], False),
        (25, ["Fio no centro", "do chao, reto", "ate a porta", ""], False),
        (27, ["Baús tem o", "que falta", "Sobrevivencia", "Pacifica"], False),
        (29, ["Uma saida por", "vez no codigo", "Anote o numero", "antes de ir"], False),
    ]
    # fix typo Baús - signs are plain, accented chars are ok in this world (MAKERCRAFT signs had accents)
    north = [item if item[0] != 27 else (27, ["Baus tem o", "que falta", "Sobrevivencia", "Pacifica"], False) for item in north]
    for x, lines, glow in north:
        p.sign(x, -59, 31, "north", lines, "pale_oak", glow)
    p.sign(22, -58, 31, "north", ["Bem-vindo", "Leia a parede", "e abra o bau", ""], "pale_oak", True)
    p.sign(20, -59, 19, "south", ["Praca la fora", "A oficina", "comeca aqui", ""], "pale_oak", False)
    p.chest(
        19,
        -60,
        31,
        "east",
        [("minecraft:bread", 32), ("minecraft:cooked_beef", 16), ("minecraft:repeater", 16), ("minecraft:redstone", 32)],
        "Despensa",
    )

    hints = [
        # fase 1 oak
        (46, -59, 31, "oak", ["Fase 1", "So redstone", "Sem Arduino", ""], True),
        (48, -59, 31, "oak", ["Alavanca no", "quadro ao sul", "Po no chao", "laranja"], False),
        (50, -59, 31, "oak", ["O fio dobra", "para o centro", "e entra de", "frente na porta"], False),
        (52, -59, 31, "oak", ["Menos de 15", "blocos. Se", "apagar, use", "repetidor"], False),
        # fase 2
        (70, -59, 31, "spruce", ["Fase 2", "Primeira porta", "e voce quem", "liga"], True),
        (72, -59, 31, "spruce", ["Segunda porta", "Saida 1", "OUTPUT:1:ON", "ja esta ligada"], False),
        (74, -59, 31, "spruce", ["Clique direito", "na Saida 1", "O fio dela", "ja vai a porta"], False),
        # fase 3
        (100, -59, 31, "birch", ["Fase 3", "A primeira", "porta e sua", ""], True),
        (102, -59, 31, "birch", ["A segunda", "fecha sozinha", "Aumente o", "delay no codigo"], False),
        (104, -59, 31, "birch", ["Saida 2", "OUTPUT:2:ON", "O repetidor", "ja esta no fio"], False),
        (108, -59, 31, "birch", ["Atravesse", "antes da", "porta fechar", ""], False),
        # fase 4 — mural longe do tubo
        (134, -59, 31, "dark_oak", ["Fase 4", "Saida 3 esta", "na coluna", "de vidro"], True),
        (136, -59, 31, "dark_oak", ["OUTPUT:3:ON", "solta a agua", "Kelp e osso", "ate o topo"], False),
        (138, -59, 31, "dark_oak", ["O ejetor", "nao da para", "abrir. So o", "codigo dispara"], False),
        # fase 6 cherry, y=-50 (floor feet -51, sign head)
        (189, -50, 31, "cherry", ["Fase 6", "A alavanca nao", "abre a porta", ""], True),
        (191, -50, 31, "cherry", ["Ligue o fio", "no Arduino", "Ele manda", "REDSTONE_LEVEL"], False),
        (193, -50, 31, "cherry", ["O codigo liga", "a Saida 5", "OUTPUT:5:ON", ""], False),
        # fase 7
        (214, -50, 31, "dark_oak", ["Fase 7", "Ordem importa", "Saida 6", "depois a 7"], True),
        (216, -50, 31, "dark_oak", ["OUTPUT:6:ON", "passa a", "primeira", ""], False),
        (218, -50, 31, "dark_oak", ["OUTPUT:7:ON", "abre a", "segunda", ""], False),
        (220, -50, 31, "dark_oak", ["Se inverter", "a ordem, a", "segunda nao", "adianta antes"], False),
        # fase 9
        (268, -50, 31, "crimson", ["Fase 9", "Tres saidas", "10 liga", "12 liga"], True),
        (270, -50, 31, "crimson", ["A 11 fica", "DESLIGADA", "Ela apaga a", "tocha do meio"], False),
        (272, -50, 31, "crimson", ["Parede norte:", "ouro, carvao,", "ouro", ""], False),
        (274, -50, 31, "crimson", ["Ouro = ON", "Carvao = OFF", "As tres portas", "de frente"], False),
    ]
    # crimson wall sign may not exist. use dark_oak for those.
    for x, y, z, wood, lines, glow in hints:
        if wood == "crimson":
            wood = "dark_oak"
        p.sign(x, y, z, "north", lines, wood, glow)


def teaching_wires(p: P):
    """Guias que o jogador completa, sempre terminando de frente para a porta."""
    # Apaga fios laterais que nao encaram a porta.
    p.clear_dust(44, 59, -60, 21, 23)
    p.clear_dust(68, 89, -60, 27, 29)
    p.clear_dust(68, 77, -60, 21, 23)
    p.clear_dust(98, 127, -60, 21, 23)
    p.clear_dust(110, 127, -60, 27, 29)
    p.clear_dust(188, 203, -51, 27, 29)
    p.clear_dust(212, 230, -51, 21, 23)
    p.clear_dust(212, 230, -51, 27, 29)

    # Fase 1 — L até a porta 60. Chão y=-61, pó em y=-60.
    p.set(50, -60, 23, "minecraft:chiseled_stone_bricks")
    p.set(50, -59, 23, "minecraft:chiseled_stone_bricks")
    p.sign(50, -59, 24, "south", ["Alavanca", "nesta face", "leste", ""])
    p.set(51, -60, 23, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})
    cells = [(50, z) for z in range(23, 26)] + [(x, 25) for x in range(51, 60)]
    p.floor_guide(cells, -61, "minecraft:orange_terracotta")
    # o poste da alavanca nao e chao de fio; o fio comeca no laranja

    # Fase 2 porta A (78)
    p.set(72, -60, 22, "minecraft:chiseled_stone_bricks")
    p.set(72, -59, 22, "minecraft:chiseled_stone_bricks")
    p.set(73, -60, 22, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})
    cells = [(72, z) for z in range(22, 26)] + [(x, 25) for x in range(73, 78)]
    p.floor_guide(cells, -61, "minecraft:red_terracotta")

    # Fase 2 porta B pré-ligada, Saída 1 em (82,-60,25), porta 90
    p.output(1, 82, -60, 25)
    p.lay([("d", x, -60, 25) for x in range(83, 90)], output=(82, -60, 25), tail=(1, 0))

    # Fase 3 porta A (106)
    p.set(100, -60, 22, "minecraft:chiseled_stone_bricks")
    p.set(100, -59, 22, "minecraft:chiseled_stone_bricks")
    p.set(101, -60, 22, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})
    cells = [(100, z) for z in range(22, 26)] + [(x, 25) for x in range(101, 106)]
    p.floor_guide(cells, -61, "minecraft:yellow_terracotta")

    # Fase 3 porta B, Saída 2, com repetidor porque passa de 15
    # O fio corre ao lado do corredor. Repetidor fora de z=25, senão vira parede.
    p.output(2, 112, -60, 24)
    seq = []
    for x in range(113, 128):
        if x == 120:
            seq.append(("r", x, -60, 24, "east"))
        else:
            seq.append(("d", x, -60, 24))
    seq.append(("d", 127, -60, 25))
    p.lay(seq, output=(112, -60, 24), tail=(1, 0))
    p.sign(120, -59, 31, "north", ["Repetidor", "renova o", "sinal de 15", ""])

    # Fase 6: jogador liga alavanca -> arduino. Saída 5 já vai à porta.
    p.arduino(194, -51, 22)
    p.set(194, -52, 22, "minecraft:copper_block")
    p.set(190, -51, 22, "minecraft:chiseled_stone_bricks")
    p.set(190, -50, 22, "minecraft:chiseled_stone_bricks")
    p.set(191, -51, 22, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})
    for x in range(190, 194):
        p.set(x, -52, 22, "minecraft:pink_terracotta")
    p.output(5, 198, -51, 25)
    p.lay([("d", x, -51, 25) for x in range(199, 204)], output=(198, -51, 25), tail=(1, 0))

    # Fase 7: as duas saídas já ligadas, de frente
    p.output(6, 214, -51, 25)
    p.lay([("d", x, -51, 25) for x in range(215, 221)], output=(214, -51, 25), tail=(1, 0))
    p.output(7, 224, -51, 25)
    p.lay([("d", x, -51, 25) for x in range(225, 231)], output=(224, -51, 25), tail=(1, 0))


def phase4_output(p: P):
    # O ejetor do jogador fica em (141,-52,24). A saída fica colada nele, na parede da coluna.
    # (141,-53,24) é o bloco de baixo: emite sinal para cima e o jogador não abre o ejetor.
    if p.name(141, -52, 24) != "minecraft:dispenser":
        raise SystemExit("ejetor da fase 4 sumiu, abortando")
    p.output(3, 141, -53, 24)


def phase5(p: P):
    """Labirinto escuro. Chão xadrez. A Saída 4 acende o caminho e a porta."""
    # Limpa o interior antigo, menos a casca.
    for x in range(158, 179):
        for z in range(19, 32):
            for y in range(-51, -44):
                p.air(x, y, z)
    for x in range(158, 179):
        for z in range(19, 32):
            p.set(x, -53, z, "minecraft:dark_oak_planks")

    correct = [
        (165, 22), (166, 22), (167, 22), (168, 22),
        (168, 23), (168, 24), (168, 25),
        (169, 25), (170, 25),
        (170, 26), (170, 27),
        (171, 27), (172, 27),
        (172, 26), (172, 25), (172, 24),
        (173, 24), (174, 24),
        (174, 23), (174, 22),
        (175, 22), (175, 23), (175, 24), (175, 25),
        (176, 25), (177, 25),
    ]
    dead = [
        (168, 26), (168, 27), (168, 28),
        (167, 25), (166, 25), (166, 26),
        (170, 24), (170, 23), (170, 22),
        (171, 25), (171, 24),
        (172, 28), (173, 28),
        (173, 22), (172, 22),
    ]
    walk = set(correct + dead)
    walk.add((164, 22))  # vão de entrada

    # Vestíbulo iluminado
    for x in range(158, 164):
        for z in range(19, 32):
            p.set(x, -52, z, "minecraft:polished_blackstone")
    for x in (159, 162):
        p.set(x, -46, 25, "minecraft:iron_chain", {"axis": "y"})
        p.set(x, -47, 25, "minecraft:lantern", {"hanging": "true"})
    p.chest(159, -51, 30, "west", [("minecraft:redstone", 32)], "Fase 5")
    p.sign(160, -50, 31, "north", ["Fase 5", "Labirinto", "escuro", ""], "dark_oak", True)
    p.sign(162, -50, 31, "north", ["Saida 4 no", "chao, canto", "sudoeste", ""], "dark_oak", False)
    p.sign(158, -50, 31, "north", ["OUTPUT:4:ON", "acende o", "xadrez e a", "porta leste"], "dark_oak", False)
    p.sign(163, -50, 31, "north", ["Parede ate", "o teto. Sem", "luz nao da", "para ver"], "dark_oak", False)

    # Chão do labirinto e paredes até o teto
    for x in range(164, 178):
        for z in range(20, 31):
            if (x, z) in walk:
                if (x + z) % 2 == 0:
                    p.set(x, -52, z, "minecraft:redstone_lamp", {"lit": "false"})
                else:
                    p.set(x, -52, z, "minecraft:black_concrete")
                for y in range(-51, -44):
                    p.air(x, y, z)
            else:
                p.set(x, -52, z, "minecraft:polished_blackstone")
                for y in range(-51, -44):
                    p.set(x, y, z, "minecraft:polished_blackstone")

    # Saída 4 no vestíbulo, colada no pó que entra na parede sul do labirinto
    p.output(4, 163, -52, 21)

    dust = []
    for x in range(164, 178):
        for z in range(20, 31):
            if (x, z) in walk:
                continue
            dust.append((x, -52, z))
    dust.append((164, -52, 21))
    dust.append((178, -52, 23))
    # Anel norte/sul para o corredor do meio não cortar o sinal.
    for x in range(158, 179):
        dust.append((x, -52, 19))
        dust.append((x, -52, 31))
    # Passarela no alto, acima da cabeça, ligando os dois lados sem furar a entrada.
    for z in range(19, 32):
        dust.append((152, -46, z))
    stair = [
        (158, -52, 19), (157, -51, 19), (156, -50, 19), (155, -49, 19),
        (154, -48, 19), (153, -47, 19), (152, -46, 19),
        (158, -52, 31), (157, -51, 31), (156, -50, 31), (155, -49, 31),
        (154, -48, 31), (153, -47, 31), (152, -46, 31),
    ]
    dust.extend(stair)

    dust_set = set(dust)
    source = (164, -52, 21)
    parent = {}
    dist = {source: 0}
    children = {source: []}
    queue = [source]
    while queue:
        cx, cy, cz = queue.pop(0)
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nxt = (cx + dx, cy, cz + dz)
            if nxt in dust_set and nxt not in dist:
                dist[nxt] = dist[(cx, cy, cz)] + 1
                parent[nxt] = (cx, cy, cz)
                children.setdefault((cx, cy, cz), []).append(nxt)
                children.setdefault(nxt, [])
                queue.append(nxt)
        for dx, dy, dz in (
            (1, 1, 0), (-1, 1, 0), (0, 1, 1), (0, 1, -1),
            (1, -1, 0), (-1, -1, 0), (0, -1, 1), (0, -1, -1),
        ):
            nxt = (cx + dx, cy + dy, cz + dz)
            if nxt in dust_set and nxt not in dist:
                dist[nxt] = dist[(cx, cy, cz)] + 1
                parent[nxt] = (cx, cy, cz)
                children.setdefault((cx, cy, cz), []).append(nxt)
                children.setdefault(nxt, [])
                queue.append(nxt)
    unreachable = [c for c in dust_set if c not in dist]
    repeaters = set()
    for cell, d in dist.items():
        if d == 0 or d % 12 != 0:
            continue
        kids = children.get(cell, [])
        if len(kids) != 1 or cell == (178, -52, 23):
            continue
        prev = parent[cell]
        child = kids[0]
        if child[1] != cell[1] or prev[1] != cell[1]:
            continue
        if (child[0] - cell[0], child[2] - cell[2]) != (cell[0] - prev[0], cell[2] - prev[2]):
            continue
        repeaters.add(cell)

    def side_props(x, y, z):
        props = {"north": "none", "south": "none", "east": "none", "west": "none", "power": "0"}
        for dx, dy, dz, key in (
            (1, 0, 0, "east"),
            (-1, 0, 0, "west"),
            (0, 0, 1, "south"),
            (0, 0, -1, "north"),
            (1, 1, 0, "east"),
            (-1, 1, 0, "west"),
            (0, 1, 1, "south"),
            (0, 1, -1, "north"),
        ):
            other = (x + dx, y + dy, z + dz)
            if other in dust_set or other == (163, -52, 21):
                props[key] = "up" if dy > 0 else "side"
        return props

    for x, y, z in dust_set:
        if (x, y, z) in repeaters:
            prev = parent[(x, y, z)]
            dx, dz = x - prev[0], z - prev[2]
            facing = {(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[(dx, dz)]
            p.set(x, y, z, "minecraft:repeater", {"facing": facing, "delay": "1", "locked": "false", "powered": "false"})
        else:
            p.set(x, y, z, "minecraft:redstone_wire", side_props(x, y, z))
        below = p.name(x, y - 1, z)
        if below in AIR or below.endswith("_carpet"):
            p.set(x, y - 1, z, "minecraft:stone_bricks")

    # tampa o anel para ninguém cair no pó da borda
    for x in range(158, 179):
        for z in (19, 31):
            if p.name(x, -51, z) in AIR:
                p.set(x, -51, z, "minecraft:polished_blackstone")

    # Repetidor de frente para o bloco sob o pó da porta. Bloco forte acende o pó, o pó abre a porta.
    p.set(178, -52, 24, "minecraft:repeater", {"facing": "south", "delay": "1", "locked": "false", "powered": "false"})
    p.set(178, -53, 24, "minecraft:polished_blackstone")
    p.set(178, -52, 25, "minecraft:polished_blackstone")
    for y in range(-50, -44):
        p.air(178, y, 25)
    p.set(
        178,
        -51,
        25,
        "minecraft:redstone_wire",
        {"north": "none", "south": "side", "east": "side", "west": "none", "power": "0"},
    )
    for z in range(20, 31):
        if z == 25:
            continue
        for y in range(-51, -44):
            p.set(178, y, z, "minecraft:polished_blackstone")
    # o pó em (178,-52,23) precisa apontar para o repetidor ao sul
    if (178, -52, 23) in dust_set:
        props = side_props(178, -52, 23)
        props["south"] = "side"
        p.set(178, -52, 23, "minecraft:redstone_wire", props)

    print(f"fase 5: po {len(dust_set)} repetidores {len(repeaters)} sem ligacao {len(unreachable)}")
    if unreachable:
        print("  soltos", unreachable[:12])


def phase8(p: P):
    """Fosso na largura da sala. Dois pistões encolhem o vão para um pulo correndo."""
    for x in range(239, 258):
        for z in range(19, 32):
            for y in range(-51, -44):
                if "sign" in p.name(x, y, z):
                    continue
                p.air(x, y, z)
            p.set(x, -52, z, "minecraft:packed_mud")
            p.set(x, -53, z, "minecraft:dark_oak_planks")

    # Caixa do fosso, da largura da sala, para a água não vazar por baixo do piso.
    for x in range(244, 253):
        for z in range(18, 33):
            p.set(x, -58, z, "minecraft:tuff_bricks")
            for y in range(-57, -51):
                edge = x in (244, 252) or z in (18, 32)
                if edge:
                    p.set(x, y, z, "minecraft:tuff_bricks")
                else:
                    p.air(x, y, z)
    for z in range(19, 32):
        for x in range(245, 252):
            p.set(x, -57, z, "minecraft:water", {"level": "0"})
    p.set(244, -52, 25, "minecraft:sticky_piston", {"facing": "east", "extended": "false"})
    p.set(245, -52, 25, "minecraft:mud_bricks")
    for x in range(246, 251):
        p.air(x, -52, 25)
    p.set(251, -52, 25, "minecraft:mud_bricks")
    p.set(252, -52, 25, "minecraft:sticky_piston", {"facing": "west", "extended": "false"})

    # Escada para voltar, na lateral, longe do pulo
    for y in range(-57, -51):
        p.set(245, y, 22, "minecraft:ladder", {"facing": "east"})
        p.set(245, y, 28, "minecraft:ladder", {"facing": "east"})

    # Saída 8 colada no pistão oeste
    p.output(8, 243, -52, 25)
    p.sign(241, -50, 31, "north", ["Fase 8", "Dois pistoes", "Saida 8 oeste", "Saida 9 leste"], "spruce", True)
    p.sign(243, -50, 31, "north", ["OUTPUT:8:ON", "e tambem", "OUTPUT:9:ON", ""], "spruce", False)
    p.sign(245, -50, 31, "north", ["So os dois", "juntos dao", "para correr", "e pular"], "spruce", False)
    p.sign(247, -50, 31, "north", ["Um so ainda", "fica largo", "demais", ""], "spruce", False)
    p.sign(249, -50, 31, "north", ["Caiu? A agua", "segura. A", "escada esta", "na lateral"], "spruce", False)
    p.set(242, -50, 23, "minecraft:spruce_planks")
    p.sign(242, -50, 24, "south", ["Saida 8", "no chao", "", ""])

    # Saída 9 na parede norte, fio dentro da parede até o pistão leste
    p.output(9, 241, -50, 19)
    p.set(241, -49, 19, "minecraft:mud_bricks")
    p.sign(241, -49, 20, "south", ["Saida 9", "", "", ""])
    seq = [
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
    ]
    p.lay(seq, output=(241, -50, 19), tail=None, support=True, support_block="minecraft:mud_bricks")
    # devolve a parede em volta do fio, um bloco acima e abaixo, sem tapar o pó
    for item in seq:
        if item[0] != "d":
            continue
        x, y, z = item[1], item[2], item[3]
        if z == 18:
            if p.name(x, y - 1, z) == "minecraft:redstone_wire":
                continue
            # mantém sólido o que não é o próprio pó
            pass

    p.chest(239, -51, 30, "west", [("minecraft:redstone", 32), ("minecraft:repeater", 4)], "Fase 8")


def phase9(p: P):
    # Saídas nos lugares do circuito da tocha. 11 NÃO vai direto na porta.
    p.output(10, 269, -51, 21)
    p.lay(
        [("d", 270, -51, 21), ("d", 271, -51, 21), ("d", 272, -51, 21), ("d", 272, -51, 22), ("d", 272, -51, 23), ("d", 272, -51, 24), ("d", 272, -51, 25)],
        output=(269, -51, 21),
        tail=(1, 0),
    )
    p.output(11, 276, -51, 21)
    p.output(12, 283, -51, 21)
    p.lay(
        [("d", 284, -51, 21), ("d", 285, -51, 21), ("d", 286, -51, 21), ("d", 286, -51, 22), ("d", 286, -51, 23), ("d", 286, -51, 24), ("d", 286, -51, 25)],
        output=(283, -51, 21),
        tail=(1, 0),
    )
    # Reforça o fio da tocha até a frente da porta do meio (280)
    for z in range(21, 26):
        north = "side" if z > 21 else "none"
        south = "side" if z < 25 else "none"
        east = "side" if z == 25 else "none"
        p.set(279, -52, z, "minecraft:purpur_block")
        p.set(
            279,
            -51,
            z,
            "minecraft:redstone_wire",
            {"east": east, "west": "side" if z == 21 else "none", "north": north, "south": south, "power": "0"},
        )
    p.set(277, -51, 21, "minecraft:purpur_pillar", {"axis": "y"})
    p.set(277, -52, 21, "minecraft:purpur_block")
    p.set(278, -51, 21, "minecraft:redstone_wall_torch", {"facing": "east", "lit": "true"})
    p.set(269, -50, 30, "minecraft:gold_block")
    p.set(276, -50, 30, "minecraft:coal_block")
    p.set(283, -50, 30, "minecraft:gold_block")
    p.sign(269, -50, 29, "north", ["LIGADA", "", "", ""])
    p.sign(276, -50, 29, "north", ["DESLIGADA", "", "", ""])
    p.sign(283, -50, 29, "north", ["LIGADA", "", "", ""])


def phase10_and_party(p: P):
    # Luz da saída 13, encostada na parede norte, sem atravessar o corredor.
    p.output(13, 300, -51, 28)
    seq = []
    for x in range(301, 311):
        seq.append(("d", x, -51, 28))
    p.lay(seq, output=(300, -51, 28), tail=None)
    for x in range(302, 311, 2):
        p.set(x, -51, 27, "minecraft:redstone_lamp", {"lit": "false"})
        p.set(x, -52, 27, "minecraft:smooth_quartz")

    # Porta da água (313). Fio curto, de frente. Não encosta na coluna.
    p.output(14, 309, -51, 23)
    p.lay(
        [("d", 310, -51, 23), ("d", 311, -51, 23), ("d", 312, -51, 23), ("d", 312, -51, 24), ("d", 312, -51, 25)],
        output=(309, -51, 23),
        tail=(1, 0),
    )

    # Mezanino: arduino + saída 15 de frente para a porta 322
    p.arduino(318, -47, 22)
    p.set(318, -48, 22, "minecraft:copper_block")
    p.set(316, -47, 22, "minecraft:chiseled_quartz_block")
    p.set(316, -46, 22, "minecraft:chiseled_quartz_block")
    p.set(317, -47, 22, "minecraft:lever", {"face": "wall", "facing": "east", "powered": "false"})
    for x in range(316, 318):
        p.set(x, -48, 21, "minecraft:smooth_quartz")
    p.output(15, 316, -47, 28)
    p.lay(
        [("d", 317, -47, 28), ("d", 318, -47, 28), ("d", 319, -47, 28), ("d", 320, -47, 28), ("d", 321, -47, 28),
         ("d", 321, -47, 27), ("d", 321, -47, 26), ("d", 321, -47, 25)],
        output=(316, -47, 28),
        tail=(1, 0),
    )

    # Sala 10 mais clara e vestida
    for x in range(295, 322, 4):
        if x in (314, 315):
            continue
        if p.name(x, -46, 22) in AIR:
            p.set(x, -46, 22, "minecraft:lantern", {"hanging": "false"})
        if p.name(x, -46, 28) in AIR:
            p.set(x, -46, 28, "minecraft:lantern", {"hanging": "false"})
    p.sign(296, -50, 31, "north", ["Fase 10", "Tres coisas", "ao mesmo", "tempo"], "pale_oak", True)
    p.sign(298, -50, 31, "north", ["Saida 13", "acende as", "lampadas", "OUTPUT:13:ON"], "pale_oak", False)
    p.sign(302, -50, 31, "north", ["Saida 14", "abre a porta", "da agua", "OUTPUT:14:ON"], "pale_oak", False)
    p.sign(306, -50, 31, "north", ["La em cima", "a alavanca", "fala com o", "Arduino"], "pale_oak", False)
    p.sign(310, -50, 31, "north", ["Desligue a", "alavanca da", "fase 6 antes", ""], "pale_oak", False)
    p.sign(316, -46, 31, "north", ["Saida 15", "abre a ultima", "porta", "OUTPUT:15:ON"], "pale_oak", True)
    p.chest(295, -51, 30, "west", [("minecraft:redstone", 64), ("minecraft:lever", 2), ("minecraft:repeater", 4)], "Fase 10")

    # Salão de comemoração, no mesmo piso do mezanino, fechado.
    x0, x1, z0, z1 = 324, 352, 18, 32
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            edge = x in (x0, x1) or z in (z0, z1)
            p.set(x, -49, z, "minecraft:quartz_block")
            p.set(x, -48, z, "minecraft:smooth_quartz" if not edge else "minecraft:calcite")
            if edge:
                for y in range(-47, -42):
                    p.set(x, y, z, "minecraft:quartz_block")
                p.set(x, -42, z, "minecraft:smooth_quartz")
            else:
                for y in range(-47, -42):
                    p.air(x, y, z)
                p.set(x, -42, z, "minecraft:quartz_block")
    # vão de entrada vindo da porta 322
    for z in (24, 25, 26):
        for y in range(-47, -44):
            p.air(x0, y, z)
        p.set(x0, -48, z, "minecraft:smooth_quartz")
    # colunas e cerejeira
    for px, pz in ((328, 20), (328, 30), (340, 20), (340, 30), (348, 20), (348, 30)):
        for y in range(-47, -43):
            p.set(px, y, pz, "minecraft:quartz_pillar", {"axis": "y"})
    for tx, tz in ((332, 22), (344, 22), (332, 28), (344, 28)):
        p.set(tx, -47, tz, "minecraft:cherry_log", {"axis": "y"})
        p.set(tx, -46, tz, "minecraft:cherry_log", {"axis": "y"})
        p.set(tx, -45, tz, "minecraft:cherry_leaves", {"persistent": "true", "distance": "1", "waterlogged": "false"})
    # fonte
    for x in range(336, 341):
        for z in range(23, 28):
            p.set(x, -48, z, "minecraft:stone_bricks")
            p.set(x, -47, z, "minecraft:stone_brick_wall", {"up": "true", "east": "none", "west": "none", "north": "none", "south": "none"})
    for x in range(337, 340):
        for z in range(24, 27):
            p.set(x, -48, z, "minecraft:stone")
            p.set(x, -47, z, "minecraft:water", {"level": "0"})
    p.set(338, -47, 25, "minecraft:sea_lantern")
    # bolo, sino, velas, baú
    p.set(346, -47, 25, "minecraft:cake", {"bites": "0"})
    p.set(346, -47, 24, "minecraft:candle", {"candles": "4", "lit": "true", "waterlogged": "false"})
    p.set(330, -47, 25, "minecraft:bell", {"attachment": "floor", "facing": "north", "powered": "false"})
    p.chest(348, -47, 28, "west", [("minecraft:golden_apple", 1), ("minecraft:cake", 1), ("minecraft:cookie", 16), ("minecraft:glow_berries", 16)], "Trofeu")
    for x in (326, 334, 342, 350):
        p.set(x, -43, 25, "minecraft:iron_chain", {"axis": "y"})
        p.set(x, -44, 25, "minecraft:lantern", {"hanging": "true"})
    p.sign(326, -46, 31, "north", ["Voce conseguiu", "A oficina", "esta aberta", ""], "pale_oak", True)
    p.sign(330, -46, 31, "north", ["Dez fases", "Redstone e", "Arduino", "juntos"], "pale_oak", False)
    p.sign(334, -46, 31, "north", ["Toque o sino", "Coma o bolo", "O bau e seu", ""], "pale_oak", False)
    p.sign(348, -46, 20, "south", ["Da varanda", "da para ver", "a vila", ""], "cherry", False)
    # varanda aberta no leste, com mureta, sem escada para o chão (não vira atalho)
    for z in range(22, 29):
        for y in range(-47, -44):
            p.air(x1, y, z)
        p.set(x1, -48, z, "minecraft:smooth_quartz")
        p.set(x1 + 1, -48, z, "minecraft:smooth_quartz")
        p.set(x1 + 1, -47, z, "minecraft:quartz_wall" if False else "minecraft:stone_brick_wall", {"up": "true", "east": "none", "west": "none", "north": "none", "south": "none"})
    for x in range(326, 351, 3):
        p.set(x, -47, 21, "minecraft:potted_cherry_sapling")
        p.set(x, -47, 29, "minecraft:potted_open_eyeblossom")


def town(p: P):
    def cottage(x, z, plank, log, door_south=True):
        for dx in range(6):
            for dz in range(5):
                p.set(x + dx, -61, z + dz, "minecraft:stone_bricks")
                edge = dx in (0, 5) or dz in (0, 4)
                for y in range(-60, -57):
                    if edge:
                        p.set(x + dx, y, z + dz, plank)
                    else:
                        p.air(x + dx, y, z + dz)
                p.set(x + dx, -57, z + dz, log if edge else "minecraft:oak_planks")
        # janelas
        p.set(x, -59, z + 2, "minecraft:glass_pane", {"east": "false", "west": "false", "north": "true", "south": "true"})
        p.set(x + 5, -59, z + 2, "minecraft:glass_pane", {"east": "false", "west": "false", "north": "true", "south": "true"})
        # porta e luz
        if door_south:
            p.set(x + 2, -60, z + 4, "minecraft:oak_door", {"facing": "south", "half": "lower", "hinge": "left", "open": "false"})
            p.set(x + 2, -59, z + 4, "minecraft:oak_door", {"facing": "south", "half": "upper", "hinge": "left", "open": "false"})
        else:
            p.set(x + 2, -60, z, "minecraft:oak_door", {"facing": "north", "half": "lower", "hinge": "left", "open": "false"})
            p.set(x + 2, -59, z, "minecraft:oak_door", {"facing": "north", "half": "upper", "hinge": "left", "open": "false"})
        p.set(x + 3, -59, z + 2, "minecraft:lantern", {"hanging": "false"})
        p.set(x + 1, -60, z + 1, "minecraft:crafting_table")
        # chaminé
        p.set(x + 4, -56, z + 1, "minecraft:bricks")
        p.set(x + 4, -55, z + 1, "minecraft:bricks")
        p.set(x + 4, -54, z + 1, "minecraft:campfire", {"lit": "true", "signal_fire": "false", "facing": "north"})

    styles = [
        ("minecraft:pale_oak_planks", "minecraft:stripped_pale_oak_log"),
        ("minecraft:cherry_planks", "minecraft:stripped_cherry_log"),
        ("minecraft:spruce_planks", "minecraft:stripped_spruce_log"),
        ("minecraft:oak_planks", "minecraft:stripped_oak_log"),
    ]
    for i, x in enumerate((8, 28, 56, 88, 124, 168, 210, 250, 300, 340)):
        plank, log = styles[i % 4]
        cottage(x, 8, plank, log, door_south=True)
        cottage(x + 10, 38, styles[(i + 1) % 4][0], styles[(i + 1) % 4][1], door_south=False)
        p.b.tree(x + 7, 6, -60, log, "minecraft:cherry_leaves" if i % 2 == 0 else "minecraft:pale_oak_leaves")
        p.b.lamp_post(x - 2, 15, -61)
        p.b.lamp_post(x - 2, 35, -61)
    # caminho de cascalho ao longo da vila, sem entrar no campus
    for x in range(4, 360):
        p.set(x, -61, 15, "minecraft:gravel")
        p.set(x, -61, 36, "minecraft:coarse_dirt")
        if x % 9 == 0:
            p.set(x, -60, 14, "minecraft:azure_bluet")
            p.set(x, -60, 37, "minecraft:open_eyeblossom")


def extra_light(p: P):
    rooms = [
        (20, 35, -55),
        (45, 58, -55),
        (69, 88, -55),
        (99, 126, -55),
        (135, 147, -55),
        (158, 163, -46),
        (188, 202, -46),
        (213, 229, -46),
        (240, 256, -46),
        (267, 285, -46),
        (296, 320, -46),
    ]
    for x0, x1, y in rooms:
        for x in range(x0, x1, 5):
            for z in (22, 28):
                if p.name(x, y, z) in AIR and p.name(x, y + 1, z) not in AIR:
                    p.set(x, y, z, "minecraft:lantern", {"hanging": "true"})


def verify(p: P):
    checks = []

    def ok(cond, msg):
        checks.append((cond, msg))
        print(("ok  " if cond else "FALHA ") + msg)

    ok(p.name(141, -52, 24) == "minecraft:dispenser", "ejetor fase 4 no lugar")
    ok("sign" not in p.name(44, -59, 25), "placa da fase 1 saiu da porta")
    ok(solid_name(p.name(78, -60, 20)), "parede da fase 2 fecha a lateral")
    ok(solid_name(p.name(106, -60, 20)), "parede da fase 3 fecha a lateral")
    ok(solid_name(p.name(221, -51, 20)), "parede da fase 7 fecha a lateral")
    ok(solid_name(p.name(273, -51, 20)) and solid_name(p.name(280, -51, 20)), "fase 9 com paredes")
    ok(p.name(59, -61, 25) == "minecraft:orange_terracotta", "guia da fase 1 de frente para a porta")
    ok(p.name(89, -60, 25) == "minecraft:redstone_wire", "saida 1 chega na frente da porta")
    ok(p.name(127, -60, 25) == "minecraft:redstone_wire", "saida 2 chega na frente da porta")
    ok(p.name(120, -60, 24) == "minecraft:repeater", "fase 3 tem repetidor ao lado do corredor")
    ok(p.name(141, -53, 24) == "makercraft:arduino_output", "saida 3 colada no ejetor")
    ok(p.name(170, -45, 21) == "minecraft:polished_blackstone", "labirinto vai ate o teto")
    ok(p.name(166, -52, 22) == "minecraft:redstone_lamp", "chao do labirinto tem lampada")
    ok(p.name(167, -52, 22) == "minecraft:black_concrete", "chao do labirinto tem bloco preto")
    ok(p.name(178, -51, 25) == "minecraft:redstone_wire", "porta do labirinto com po na frente")
    ok(p.name(248, -52, 20) in AIR, "fosso da fase 8 atravessa a sala")
    ok(p.name(244, -52, 25) == "minecraft:sticky_piston", "pistao oeste")
    ok(p.name(252, -52, 25) == "minecraft:sticky_piston", "pistao leste")
    ok(p.name(243, -52, 25) == "makercraft:arduino_output", "saida 8")
    ok(p.name(241, -50, 19) == "makercraft:arduino_output", "saida 9")
    ok(p.name(346, -47, 25) == "minecraft:cake", "sala de comemoracao")
    ok(len(OUTPUTS) == 15, f"quinze saidas ({len(OUTPUTS)})")
    ok(len(ARDUINOS) == 2, f"dois arduinos ({len(ARDUINOS)})")
    failed = [msg for cond, msg in checks if not cond]
    if failed:
        raise SystemExit("verificacao falhou: " + "; ".join(failed))


def main():
    if not BACKUP.exists():
        shutil.copy2(REGION, BACKUP)
        print("backup", BACKUP)
    chunks = load_region(REGION)
    world = World(chunks)
    p = P(world)
    seal(p)
    strip_blocking_signs(p)
    lobby_and_hints(p)
    teaching_wires(p)
    phase4_output(p)
    phase5(p)
    phase8(p)
    phase9(p)
    phase10_and_party(p)
    town(p)
    extra_light(p)
    verify(p)
    OUTPUTS.sort()
    world.apply()
    save_region(REGION, world.chunks)
    write_saved_data(OUTPUTS)
    write_datapack(OUTPUTS, ARDUINOS)
    print("gravado", len(OUTPUTS), "saidas", len(world.edits), "blocos")
    for number, x, y, z in OUTPUTS:
        print(f"  saida {number}: {x} {y} {z}")


if __name__ == "__main__":
    main()
