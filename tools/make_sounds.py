#!/usr/bin/env python3
"""Generates the built-in sounds into sounds/: synthesized loops and jingles (pure Python)
and voice lines via macOS `say` + `ffmpeg`. Run: python3 tools/make_sounds.py"""
import math
import os
import random
import struct
import subprocess
import tempfile
import wave
from collections.abc import Callable
from functools import partial

SR = 32000
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'sounds')
Buf = list[float]
Tone = Callable[..., None]
Jingle = Callable[[Buf, Tone], None]
NAMES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def hz(n: str, st: int = 0) -> float:  # 'A4', 'C#3' -> Hz
    midi = NAMES[n[0]] + n.count('#') + 12 * (int(n[-1]) + 1) + st
    return 440 * 2 ** ((midi - 69) / 12)


def osc(kind: str, ph: float) -> float:
    p = ph % 1
    if kind == 'sq': return 1.0 if p < .5 else -1.0
    if kind == 'pulse': return 1.0 if p < .25 else -1.0
    if kind == 'saw': return 2 * p - 1
    if kind == 'tri': return 4 * abs(p - .5) - 1
    if kind == 'noise': return random.uniform(-1, 1)
    return math.sin(2 * math.pi * p)


def tone(buf: Buf, t0: float, dur: float, f: float, kind: str = 'sq', vol: float = .2, a: float = .005, r: float = .04,
         dec: float = 0, slide: float = 0, vib: float = 0, lp: float = 1, loop: bool = False) -> None:
    """Adds one note to the buffer. slide = pitch shift in octaves over the note, lp = one-pole low-pass (0..1)."""
    s0, n, N = int(t0 * SR), int((dur + r) * SR), len(buf)
    ph = y = 0.0
    for i in range(n):
        t = i / SR
        ph += f * 2 ** (slide * min(t, dur) / dur) * (1 + vib * math.sin(12 * math.pi * t)) / SR
        env = min(1, t / a)
        if t > dur: env *= 1 - (t - dur) / r
        if dec: env *= math.exp(-dec * t)
        y += lp * (osc(kind, ph) - y)
        j = s0 + i
        if loop: j %= N  # the note tail wraps to the start -> seamless loop
        elif j >= N: break
        buf[j] += y * env * vol


def kick(b: Buf, t: float, v: float = .6, **k: bool) -> None: tone(b, t, .18, 110, 'sin', v, a=.001, r=.02, dec=18, slide=-1.5, **k)
def snare(b: Buf, t: float, v: float = .25, **k: bool) -> None:
    tone(b, t, .15, 0, 'noise', v, a=.001, dec=25, lp=.5, **k)
    tone(b, t, .08, 190, 'tri', v * .8, a=.001, dec=30, **k)
def hat(b: Buf, t: float, v: float = .07, **k: bool) -> None: tone(b, t, .04, 0, 'noise', v, a=.001, r=.01, dec=60, **k)
def crash(b: Buf, t: float, v: float = .3, **k: bool) -> None: tone(b, t, 1.5, 0, 'noise', v, a=.001, r=.2, dec=3, **k)


def save(buf: Buf, name: str) -> None:
    path = os.path.join(ROOT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b''.join(struct.pack('<h', int(math.tanh(x) * 32000)) for x in buf))
    print(name)


def new_loop(bpm: float, beats: int) -> tuple[Buf, float, Tone]:
    b = [0.0] * round(60 / bpm * beats * SR)
    return b, 60 / bpm, partial(tone, b, loop=True)


# ---------- loops ----------
def arcade() -> Buf:
    b, q, T = new_loop(128, 32)
    for bar, ch in enumerate([('A3', 'C4', 'E4'), ('F3', 'A3', 'C4'), ('C4', 'E4', 'G4'), ('G3', 'B3', 'D4')] * 2):
        t0, up = bar * 4 * q, 12 if bar >= 4 else 0
        arp = [hz(n, up) for n in ch] + [hz(ch[0], 12 + up)]
        for s in range(16): T(t0 + s * q / 4, q / 4 * .8, arp[s % 4], 'pulse', .09)
        for e in range(8):
            T(t0 + e * q / 2, q / 2 * .8, hz(ch[0], -12 + 12 * (e % 2)), 'tri', .3)
            hat(b, t0 + e * q / 2, loop=True)
        for k in range(4): (kick if k % 2 == 0 else snare)(b, t0 + k * q, loop=True)
    return b


