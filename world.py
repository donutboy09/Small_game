import math
import random

from settings import WALL_TYPES


def wall_style(x, y):
    return 1 + ((x // 4) + (y // 4) * 3) % WALL_TYPES


class World:
    def __init__(self, width=32, height=32, seed=None):
        self.w = width
        self.h = height
        self.rng = random.Random(seed)
        self.grid = [[wall_style(x, y) for x in range(width)] for y in range(height)]
        self.rooms = []
        self._generate()

    def at(self, x, y):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return 1
        return self.grid[y][x]

    def is_wall(self, x, y):
        return self.at(x, y) > 0

    def collides(self, x, y, r):
        for cy in range(int(y - r), int(y + r) + 1):
            for cx in range(int(x - r), int(x + r) + 1):
                if self.is_wall(cx, cy):
                    return True
        return False

    def line_of_sight(self, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 0.001:
            return True
        steps = int(dist / 0.12) + 1
        sx = dx / steps
        sy = dy / steps
        x = x1
        y = y1
        for _ in range(steps):
            x += sx
            y += sy
            if self.is_wall(int(x), int(y)):
                return False
        return True

    def start_pos(self):
        return self._center(self.rooms[0])

    def random_open(self, rng, min_dist_from=None, min_dist=0.0, tries=300):
        for _ in range(tries):
            x = rng.uniform(1.5, self.w - 1.5)
            y = rng.uniform(1.5, self.h - 1.5)
            if self.collides(x, y, 0.45):
                continue
            if min_dist_from is not None:
                dx = x - min_dist_from[0]
                dy = y - min_dist_from[1]
                if dx * dx + dy * dy < min_dist * min_dist:
                    continue
            return x, y
        return self._center(self.rooms[-1])

    def _carve(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.grid[y][x] = 0

    def _carve_rect(self, x, y, w, h):
        for cy in range(y, y + h):
            for cx in range(x, x + w):
                self._carve(cx, cy)

    def _overlaps(self, room):
        x, y, w, h = room
        for (rx, ry, rw, rh) in self.rooms:
            if x - 1 < rx + rw and x + w + 1 > rx and y - 1 < ry + rh and y + h + 1 > ry:
                return True
        return False

    def _center(self, room):
        x, y, w, h = room
        return x + w // 2, y + h // 2

    def _hcorr(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self._carve(x, y)

    def _vcorr(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self._carve(x, y)

    def _generate(self):
        attempts = 0
        while len(self.rooms) < 8 and attempts < 500:
            attempts += 1
            rw = self.rng.randint(4, 8)
            rh = self.rng.randint(4, 8)
            rx = self.rng.randint(1, self.w - rw - 2)
            ry = self.rng.randint(1, self.h - rh - 2)
            room = (rx, ry, rw, rh)
            if self._overlaps(room):
                continue
            self.rooms.append(room)
            self._carve_rect(rx, ry, rw, rh)

        if len(self.rooms) < 2:
            self.rooms = [(1, 1, self.w - 2, self.h - 2)]
            self._carve_rect(1, 1, self.w - 2, self.h - 2)
            return

        for i in range(1, len(self.rooms)):
            x1, y1 = self._center(self.rooms[i - 1])
            x2, y2 = self._center(self.rooms[i])
            if self.rng.random() < 0.5:
                self._hcorr(x1, x2, y1)
                self._vcorr(y1, y2, x2)
            else:
                self._vcorr(y1, y2, x1)
                self._hcorr(x1, x2, y2)

        for _ in range(4):
            a = self.rng.randrange(len(self.rooms))
            b = self.rng.randrange(len(self.rooms))
            if a == b:
                continue
            x1, y1 = self._center(self.rooms[a])
            x2, y2 = self._center(self.rooms[b])
            self._hcorr(x1, x2, y1)
            self._vcorr(y1, y2, x2)
