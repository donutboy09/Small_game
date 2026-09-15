import math
import random
import sys

import pygame

import audio
from engine import Renderer
from entities import Enemy, Particle, Pickup, Player
from settings import (
    MOUSE_SENS,
    PLAYER_START_AMMO,
    RENDER_H,
    RENDER_W,
    ROT_SPEED,
    WINDOW_H,
    WINDOW_W,
    WEAPON_COOLDOWN,
    WEAPON_DAMAGE,
    WEAPON_RANGE,
    WEAPON_SPREAD,
)
from world import World

MENU = "menu"
PLAY = "play"
PAUSE = "pause"
DEAD = "dead"


def make_weapon():
    g = pygame.Surface((120, 95), pygame.SRCALPHA)
    pygame.draw.polygon(g, (46, 48, 58), [(44, 95), (76, 95), (70, 60), (50, 60)])
    pygame.draw.polygon(g, (28, 30, 38), [(44, 95), (76, 95), (70, 60), (50, 60)], 2)
    pygame.draw.rect(g, (74, 78, 92), (36, 44, 48, 22), border_radius=5)
    pygame.draw.rect(g, (50, 54, 66), (36, 44, 48, 22), 2, border_radius=5)
    pygame.draw.rect(g, (88, 94, 110), (52, 18, 16, 32), border_radius=4)
    pygame.draw.rect(g, (56, 60, 74), (52, 18, 16, 32), 2, border_radius=4)
    pygame.draw.rect(g, (28, 32, 42), (50, 13, 20, 8), border_radius=3)
    pygame.draw.rect(g, (112, 120, 142), (57, 36, 6, 8), border_radius=2)
    pygame.draw.line(g, (132, 142, 168), (40, 48), (80, 48), 2)
    return g


def make_flash():
    s = pygame.Surface((64, 64), pygame.SRCALPHA)
    center = (32, 32)
    for a in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
        pygame.draw.polygon(
            s,
            (255, 236, 150, 150),
            [
                center,
                (32 + math.cos(a) * 30, 32 + math.sin(a) * 30),
                (32 + math.cos(a + 0.45) * 12, 32 + math.sin(a + 0.45) * 12),
            ],
        )
    for r, col in ((22, (255, 214, 110, 45)), (15, (255, 228, 150, 95)), (9, (255, 246, 210, 170)), (5, (255, 255, 255, 235))):
        pygame.draw.circle(s, col, center, r)
    return s


