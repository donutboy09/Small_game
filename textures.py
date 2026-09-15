import math
import random

import pygame

from settings import TEX_SIZE, SHADE_LEVELS, FOG_COLOR, RENDER_W, RENDER_H

_sheets = {}


def _lerp(a, b, t):
    return a + (b - a) * t


def _mix(c1, c2, t):
    return (
        int(_lerp(c1[0], c2[0], t)),
        int(_lerp(c1[1], c2[1], t)),
        int(_lerp(c1[2], c2[2], t)),
    )


def _jitter(rng, c, amount):
    return (
        max(0, min(255, c[0] + rng.randint(-amount, amount))),
        max(0, min(255, c[1] + rng.randint(-amount, amount))),
        max(0, min(255, c[2] + rng.randint(-amount, amount))),
    )


def make_brick(rng):
    surf = pygame.Surface((TEX_SIZE, TEX_SIZE))
    surf.fill((52, 36, 32))
    bh = 16
    bw = 32
    for row in range(TEX_SIZE // bh):
        y = row * bh
        off = 0 if row % 2 == 0 else -bw // 2
        for x in range(off - bw, TEX_SIZE + bw, bw):
            c = _jitter(rng, (122, 58, 46), 18)
            pygame.draw.rect(surf, c, (x + 1, y + 1, bw - 2, bh - 2))
    return surf


def make_stone(rng):
    surf = pygame.Surface((TEX_SIZE, TEX_SIZE))
    surf.fill((94, 96, 102))
    for _ in range(260):
        x = rng.randrange(TEX_SIZE)
        y = rng.randrange(TEX_SIZE)
        surf.set_at((x, y), _jitter(rng, (94, 96, 102), 26))
    for _ in range(7):
        x = rng.randrange(TEX_SIZE)
        y = rng.randrange(TEX_SIZE)
        w = rng.randint(10, 26)
        h = rng.randint(10, 26)
        c = 68 + rng.randint(0, 52)
        pygame.draw.rect(surf, (c, c, c + 6), (x, y, w, h), 1)
    return surf


def make_tech(rng):
    surf = pygame.Surface((TEX_SIZE, TEX_SIZE))
    surf.fill((36, 44, 64))
    for y in range(0, TEX_SIZE, 32):
        for x in range(0, TEX_SIZE, 32):
            pygame.draw.rect(surf, (52, 66, 94), (x + 2, y + 2, 28, 28), border_radius=4)
            pygame.draw.rect(surf, (26, 32, 48), (x + 2, y + 2, 28, 28), 2, border_radius=4)
            for (rx, ry) in ((7, 7), (25, 7), (7, 25), (25, 25)):
                pygame.draw.circle(surf, (92, 108, 140), (x + rx, y + ry), 2)
    pygame.draw.line(surf, (110, 200, 220), (0, 0), (0, TEX_SIZE), 2)
    return surf


def make_hazard(rng):
    surf = pygame.Surface((TEX_SIZE, TEX_SIZE))
    surf.fill((28, 26, 24))
    for i in range(-TEX_SIZE, TEX_SIZE * 2, 22):
        pygame.draw.line(surf, (198, 160, 44), (i, 0), (i + TEX_SIZE, TEX_SIZE), 9)
    for _ in range(140):
        x = rng.randrange(TEX_SIZE)
        y = rng.randrange(TEX_SIZE)
        surf.set_at((x, y), _jitter(rng, (38, 34, 28), 12))
    return surf


def shade(surf, brightness, alpha=False):
    s = surf.copy()
    v = max(0, min(255, int(brightness * 255)))
    if alpha:
        s.fill((v, v, v, 255), special_flags=pygame.BLEND_RGBA_MULT)
    else:
        s.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    return s


def shade_levels(surf, alpha=False):
    levels = []
    for i in range(SHADE_LEVELS):
        b = 0.10 + 0.90 * (i / (SHADE_LEVELS - 1))
        levels.append(shade(surf, b, alpha))
    return levels


def make_wall_textures():
    rng = random.Random(1337)
    return [make_brick(rng), make_stone(rng), make_tech(rng), make_hazard(rng)]


def make_background():
    surf = pygame.Surface((RENDER_W, RENDER_H))
    half = RENDER_H // 2
    ceil_near = (46, 52, 72)
    floor_near = (58, 50, 40)
    for y in range(RENDER_H):
        if y < half:
            d = (0.5 * RENDER_H) / max(1, half - y)
            base = ceil_near
        else:
            d = (0.5 * RENDER_H) / max(1, y - half)
            base = floor_near
        fog_t = min(1.0, d / 14.0)
        c = _mix(base, FOG_COLOR, fog_t)
        band = 0.78 if int(d * 2.0) % 2 == 0 else 1.0
        c = (int(c[0] * band), int(c[1] * band), int(c[2] * band))
        pygame.draw.line(surf, c, (0, y), (RENDER_W, y))
    fog = pygame.Surface((RENDER_W, RENDER_H), pygame.SRCALPHA)
    for i in range(24):
        a = int(150 * (1.0 - i / 24.0))
        y = half - 12 + i
        pygame.draw.line(fog, (*FOG_COLOR, a), (0, y), (RENDER_W, y))
    surf.blit(fog, (0, 0))
    return surf


def _make_enemy0():
    s = pygame.Surface((TEX_SIZE, TEX_SIZE), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 90), (14, 56, 36, 7))
    pygame.draw.rect(s, (38, 104, 58), (22, 42, 8, 17), border_radius=3)
    pygame.draw.rect(s, (38, 104, 58), (34, 42, 8, 17), border_radius=3)
    pygame.draw.ellipse(s, (74, 190, 96), (16, 20, 32, 30))
    pygame.draw.ellipse(s, (48, 142, 70), (16, 20, 32, 30), 2)
    pygame.draw.ellipse(s, (66, 172, 86), (6, 26, 12, 20))
    pygame.draw.ellipse(s, (66, 172, 86), (46, 26, 12, 20))
    pygame.draw.circle(s, (98, 216, 120), (32, 16), 13)
    pygame.draw.circle(s, (255, 238, 92), (26, 14), 4)
    pygame.draw.circle(s, (255, 238, 92), (38, 14), 4)
    pygame.draw.circle(s, (18, 18, 18), (26, 15), 2)
    pygame.draw.circle(s, (18, 18, 18), (38, 15), 2)
    pygame.draw.arc(s, (22, 46, 28), (24, 18, 16, 10), math.pi, 2 * math.pi, 2)
    pygame.draw.polygon(s, (238, 238, 238), [(27, 21), (29, 25), (31, 21)])
    pygame.draw.polygon(s, (238, 238, 238), [(33, 21), (35, 25), (37, 21)])
    return s


