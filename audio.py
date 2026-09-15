import array
import math
import random

import pygame

_rate = 22050
_channels = 1
_ok = False
_muted = False
_sounds = {}


def toggle_mute():
    global _muted
    _muted = not _muted
    return _muted


def init():
    global _ok, _rate, _channels
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(22050, -16, 1, 256)
        info = pygame.mixer.get_init()
        if info is None:
            _ok = False
            return
        _rate, _fmt, _channels = info
        _ok = True
        _build()
    except Exception:
        _ok = False


def _osc(wave, phase):
    if wave == "square":
        return 1.0 if math.sin(phase) >= 0.0 else -1.0
    if wave == "saw":
        frac = (phase / (2.0 * math.pi)) % 1.0
        return frac * 2.0 - 1.0
    if wave == "tri":
        frac = (phase / (2.0 * math.pi)) % 1.0
        return 4.0 * abs(frac - 0.5) - 1.0
    return math.sin(phase)


def _sweep(f0, f1, dur, wave="sine", decay=8.0, vol=0.6, noise=0.0):
    n = max(1, int(_rate * dur))
    phase = 0.0
    out = []
    for i in range(n):
        t = i / _rate
        f = f0 + (f1 - f0) * (t / dur if dur > 0 else 0.0)
        phase += 2.0 * math.pi * f / _rate
        env = math.exp(-t * decay)
        v = _osc(wave, phase) * vol * env
        if noise > 0.0:
            v += random.uniform(-1.0, 1.0) * noise * env
        out.append(v)
    return out


def _tone(freq, dur, wave="square", decay=20.0, vol=0.5):
    return _sweep(freq, freq, dur, wave, decay, vol)


def _to_sound(samples):
    data = array.array("h")
    for s in samples:
        v = int(max(-1.0, min(1.0, s)) * 32000)
        data.append(v)
        if _channels == 2:
            data.append(v)
    return pygame.mixer.Sound(buffer=data.tobytes())


def _build():
    global _sounds
    if not _ok:
        return
    try:
        s = {}
        s["shoot"] = _to_sound(_sweep(260, 90, 0.13, "saw", 34.0, 0.7, 0.55))
        s["empty"] = _to_sound(_tone(120, 0.05, "square", 60.0, 0.35))
        s["hit"] = _to_sound(_sweep(520, 300, 0.08, "square", 40.0, 0.5))
        s["die"] = _to_sound(_sweep(400, 70, 0.45, "saw", 7.0, 0.6, 0.12))
        s["hurt"] = _to_sound(_sweep(180, 90, 0.28, "saw", 11.0, 0.6, 0.25))
        s["pickup"] = _to_sound(_tone(680, 0.09, "tri", 24.0, 0.5) + _tone(1020, 0.12, "tri", 20.0, 0.5))
        s["wave"] = _to_sound(
            _tone(440, 0.16, "tri", 12.0, 0.5)
            + _tone(660, 0.16, "tri", 12.0, 0.5)
            + _tone(880, 0.3, "tri", 8.0, 0.55)
        )
        s["gameover"] = _to_sound(
            _tone(400, 0.22, "saw", 6.0, 0.6)
            + _tone(280, 0.22, "saw", 6.0, 0.6)
            + _tone(160, 0.6, "saw", 4.0, 0.6)
        )
        _sounds = s
    except Exception:
        _sounds = {}


def play(name):
    if not _ok or _muted:
        return
    snd = _sounds.get(name)
    if snd is None:
        return
    try:
        snd.play()
    except Exception:
        pass