def dark() -> Buf:
    b, q, T = new_loop(100, 32)
    for i, (root, ch) in enumerate([('A1', ('A2', 'C3', 'E3')), ('F1', ('F2', 'A2', 'C3')),
                                    ('D1', ('D2', 'F2', 'A2')), ('E1', ('E2', 'G#2', 'B2'))]):
        t0 = i * 8 * q
        for n in ch: T(t0, 8 * q - .3, hz(n), 'saw', .07, a=.4, r=.3, lp=.05)
        for s in range(32): T(t0 + s * q / 4, q / 4 * .7, hz(root, 12 * (s % 4 == 0)), 'saw', .3 if s % 4 == 0 else .2, lp=.12)
        for k in range(8):
            kick(b, t0 + k * q, loop=True)
            if k % 2: snare(b, t0 + k * q, .18, loop=True)
        for s in range(32): hat(b, t0 + s * q / 4, .03 + .03 * (s % 2 == 0), loop=True)
    return b


def lofi() -> Buf:
    b, q, T = new_loop(78, 16)
    for bar, ch in enumerate([('D3', 'F3', 'A3', 'C4'), ('G2', 'B2', 'D3', 'F3'), ('C3', 'E3', 'G3', 'B3'), ('A2', 'C3', 'E3', 'G3')]):
        t0 = bar * 4 * q
        for n in ch:
            T(t0, 4 * q - .4, hz(n), 'tri', .05, a=.08, r=.4, vib=.003, lp=.3)
            for p in (0, 1.5, 2.5): T(t0 + p * q, .6, hz(n, 12), 'sin', .05, dec=4)
        for p in (0, 2.5): T(t0 + p * q, q, hz(ch[0], -12), 'sin', .35, dec=2)
        for p in (0, 1.75, 2.5): kick(b, t0 + p * q, .45, loop=True)
        for p in (1, 3): tone(b, t0 + p * q, .2, 0, 'noise', .15, a=.002, dec=18, lp=.25, loop=True)
        for e in range(8): hat(b, t0 + (e // 2 + (.6 if e % 2 else 0)) * q, .04, loop=True)
    return b


def boss() -> Buf:
    b, q, T = new_loop(160, 32)
    for bar, ch in enumerate([('E2', 'G2', 'B2'), ('C2', 'E2', 'G2'), ('D2', 'F#2', 'A2'), ('B1', 'D#2', 'F#2')] * 2):
        t0 = bar * 4 * q
        for e in range(8): T(t0 + e * q / 2, q / 2 * .7, hz(ch[0], 12 * (e in (3, 6))), 'sq', .16, lp=.3)
        if bar >= 4:
            lead = [hz(n, 24) for n in ch] + [hz(ch[0], 36)]
            for e in range(8): T(t0 + e * q / 2, q / 2 * .9, lead[[0, 1, 2, 3, 2, 1, 2, 1][e]], 'pulse', .08)
        else:
            T(t0, q * 1.5, hz(ch[1], 24), 'saw', .07, lp=.2)
        for k in range(4):
            kick(b, t0 + k * q, loop=True); kick(b, t0 + (k + .5) * q, .3, loop=True)
            if k % 2: snare(b, t0 + k * q, loop=True)
        for e in range(8): hat(b, t0 + e * q / 2, loop=True)
    return b


def synthwave() -> Buf:
    b, q, T = new_loop(100, 32)
    for i, ch in enumerate([('E3', 'G3', 'B3'), ('C3', 'E3', 'G3'), ('G2', 'B2', 'D3'), ('D3', 'F#3', 'A3')]):
        for half in (0, 1):
            t0 = (i * 2 + half) * 4 * q
            if half == 0:
                for n in ch: T(t0, 8 * q - .3, hz(n), 'saw', .045, a=.3, r=.3, lp=.06)
            for e in range(8): T(t0 + e * q / 2, q / 2 * .8, hz(ch[0], -12), 'saw', .22, lp=.15)
            if i >= 2:  # second half of the loop: arpeggio
                arp = [hz(ch[k], 12) for k in (0, 1, 2, 1)]
                for s in range(16): T(t0 + s * q / 4, q / 4 * .7, arp[s % 4], 'pulse', .06, lp=.5)
            for k in range(4):
                if k % 2: snare(b, t0 + k * q, .3, loop=True); T(t0 + k * q, .4, 0, 'noise', .08, dec=6, lp=.3)
                else: kick(b, t0 + k * q, loop=True)
            for e in range(8): hat(b, t0 + e * q / 2, .05, loop=True)
    return b


def funk() -> Buf:
    b, q, T = new_loop(104, 32)
    s16 = q / 4
    for bar, (root, ch) in enumerate([('E2', ('E3', 'G3', 'B3', 'D4'))] * 2 + [('A1', ('A2', 'C#3', 'E3', 'G3'))] * 2
                                     + [('E2', ('E3', 'G3', 'B3', 'D4'))] * 2 + [('B1', ('B2', 'D#3', 'F#3', 'A3'))] * 2):
        t0 = bar * 4 * q
        for pos, st in ((0, 0), (3, 0), (6, 12), (7, 10), (10, 0), (12, 7), (14, 10)):
            T(t0 + pos * s16, s16 * .8, hz(root, st), 'sq', .28, dec=5, lp=.2)
        for pos in (2, 6, 10, 11, 14):
            for n in ch: T(t0 + pos * s16, .07, hz(n), 'pulse', .045, r=.02, lp=.4)
        for pos in (0, 7, 10): kick(b, t0 + pos * s16, loop=True)
        for pos in (4, 12): snare(b, t0 + pos * s16, loop=True)
        for pos in (9, 15): snare(b, t0 + pos * s16, .06, loop=True)
        for s in range(16): hat(b, t0 + s * s16, .06 if s % 2 == 0 else .03, loop=True)
    return b


def quiz() -> Buf:
    b, q, T = new_loop(120, 32)
    for i, ch in enumerate([('A3', 'C4', 'E4'), ('A3', 'C4', 'E4'), ('D3', 'F3', 'A3'), ('E3', 'G#3', 'B3')]):
        t0 = i * 8 * q
        for beat in range(8):
            T(t0 + beat * q, .02, 1800 if beat % 2 == 0 else 1300, 'sin', .25, a=.001, r=.01, dec=80)  # tick-tock
            if beat % 2 == 0: T(t0 + beat * q, 2 * q, hz(ch[0], -12), 'sin', .3, dec=1.5)
        arp = [hz(ch[k]) for k in (0, 1, 2, 1)]
        for e in range(16): T(t0 + e * q / 2, q / 2 * .9, arp[e % 4], 'tri', .1, dec=5)
        for s in range(32): hat(b, t0 + s * q / 4, .02, loop=True)
    return b


def techno() -> Buf:
    b, q, T = new_loop(128, 32)
    s16 = q / 4
    acid = [0, 0, 12, 0, 3, 0, 10, 0, 0, 12, 0, 7, 0, 3, 0, 12]
    for s in range(128):
        t = s * s16
        lp = .05 + .25 * (.5 - .5 * math.cos(2 * math.pi * s / 128))  # the filter opens and closes over the loop -> no seam
        T(t, s16 * .7, hz('A1', acid[s % 16]), 'saw', .22 if s % 4 == 0 else .15, lp=lp)
        if s % 4 == 0: kick(b, t, .7, loop=True)
        if s % 4 == 2: T(t, .1, 0, 'noise', .07, a=.001, dec=20, lp=.9)  # open hat on the off-beat
        if s % 8 == 4:
            for d in (0, .012): snare(b, t + d, .14, loop=True)  # clap
        if s % 32 == 30:
            for n in ('A3', 'C4', 'E4'): T(t, .15, hz(n), 'saw', .06, lp=.3)
    return b


def epic() -> Buf:
    b, q, T = new_loop(80, 32)
    for i, ch in enumerate([('D3', 'F3', 'A3'), ('A#2', 'D3', 'F3'), ('F2', 'A2', 'C3'), ('C3', 'E3', 'G3')]):
        t0 = i * 8 * q
        for n in ch:
            T(t0, 8 * q - .4, hz(n), 'saw', .05, a=.6, r=.4, vib=.004, lp=.07)
            T(t0, 8 * q - .4, hz(n, 12), 'saw', .025, a=.8, r=.4, vib=.005, lp=.05)
        for e in range(16): T(t0 + e * q / 2, q / 2 * .8, hz(ch[0], -12), 'saw', .2 if e % 4 == 0 else .13, lp=.1)
        for bar in (0, 1):
            tb = t0 + bar * 4 * q
            kick(b, tb, .8, loop=True)
            for p in (0, 1.5, 2, 3, 3.5): T(tb + p * q, .4, 95, 'sin', .45, a=.001, dec=6, slide=-.6)  # toms
        crash(b, t0, .15, loop=True)
    return b


LOOPS = {'arcade': arcade, 'dark': dark, 'lofi': lofi, 'boss': boss,
         'synthwave': synthwave, 'funk': funk, 'quiz': quiz, 'techno': techno, 'epic': epic}


# ---------- jingles and effects ----------
def sfx(seconds: float, fn: Jingle) -> Buf:
    b = [0.0] * int(seconds * SR)
    fn(b, partial(tone, b))
    peak = max(map(abs, b))
    return [x * .7 / peak for x in b]  # match the jingle loudness to the voice lines


JINGLES: dict[str, tuple[float, Jingle]] = {}


def jingle(seconds: float) -> Callable[[Jingle], Jingle]:
    """Registers a jingle `seconds` long; the output file is named after the function."""
    def register(fn: Jingle) -> Jingle:
        JINGLES[fn.__name__] = (seconds, fn)
        return fn
    return register


@jingle(1.6)
def fanfare(b: Buf, note: Tone) -> None:
    for i, n in enumerate(['C5', 'E5', 'G5']):
        note(i * .13, .12, hz(n), 'pulse', .15)
    for n, k in [('C6', 'pulse'), ('E5', 'sq'), ('G4', 'tri'), ('C3', 'tri')]:
        note(.39, .8, hz(n), k, .12, r=.3)


@jingle(1.0)
def levelup(b: Buf, note: Tone) -> None:
    for i, n in enumerate(['C5', 'E5', 'G5', 'C6', 'E6', 'G6']):
        note(i * .06, .06, hz(n), 'sq', .13)
    note(.36, .35, hz('C7'), 'sq', .12, dec=4)


@jingle(.7)
def coin(b: Buf, note: Tone) -> None:
    note(0, .07, hz('B5'), 'sq', .15)
    note(.07, .45, hz('E6'), 'sq', .15, dec=6)


@jingle(2.4)
def gameover(b: Buf, note: Tone) -> None:
    for i, n in enumerate(['C5', 'G4', 'E4', 'D#4', 'C4']):
        for k in ('sq', 'tri'):
            note(i * .3, 1.2 if i == 4 else .28, hz(n), k, .15, r=.2, vib=.01 * (i == 4))


@jingle(3.4)
def trombone(b: Buf, note: Tone) -> None:
    for i, n in enumerate(['D4', 'C#4', 'C4', 'B3']):
        note(i * .5, 1.4 if i == 3 else .42, hz(n), 'saw', .3, a=.05, r=.15, lp=.15, vib=.025 * (i == 3))


@jingle(1.0)
def buzzer(b: Buf, note: Tone) -> None:
    for f in (110, 116):
        note(0, .8, f, 'sq', .15, lp=.4)


@jingle(2.2)
def rimshot(b: Buf, note: Tone) -> None:
    note(0, .15, 220, 'sin', .5, dec=12, slide=-.4)
    note(.18, .2, 160, 'sin', .5, dec=10, slide=-.4)
    kick(b, .45)
    crash(b, .45)
    snare(b, .45, .2)


@jingle(3.6)
def drumroll(b: Buf, note: Tone) -> None:
    for i in range(45):
        snare(b, i * .045, .04 + .2 * i / 45)
    kick(b, 2.05, .8)
    crash(b, 2.05, .4)


@jingle(1.8)
def airhorn(b: Buf, note: Tone) -> None:
    for t, d in ((0, .15), (.22, .15), (.44, .9)):
        for m in (1, 1.008, 1.5, 2.003):
            note(t, d, hz('A#4') * m, 'saw', .1, a=.01, lp=.5)


@jingle(2.2)
def siren(b: Buf, note: Tone) -> None:
    for i in range(4):
        up = i % 2 == 0
        note(i * .5, .5, 600 if up else 900, 'sq', .15, a=.01, r=.01, lp=.2, slide=.58 if up else -.58)


@jingle(1.0)
def laser(b: Buf, note: Tone) -> None:
    for i in range(3):
        note(i * .28, .25, 1800, 'sq', .12, dec=8, slide=-3)


@jingle(2.6)
def explosion(b: Buf, note: Tone) -> None:
    note(0, 2.2, 0, 'noise', 1.2, a=.002, dec=2, lp=.04)
    note(0, 1.2, 70, 'sin', .6, dec=3, slide=-1)


@jingle(2.8)
def dundun(b: Buf, note: Tone) -> None:
    for t, d, n in ((0, .22, 'D3'), (.32, .22, 'F3'), (.64, 1.7, 'C#3')):
        for o in (0, -12):
            note(t, d, hz(n, o), 'saw', .25, a=.01, r=.3, lp=.15, vib=.01 * (d > 1))


@jingle(3.8)
def countdown(b: Buf, note: Tone) -> None:
    for i in range(3):
        note(i, .15, 440, 'sq', .15)
    note(3, .6, 880, 'sq', .15)


@jingle(.8)
def boing(b: Buf, note: Tone) -> None:
    note(0, .5, 150, 'tri', .4, dec=4, slide=1.2, vib=.12)


@jingle(3.6)
def crickets(b: Buf, note: Tone) -> None:
    for k in range(6):
        for p in range(3):
            note(k * .6 + p * .045, .025, 4300, 'sin', .12, a=.003, r=.01)


# ---------- voice lines (say + ffmpeg) ----------
STYLE = {  # boss = deep announcer with echo, cute = sped-up squeaky voice
    'boss': 'asetrate=22050*0.78,aresample=44100,aecho=0.8:0.5:90|180:0.35|0.2,',
    'cute': 'asetrate=22050*1.45,aresample=44100,',
    'plain': '',
}
VOICES = [
    ('fight', 'Daniel', 'boss', 'Fight!'),
    ('round1', 'Daniel', 'boss', 'Round one. Fight!'),
    ('round2', 'Daniel', 'boss', 'Round two. Fight!'),
    ('round3', 'Daniel', 'boss', 'Round three. Fight!'),
    ('round4', 'Daniel', 'boss', 'Round four. Fight!'),
    ('finish', 'Daniel', 'boss', 'Finish him!'),
    ('fatality', 'Daniel', 'boss', 'Fatality!'),
    ('segfault', 'Daniel', 'boss', 'Fatality. Segmentation fault.'),
    ('flawless', 'Daniel', 'boss', 'Flawless deployment!'),
    ('winner', 'Daniel', 'boss', 'Winner!'),
    ('highscore', 'Daniel', 'boss', 'New high score!'),
    ('merge', 'Ralph', 'boss', 'Merge conflict!'),
    ('prod', 'Ralph', 'boss', 'Production is down!'),
    ('force', 'Ralph', 'boss', 'Git push. Force!'),
    ('kernel', 'Ralph', 'boss', 'Kernel panic!'),
    ('legacy', 'Ralph', 'boss', 'Legacy code detected!'),
    ('friday', 'Ralph', 'boss', 'Deploy on Friday!'),
    ('shipit', 'Fred', 'plain', 'Ship it!'),
    ('mymachine', 'Fred', 'plain', 'It works on my machine.'),
    ('offon', 'Fred', 'plain', 'Have you tried turning it off and on again?'),
    ('yay', 'Junior', 'cute', 'Yaaaay!'),
    ('uhoh', 'Junior', 'cute', 'Uh oh!'),
    ('oops', 'Junior', 'cute', 'Oopsie!'),
    ('hugs', 'Junior', 'cute', 'Hugs for everyone!'),
    # Czech lines for local events, spoken by the Czech voice Zuzana
    ('coffee', 'Zuzana', 'plain', 'Pauza na kafe!'),
    ('applause', 'Zuzana', 'plain', 'Potlesk, prosím!'),
    ('worksforme', 'Zuzana', 'plain', 'U mě to funguje.'),
    ('whobrokeprod', 'Zuzana', 'plain', 'Kdo rozbil produkci?'),
    ('bomb', 'Zuzana', 'plain', 'Tak to je bomba!'),
    ('next', 'Zuzana', 'plain', 'Další, prosím!'),
]


def voice(name: str, v: str, style: str, text: str) -> None:
    out = os.path.join(ROOT, 'sfx', name + '.mp3')
    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, 'raw.wav')
        subprocess.run(['say', '-v', v, '--file-format=WAVE', '--data-format=LEI16@22050', '-o', raw, text], check=True)
        if os.path.getsize(raw) <= 4096:  # header only = say cannot reach the speech service (sandbox, missing voice)
            raise SystemExit(f'say produced no audio for "{text}" (voice {v}). Run the script in a regular terminal.')
        af = STYLE[style] + 'silenceremove=start_periods=1:start_threshold=-50dB,loudnorm=I=-14:TP=-1'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', af, '-ar', '44100', '-b:a', '128k', out], check=True)
    print('sfx/' + name + '.mp3')


if __name__ == '__main__':
    for name, make in LOOPS.items():
        random.seed(name)  # noise depends only on the name -> adding a sound does not change the others
        save(make(), f'loops/{name}.wav')
    for name, (sec, fn) in JINGLES.items():
        random.seed(name)
        save(sfx(sec, fn), f'sfx/{name}.wav')
    for args in VOICES:
        voice(*args)