def _make_enemy1():
    s = pygame.Surface((TEX_SIZE, TEX_SIZE), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 100), (8, 55, 48, 8))
    pygame.draw.rect(s, (108, 30, 30), (16, 42, 12, 18), border_radius=4)
    pygame.draw.rect(s, (108, 30, 30), (36, 42, 12, 18), border_radius=4)
    pygame.draw.ellipse(s, (168, 48, 48), (8, 16, 48, 36))
    pygame.draw.ellipse(s, (120, 30, 30), (8, 16, 48, 36), 2)
    pygame.draw.ellipse(s, (150, 42, 42), (0, 24, 14, 24))
    pygame.draw.ellipse(s, (150, 42, 42), (50, 24, 14, 24))
    pygame.draw.circle(s, (182, 56, 56), (32, 15), 14)
    pygame.draw.polygon(s, (222, 214, 200), [(20, 8), (14, 0), (26, 9)])
    pygame.draw.polygon(s, (222, 214, 200), [(44, 8), (50, 0), (38, 9)])
    pygame.draw.circle(s, (255, 210, 60), (26, 14), 4)
    pygame.draw.circle(s, (255, 210, 60), (38, 14), 4)
    pygame.draw.circle(s, (30, 0, 0), (26, 15), 2)
    pygame.draw.circle(s, (30, 0, 0), (38, 15), 2)
    pygame.draw.line(s, (70, 12, 12), (22, 24), (42, 24), 3)
    for i in range(5):
        pygame.draw.polygon(s, (240, 240, 240), [(23 + i * 4, 24), (25 + i * 4, 29), (27 + i * 4, 24)])
    return s


def _make_enemy2():
    s = pygame.Surface((TEX_SIZE, TEX_SIZE), pygame.SRCALPHA)
    glow = pygame.Surface((TEX_SIZE, TEX_SIZE), pygame.SRCALPHA)
    for r, a in ((28, 36), (22, 60), (16, 96), (11, 140)):
        pygame.draw.circle(glow, (146, 88, 255, a), (32, 32), r)
    s.blit(glow, (0, 0))
    pygame.draw.circle(s, (176, 128, 255), (32, 32), 13)
    pygame.draw.circle(s, (226, 196, 255), (32, 32), 8)
    pygame.draw.circle(s, (255, 255, 255), (32, 32), 4)
    pygame.draw.circle(s, (60, 20, 110), (27, 30), 3)
    pygame.draw.circle(s, (60, 20, 110), (37, 30), 3)
    return s


def _make_health():
    s = pygame.Surface((TEX_SIZE, TEX_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(s, (238, 240, 246), (16, 20, 32, 32), border_radius=7)
    pygame.draw.rect(s, (196, 44, 66), (16, 20, 32, 32), 3, border_radius=7)
    pygame.draw.rect(s, (212, 44, 66), (28, 26, 8, 20), border_radius=2)
    pygame.draw.rect(s, (212, 44, 66), (22, 32, 20, 8), border_radius=2)
    return s


def _make_ammo():
    s = pygame.Surface((TEX_SIZE, TEX_SIZE), pygame.SRCALPHA)
    pygame.draw.rect(s, (58, 54, 38), (13, 24, 38, 26), border_radius=5)
    pygame.draw.rect(s, (206, 174, 62), (13, 24, 38, 26), 3, border_radius=5)
    for i in range(3):
        x = 19 + i * 10
        pygame.draw.rect(s, (244, 214, 92), (x, 31, 7, 14), border_radius=2)
        pygame.draw.polygon(s, (255, 232, 140), [(x, 31), (x + 3, 24), (x + 6, 31)])
    return s


def _make_particle(color):
    s = pygame.Surface((10, 10), pygame.SRCALPHA)
    pygame.draw.circle(s, color, (5, 5), 5)
    return s


def _named(name):
    rng = random.Random(hash(name) & 0xFFFF)
    if name == "enemy0":
        return _make_enemy0()
    if name == "enemy1":
        return _make_enemy1()
    if name == "enemy2":
        return _make_enemy2()
    if name == "health":
        return _make_health()
    if name == "ammo":
        return _make_ammo()
    if name.startswith("particle:"):
        parts = name.split(":")
        return _make_particle((int(parts[1]), int(parts[2]), int(parts[3])))
    return _make_enemy0()


def get_sheet(name):
    if name not in _sheets:
        base = _named(name)
        _sheets[name] = (base, shade_levels(base, alpha=True))
    return _sheets[name]


def particle_sheet(color):
    return get_sheet("particle:%d:%d:%d" % color)
