import math
import random

import textures
from settings import (
    PLAYER_RADIUS,
    PLAYER_MAX_HP,
    PLAYER_MAX_AMMO,
    MOVE_SPEED,
    STRAFE_SPEED,
    ENEMY_ATTACK_RANGE,
    ENEMY_DETECT_RANGE,
    ENEMY_HEAR_RANGE,
)


class Player:
    def __init__(self, x, y, angle=0.0):
        self.x = x
        self.y = y
        self.angle = angle
        self.hp = PLAYER_MAX_HP
        self.max_hp = PLAYER_MAX_HP
        self.ammo = 48
        self.max_ammo = PLAYER_MAX_AMMO
        self.score = 0
        self.hurt = 0.0
        self.heal = 0.0
        self.bob = 0.0
        self.muzzle = 0.0
        self.moving = False

    def move(self, world, forward, strafe, dt):
        if forward == 0 and strafe == 0:
            self.moving = False
            return
        self.moving = True
        dx = math.cos(self.angle) * forward * MOVE_SPEED * dt
        dy = math.sin(self.angle) * forward * MOVE_SPEED * dt
        sx = -math.sin(self.angle) * strafe * STRAFE_SPEED * dt
        sy = math.cos(self.angle) * strafe * STRAFE_SPEED * dt
        self._slide(world, dx + sx, dy + sy)
        self.bob += dt * 9.0

    def _slide(self, world, dx, dy):
        if not world.collides(self.x + dx, self.y, PLAYER_RADIUS):
            self.x += dx
        if not world.collides(self.x, self.y + dy, PLAYER_RADIUS):
            self.y += dy

    def damage(self, amount):
        self.hp -= amount
        self.hurt = min(1.0, self.hurt + 0.55)
        if self.hp < 0:
            self.hp = 0

    def heal_amount(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)
        self.heal = min(1.0, self.heal + 0.5)

    def add_ammo(self, amount):
        self.ammo = min(self.max_ammo, self.ammo + amount)


class Enemy:
    KINDS = {
        0: dict(hp=30, speed=1.75, dmg=8, points=100, size=0.62, sheet="enemy0", v=0.0, radius=0.32),
        1: dict(hp=78, speed=1.15, dmg=17, points=250, size=0.92, sheet="enemy1", v=0.0, radius=0.42),
        2: dict(hp=18, speed=2.55, dmg=6, points=150, size=0.5, sheet="enemy2", v=0.22, radius=0.3),
    }

    def __init__(self, x, y, kind, hp_scale=1.0):
        cfg = Enemy.KINDS[kind]
        self.x = x
        self.y = y
        self.kind = kind
        self.max_hp = int(cfg["hp"] * hp_scale)
        self.hp = self.max_hp
        self.speed = cfg["speed"]
        self.dmg = cfg["dmg"]
        self.points = cfg["points"]
        self.size = cfg["size"]
        self.v_offset = cfg["v"]
        self.radius = cfg["radius"]
        base, shaded = textures.get_sheet(cfg["sheet"])
        self.surface = base
        self.shaded = shaded
        self.flash = 0.0
        self.cd = 0.0
        self.awake = False
        self.phase = random.random() * 6.28
        self.wander = 0.0

    def update(self, world, player, dt, rng):
        if self.flash > 0.0:
            self.flash -= dt
        if self.cd > 0.0:
            self.cd -= dt
        if self.kind == 2:
            self.phase += dt * 3.0
            self.v_offset = 0.22 + math.sin(self.phase) * 0.05

        dx = player.x - self.x
        dy = player.y - self.y
        dist = math.hypot(dx, dy) or 0.0001
        los = world.line_of_sight(self.x, self.y, player.x, player.y)

        if dist < ENEMY_DETECT_RANGE and los:
            self.awake = True
        if dist < ENEMY_HEAR_RANGE:
            self.awake = True

        if not self.awake:
            return

        if dist < ENEMY_ATTACK_RANGE and los:
            if self.cd <= 0.0:
                player.damage(self.dmg)
                self.cd = 1.0
                return "attack"
            return

        if dist > 0.75:
            step = self.speed * dt
            mx = dx / dist * step
            my = dy / dist * step
            moved = False
            if not world.collides(self.x + mx, self.y, self.radius):
                self.x += mx
                moved = True
            if not world.collides(self.x, self.y + my, self.radius):
                self.y += my
                moved = True
            if not moved:
                base = math.atan2(dy, dx)
                for off in (0.7, -0.7, 1.4, -1.4, 2.1, -2.1):
                    a = base + off
                    nx = math.cos(a) * step
                    ny = math.sin(a) * step
                    if not world.collides(self.x + nx, self.y, self.radius):
                        self.x += nx
                        moved = True
                    if not world.collides(self.x, self.y + ny, self.radius):
                        self.y += ny
                        moved = True
                    if moved:
                        break
            if not moved:
                self.wander += dt
        return None

    def hit(self, amount):
        self.hp -= amount
        self.flash = 0.14
        self.awake = True
        return self.hp <= 0


class Pickup:
    def __init__(self, x, y, kind):
        self.x = x
        self.y = y
        self.kind = kind
        self.size = 0.42
        self.v_offset = 0.05
        self.phase = random.random() * 6.28
        base, shaded = textures.get_sheet(kind)
        self.surface = base
        self.shaded = shaded

    def update(self, dt):
        self.phase += dt * 2.4
        self.v_offset = 0.06 + math.sin(self.phase) * 0.05


class Particle:
    def __init__(self, x, y, vx, vy, life, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.size = 0.09
        self.v_offset = 0.42
        base, shaded = textures.particle_sheet(color)
        self.surface = base
        self.shaded = shaded

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.90
        self.vy *= 0.90
        self.life -= dt
        return self.life > 0.0