class Game:
    def __init__(self):
        pygame.init()
        audio.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Dungeon Strike 3D")
        self.clock = pygame.time.Clock()
        self.frame = pygame.Surface((RENDER_W, RENDER_H))
        self.renderer = Renderer()
        self.effect_layer = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        self.font_small = pygame.font.Font(None, 22)
        self.font = pygame.font.Font(None, 30)
        self.font_big = pygame.font.Font(None, 84)
        self.weapon = make_weapon()
        self.weapon_flash = make_flash()
        self.rng = random.Random()
        self.firing = False
        self.running = True
        self._menu_setup()

    def _menu_setup(self):
        self.state = MENU
        self.world = World(seed=self.rng.randrange(1 << 30))
        cx, cy = self.world.start_pos()
        self.player = Player(cx + 0.5, cy + 0.5, 0.0)
        self.enemies = []
        self.pickups = []
        self.particles = []
        for _ in range(3):
            x, y = self.world.random_open(self.rng, (self.player.x, self.player.y), 2.5)
            self.enemies.append(Enemy(x, y, self.rng.randrange(3)))
        if self.enemies:
            e = self.enemies[0]
            self.player.angle = math.atan2(e.y - self.player.y, e.x - self.player.x)
        self.wave = 0
        self.wave_active = False
        self.wave_timer = 0.0
        self.shoot_cd = 0.0
        self.shake = 0.0
        self.hit_marker = 0.0
        self.banner_text = ""
        self.banner_timer = 0.0

    def start_game(self):
        self.player = Player(0.5, 0.5, 0.0)
        self.player.ammo = PLAYER_START_AMMO
        self.player.score = 0
        self.wave = 0
        self.wave_active = False
        self.wave_timer = 0.0
        self.particles = []
        self.enemies = []
        self.pickups = []
        self.shoot_cd = 0.0
        self.shake = 0.0
        self.hit_marker = 0.0
        self.banner_text = ""
        self.banner_timer = 0.0
        self.firing = False
        self.state = PLAY
        self.start_wave()
        self._grab()

    def _grab(self):
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        pygame.mouse.get_rel()

    def _release(self):
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)

    def set_banner(self, text, seconds):
        self.banner_text = text
        self.banner_timer = seconds

    def pick_kind(self):
        r = self.rng.random()
        if self.wave < 2:
            return 0
        if self.wave < 4:
            return 0 if r < 0.7 else 2
        if r < 0.5:
            return 0
        if r < 0.8:
            return 2
        return 1

    def start_wave(self):
        self.wave += 1
        self.world = World(seed=self.rng.randrange(1 << 30))
        cx, cy = self.world.start_pos()
        self.player.x = cx + 0.5
        self.player.y = cy + 0.5
        self.player.angle = self.rng.uniform(0.0, math.tau)
        self.enemies = []
        self.pickups = []
        self.particles = []
        count = min(4 + self.wave * 2, 22)
        scale = 1.0 + 0.12 * (self.wave - 1)
        for _ in range(count):
            x, y = self.world.random_open(self.rng, (self.player.x, self.player.y), 6.0)
            self.enemies.append(Enemy(x, y, self.pick_kind(), hp_scale=scale))
        for _ in range(2):
            x, y = self.world.random_open(self.rng, (self.player.x, self.player.y), 3.0)
            self.pickups.append(Pickup(x, y, "health"))
        for _ in range(3):
            x, y = self.world.random_open(self.rng, (self.player.x, self.player.y), 3.0)
            self.pickups.append(Pickup(x, y, "ammo"))
        self.wave_active = True
        self.wave_timer = 0.0
        self.set_banner("WAVE %d" % self.wave, 1.9)
        audio.play("pickup")

    def spawn_particles(self, x, y, color, count):
        if len(self.particles) > 240:
            del self.particles[: len(self.particles) - 240]
        for _ in range(count):
            a = self.rng.uniform(0.0, math.tau)
            sp = self.rng.uniform(0.5, 3.2)
            life = self.rng.uniform(0.25, 0.65)
            self.particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp, life, color))

    def ray_wall_dist(self, x, y, dx, dy, maxd=20.0):
        t = 0.0
        while t < maxd:
            t += 0.08
            if self.world.is_wall(int(x + dx * t), int(y + dy * t)):
                return t
        return maxd

    def shoot(self):
        if self.state != PLAY or self.shoot_cd > 0.0:
            return
        p = self.player
        if p.ammo <= 0:
            audio.play("empty")
            self.shoot_cd = 0.3
            return
        p.ammo -= 1
        self.shoot_cd = WEAPON_COOLDOWN
        p.muzzle = 0.07
        self.shake = min(0.5, self.shake + 0.26)
        audio.play("shoot")

        dirx = math.cos(p.angle)
        diry = math.sin(p.angle)
        best = None
        best_t = 1e9
        for e in self.enemies:
            ex = e.x - p.x
            ey = e.y - p.y
            t = ex * dirx + ey * diry
            if t <= 0.2 or t > WEAPON_RANGE:
                continue
            perp = abs(ex * diry - ey * dirx)
            if perp > WEAPON_SPREAD * (1.0 + t * 0.12):
                continue
            if not self.world.line_of_sight(p.x, p.y, e.x, e.y):
                continue
            if t < best_t:
                best_t = t
                best = e

        if best is not None:
            dmg = WEAPON_DAMAGE + self.rng.randint(0, 7)
            killed = best.hit(dmg)
            self.spawn_particles(best.x, best.y, (214, 40, 52), 12)
            self.hit_marker = 0.16
            if killed:
                p.score += best.points
                self.spawn_particles(best.x, best.y, (140, 26, 40), 22)
                self.enemies.remove(best)
                audio.play("die")
                roll = self.rng.random()
                if roll < 0.2:
                    self.pickups.append(Pickup(best.x, best.y, "ammo"))
                elif roll < 0.32:
                    self.pickups.append(Pickup(best.x, best.y, "health"))
            else:
                audio.play("hit")
        else:
            d = self.ray_wall_dist(p.x, p.y, dirx, diry, WEAPON_RANGE)
            hx = p.x + dirx * max(0.2, d - 0.06)
            hy = p.y + diry * max(0.2, d - 0.06)
            self.spawn_particles(hx, hy, (188, 188, 200), 4)

    def die(self):
        self.state = DEAD
        self._release()
        self.shake = 0.8
        audio.play("gameover")

    def update(self, dt):
        p = self.player
        if self.shoot_cd > 0.0:
            self.shoot_cd -= dt
        if p.muzzle > 0.0:
            p.muzzle -= dt
        if p.hurt > 0.0:
            p.hurt = max(0.0, p.hurt - dt * 1.8)
        if p.heal > 0.0:
            p.heal = max(0.0, p.heal - dt * 1.8)
        if self.hit_marker > 0.0:
            self.hit_marker -= dt
        if self.shake > 0.0:
            self.shake = max(0.0, self.shake - dt * 2.2)
        if self.banner_timer > 0.0:
            self.banner_timer -= dt

        if self.state != PLAY:
            return

        keys = pygame.key.get_pressed()
        forward = int(keys[pygame.K_w] or keys[pygame.K_UP]) - int(keys[pygame.K_s] or keys[pygame.K_DOWN])
        strafe = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        turn = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        p.angle += turn * ROT_SPEED * dt
        p.move(self.world, forward, strafe, dt)

        if keys[pygame.K_SPACE] or self.firing:
            self.shoot()

        for e in list(self.enemies):
            if e.update(self.world, p, dt, self.rng) == "attack":
                audio.play("hurt")
                self.shake = min(0.6, self.shake + 0.22)

        if p.hp <= 0:
            self.die()
            return

        for pk in list(self.pickups):
            pk.update(dt)
            if math.hypot(pk.x - p.x, pk.y - p.y) < 0.6:
                if pk.kind == "health":
                    p.heal_amount(30)
                    p.score += 25
                else:
                    p.add_ammo(24)
                    p.score += 15
                audio.play("pickup")
                self.pickups.remove(pk)

        for pt in list(self.particles):
            if not pt.update(dt):
                self.particles.remove(pt)

        if self.wave_active and not self.enemies:
            self.wave_active = False
            self.wave_timer = 2.6
            p.heal_amount(25)
            p.add_ammo(12)
            audio.play("wave")
            self.set_banner("WAVE %d CLEARED" % self.wave, 2.4)

        if not self.wave_active:
            self.wave_timer -= dt
            if self.wave_timer <= 0.0:
                self.start_wave()

    def sprites(self):
        return self.enemies + self.pickups + self.particles

    def draw_weapon(self, frame):
        p = self.player
        bobx = math.sin(p.bob) * 5.0
        boby = abs(math.cos(p.bob)) * 4.0
        if not p.moving:
            bobx *= 0.25
            boby *= 0.25
        w = self.weapon
        gx = RENDER_W // 2 - w.get_width() // 2 + int(bobx)
        gy = RENDER_H - w.get_height() + int(boby) + 8
        if p.muzzle > 0.0:
            fl = self.weapon_flash
            fx = gx + w.get_width() // 2 - fl.get_width() // 2
            fy = gy + 15 - fl.get_height() // 2
            frame.blit(fl, (fx, fy))
        frame.blit(w, (gx, gy))

    def draw_vignette(self, color, intensity):
        layer = self.effect_layer
        steps = 34
        for i in range(steps):
            a = int(150 * intensity * (1.0 - i / steps))
            if a <= 0:
                continue
            m = i * 7
            pygame.draw.rect(layer, (color[0], color[1], color[2], a), (m, m, WINDOW_W - 2 * m, WINDOW_H - 2 * m), 7)

    def draw_effects(self):
        p = self.player
        if p.hurt <= 0.01 and p.heal <= 0.01:
            return
        self.effect_layer.fill((0, 0, 0, 0))
        if p.hurt > 0.01:
            self.draw_vignette((214, 26, 36), p.hurt)
        if p.heal > 0.01:
            self.draw_vignette((34, 220, 140), p.heal)
        self.screen.blit(self.effect_layer, (0, 0))

    def draw_minimap(self):
        s = self.screen
        cells = 11
        half = cells // 2
        cell = 12
        size = cells * cell
        ox = 16
        oy = 16
        pygame.draw.rect(s, (6, 9, 16), (ox - 3, oy - 3, size + 6, size + 6), border_radius=7)
        p = self.player
        cx = int(p.x)
        cy = int(p.y)
        for gy in range(cy - half, cy + half + 1):
            for gx in range(cx - half, cx + half + 1):
                sx = ox + (gx - (cx - half)) * cell
                sy = oy + (gy - (cy - half)) * cell
                if self.world.is_wall(gx, gy):
                    pygame.draw.rect(s, (74, 92, 118), (sx, sy, cell - 1, cell - 1))
                else:
                    pygame.draw.rect(s, (22, 28, 40), (sx, sy, cell - 1, cell - 1))
        for e in self.enemies:
            if abs(e.x - cx) <= half and abs(e.y - cy) <= half:
                ex = ox + int((e.x - (cx - half)) * cell)
                ey = oy + int((e.y - (cy - half)) * cell)
                pygame.draw.circle(s, (240, 70, 70), (ex, ey), 3)
        for pk in self.pickups:
            if abs(pk.x - cx) <= half and abs(pk.y - cy) <= half:
                px = ox + int((pk.x - (cx - half)) * cell)
                py = oy + int((pk.y - (cy - half)) * cell)
                c = (240, 90, 110) if pk.kind == "health" else (240, 200, 90)
                pygame.draw.circle(s, c, (px, py), 2)
        px = ox + int((p.x - (cx - half)) * cell)
        py = oy + int((p.y - (cy - half)) * cell)
        dx = math.cos(p.angle)
        dy = math.sin(p.angle)
        pts = [
            (px + dx * 7, py + dy * 7),
            (px - dy * 4 - dx * 4, py + dx * 4 - dy * 4),
            (px + dy * 4 - dx * 4, py - dx * 4 - dy * 4),
        ]
        pygame.draw.polygon(s, (80, 240, 190), pts)

    def draw_banner(self):
        a = max(0.0, min(1.0, self.banner_timer))
        col = (int(255 * a), int(226 * a), int(130 * a))
        img = self.font_big.render(self.banner_text, True, col)
        self.screen.blit(img, (WINDOW_W // 2 - img.get_width() // 2, WINDOW_H // 4))

    def draw_hud(self):
        s = self.screen
        p = self.player
        cx = WINDOW_W // 2
        cy = WINDOW_H // 2
        col = (255, 90, 90) if self.hit_marker > 0.0 else (232, 240, 255)
        gap = 7
        ln = 13
        pygame.draw.line(s, col, (cx - gap - ln, cy), (cx - gap, cy), 2)
        pygame.draw.line(s, col, (cx + gap, cy), (cx + gap + ln, cy), 2)
        pygame.draw.line(s, col, (cx, cy - gap - ln), (cx, cy - gap), 2)
        pygame.draw.line(s, col, (cx, cy + gap), (cx, cy + gap + ln), 2)

        bx = 24
        by = WINDOW_H - 58
        bw = 280
        bh = 26
        pygame.draw.rect(s, (10, 14, 22), (bx - 2, by - 2, bw + 4, bh + 4), border_radius=8)
        ratio = p.hp / p.max_hp
        fill = int(bw * ratio)
        if ratio > 0.5:
            hc = (60, 210, 130)
        elif ratio > 0.25:
            hc = (230, 190, 60)
        else:
            hc = (230, 70, 70)
        if fill > 0:
            pygame.draw.rect(s, hc, (bx, by, fill, bh), border_radius=6)
        pygame.draw.rect(s, (92, 112, 142), (bx - 2, by - 2, bw + 4, bh + 4), 2, border_radius=8)
        self.text(s, "HP %d" % int(p.hp), self.font_small, (255, 255, 255), (bx + 10, by + 4))

        ammo = self.font.render("AMMO %d" % p.ammo, True, (255, 214, 120))
        s.blit(ammo, (WINDOW_W - ammo.get_width() - 28, WINDOW_H - 54))
        score = self.font.render("SCORE %d" % p.score, True, (120, 240, 210))
        s.blit(score, (WINDOW_W - score.get_width() - 28, 22))
        wave = self.font.render("WAVE %d" % self.wave, True, (204, 212, 255))
        s.blit(wave, (WINDOW_W // 2 - wave.get_width() // 2, 20))
        self.draw_minimap()
        if self.banner_timer > 0.0 and self.banner_text:
            self.draw_banner()

    def text(self, surf, msg, font, color, pos):
        surf.blit(font.render(msg, True, color), pos)

    def draw_overlays(self):
        s = self.screen
        if self.state == MENU:
            panel = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            panel.fill((4, 6, 12, 190))
            s.blit(panel, (0, 0))
            title = self.font_big.render("DUNGEON STRIKE 3D", True, (90, 240, 210))
            s.blit(title, (WINDOW_W // 2 - title.get_width() // 2, 120))
            lines = [
                "WASD move    MOUSE look    CLICK / SPACE shoot",
                "ARROWS turn    P / ESC pause    M mute",
                "",
                "Clear every wave. Grab health and ammo. Survive.",
            ]
            y = 260
            for ln in lines:
                img = self.font.render(ln, True, (210, 222, 240))
                s.blit(img, (WINDOW_W // 2 - img.get_width() // 2, y))
                y += 40
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 320.0)
            c = int(140 + 115 * pulse)
            prompt = self.font.render("PRESS ENTER TO START", True, (c, 240, 210))
            s.blit(prompt, (WINDOW_W // 2 - prompt.get_width() // 2, 460))
        elif self.state == PAUSE:
            panel = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            panel.fill((4, 6, 12, 170))
            s.blit(panel, (0, 0))
            t = self.font_big.render("PAUSED", True, (230, 236, 250))
            s.blit(t, (WINDOW_W // 2 - t.get_width() // 2, WINDOW_H // 2 - 90))
            h = self.font.render("ESC / P to resume", True, (200, 212, 232))
            s.blit(h, (WINDOW_W // 2 - h.get_width() // 2, WINDOW_H // 2 + 10))
        elif self.state == DEAD:
            panel = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            panel.fill((30, 4, 8, 180))
            s.blit(panel, (0, 0))
            t = self.font_big.render("YOU DIED", True, (235, 70, 80))
            s.blit(t, (WINDOW_W // 2 - t.get_width() // 2, WINDOW_H // 2 - 120))
            info = self.font.render(
                "SCORE %d    WAVE %d" % (self.player.score, self.wave), True, (240, 230, 220)
            )
            s.blit(info, (WINDOW_W // 2 - info.get_width() // 2, WINDOW_H // 2 - 20))
            h = self.font.render("PRESS R TO RESTART", True, (220, 226, 240))
            s.blit(h, (WINDOW_W // 2 - h.get_width() // 2, WINDOW_H // 2 + 40))

    def render(self):
        self.renderer.render(self.frame, self.world, self.player, self.sprites())
        self.draw_weapon(self.frame)
        ox = 0
        oy = 0
        if self.shake > 0.01:
            m = self.shake * 11.0
            ox = int(self.rng.uniform(-m, m))
            oy = int(self.rng.uniform(-m, m))
        scaled = pygame.transform.scale(self.frame, (WINDOW_W, WINDOW_H))
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled, (ox, oy))
        self.draw_effects()
        self.draw_hud()
        self.draw_overlays()
        pygame.display.flip()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == PLAY:
                    self.state = PAUSE
                    self._release()
                elif self.state == PAUSE:
                    self.state = PLAY
                    self._grab()
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if self.state in (MENU, DEAD):
                    self.start_game()
            elif event.key == pygame.K_p:
                if self.state == PLAY:
                    self.state = PAUSE
                    self._release()
                elif self.state == PAUSE:
                    self.state = PLAY
                    self._grab()
            elif event.key == pygame.K_r and self.state == DEAD:
                self.start_game()
            elif event.key == pygame.K_m:
                audio.toggle_mute()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state in (MENU, DEAD):
                self.start_game()
            elif self.state == PLAY:
                self.firing = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.firing = False
        elif event.type == pygame.MOUSEMOTION and self.state == PLAY:
            self.player.angle += event.rel[0] * MOUSE_SENS

    def run(self):
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(dt)
            self.render()
        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    Game().run()
