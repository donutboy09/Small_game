import math

import pygame

import textures
from settings import (
    RENDER_W,
    RENDER_H,
    FOV,
    MAX_DEPTH,
    TEX_SIZE,
    SHADE_LEVELS,
)


class Renderer:
    def __init__(self):
        self.wall_columns = []
        for tex in textures.make_wall_textures():
            levels = textures.shade_levels(tex, alpha=False)
            level_cols = []
            for lv in levels:
                level_cols.append([lv.subsurface((x, 0, 1, TEX_SIZE)) for x in range(TEX_SIZE)])
            self.wall_columns.append(level_cols)
        self.background = textures.make_background()
        self.zbuf = [MAX_DEPTH] * RENDER_W
        self.horizon = RENDER_H // 2

    def render(self, frame, world, player, sprites):
        frame.blit(self.background, (0, 0))
        self._render_walls(frame, world, player)
        self._render_sprites(frame, player, sprites)

    def _render_walls(self, frame, world, player):
        dirx = math.cos(player.angle)
        diry = math.sin(player.angle)
        plane_len = math.tan(FOV / 2.0)
        planex = -diry * plane_len
        planey = dirx * plane_len
        px = player.x
        py = player.y
        horizon = self.horizon
        zbuf = self.zbuf
        wall_columns = self.wall_columns
        scale = pygame.transform.scale
        blit = frame.blit

        for col in range(RENDER_W):
            camx = 2.0 * col / RENDER_W - 1.0
            raydx = dirx + planex * camx
            raydy = diry + planey * camx
            mapx = int(px)
            mapy = int(py)
            deltax = abs(1.0 / raydx) if raydx != 0.0 else 1e30
            deltay = abs(1.0 / raydy) if raydy != 0.0 else 1e30
            if raydx < 0.0:
                stepx = -1
                sidex = (px - mapx) * deltax
            else:
                stepx = 1
                sidex = (mapx + 1.0 - px) * deltax
            if raydy < 0.0:
                stepy = -1
                sidey = (py - mapy) * deltay
            else:
                stepy = 1
                sidey = (mapy + 1.0 - py) * deltay

            side = 0
            wall = 0
            for _ in range(96):
                if sidex < sidey:
                    sidex += deltax
                    mapx += stepx
                    side = 0
                else:
                    sidey += deltay
                    mapy += stepy
                    side = 1
                wall = world.at(mapx, mapy)
                if wall > 0:
                    break

            if side == 0:
                perp = sidex - deltax
            else:
                perp = sidey - deltay
            if perp < 0.03:
                perp = 0.03
            zbuf[col] = perp

            line_h = int(RENDER_H / perp)
            if line_h > RENDER_H * 3:
                line_h = RENDER_H * 3
            if line_h < 1:
                line_h = 1
            draw_start = -line_h // 2 + horizon

            if side == 0:
                wallx = py + perp * raydy
            else:
                wallx = px + perp * raydx
            wallx -= math.floor(wallx)
            texx = int(wallx * TEX_SIZE)
            if (side == 0 and raydx > 0.0) or (side == 1 and raydy < 0.0):
                texx = TEX_SIZE - texx - 1
            if texx < 0:
                texx = 0
            elif texx >= TEX_SIZE:
                texx = TEX_SIZE - 1

            level = int(SHADE_LEVELS * (1.0 - min(perp, MAX_DEPTH) / MAX_DEPTH))
            if side == 1:
                level -= 2
            if level < 0:
                level = 0
            elif level >= SHADE_LEVELS:
                level = SHADE_LEVELS - 1

            colsurf = wall_columns[wall - 1][level][texx]
            blit(scale(colsurf, (1, line_h)), (col, draw_start))

    def _render_sprites(self, frame, player, sprites):
        dirx = math.cos(player.angle)
        diry = math.sin(player.angle)
        plane_len = math.tan(FOV / 2.0)
        planex = -diry * plane_len
        planey = dirx * plane_len
        horizon = self.horizon
        invdet = 1.0 / (planex * diry - dirx * planey)
        zbuf = self.zbuf

        ordered = sorted(
            sprites,
            key=lambda s: (s.x - player.x) ** 2 + (s.y - player.y) ** 2,
            reverse=True,
        )

        for sp in ordered:
            dx = sp.x - player.x
            dy = sp.y - player.y
            tx = invdet * (diry * dx - dirx * dy)
            ty = invdet * (-planey * dx + planex * dy)
            if ty <= 0.2:
                continue

            screen_x = int((RENDER_W / 2.0) * (1.0 + tx / ty))
            line_h = RENDER_H / ty
            h = int(line_h * sp.size)
            if h < 1:
                continue
            src = sp.surface
            sw = src.get_width()
            sh = src.get_height()
            w = int(h * sw / sh)
            if w < 1:
                continue

            bottom = int(horizon + line_h * 0.5 - line_h * sp.v_offset)
            top = bottom - h
            x0 = screen_x - w // 2
            x1 = x0 + w

            level = int(SHADE_LEVELS * (1.0 - min(ty, MAX_DEPTH) / MAX_DEPTH))
            if level < 0:
                level = 0
            elif level >= SHADE_LEVELS:
                level = SHADE_LEVELS - 1
            shaded = sp.shaded[level]

            a = max(0, x0)
            b = min(RENDER_W, x1)
            run = None
            for col in range(a, b):
                if ty < zbuf[col]:
                    if run is None:
                        run = col
                elif run is not None:
                    self._blit_run(frame, shaded, run, col, x0, w, top, h, sw, sh)
                    run = None
            if run is not None:
                self._blit_run(frame, shaded, run, b, x0, w, top, h, sw, sh)

    def _blit_run(self, frame, shaded, a, b, x0, w, top, h, sw, sh):
        sx0 = int((a - x0) / w * sw)
        sx1 = int((b - x0) / w * sw)
        if sx1 <= sx0:
            sx1 = sx0 + 1
        if sx0 < 0:
            sx0 = 0
        if sx1 > sw:
            sx1 = sw
        if sx1 <= sx0:
            return
        sub = shaded.subsurface((sx0, 0, sx1 - sx0, sh))
        scaled = pygame.transform.scale(sub, (b - a, h))
        frame.blit(scaled, (a, top))
