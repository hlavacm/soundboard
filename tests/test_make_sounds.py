import json
import os
import random
import sys
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_sounds as m


class Synth(unittest.TestCase):
    def test_hz(self) -> None:
        self.assertEqual(m.hz('A4'), 440)
        self.assertAlmostEqual(m.hz('A5'), 880)
        self.assertAlmostEqual(m.hz('A4', 12), 880)
        self.assertAlmostEqual(m.hz('C#4'), 277.18, places=2)

    def test_loop_tone_wraps_to_start(self) -> None:
        buf = [0.0] * 1000
        m.tone(buf, 900 / m.SR, 200 / m.SR, 440, loop=True)
        self.assertNotEqual(buf[50], 0)  # the note tail wrapped to the start -> seamless loop

    def test_one_shot_tone_does_not_wrap(self) -> None:
        buf = [0.0] * 1000
        m.tone(buf, 900 / m.SR, 200 / m.SR, 440)
        self.assertEqual(buf[:900], [0.0] * 900)

    def test_loop_length_is_exact_beats(self) -> None:
        buf, beat, _ = m.new_loop(120, 8)
        self.assertEqual(beat, .5)
        self.assertEqual(len(buf), 4 * m.SR)

    def test_jingles_are_normalized(self) -> None:
        random.seed(1)
        for name, (seconds, fn) in m.JINGLES.items():
            with self.subTest(name):
                b = m.sfx(seconds, fn)
                self.assertEqual(len(b), int(seconds * m.SR))
                self.assertAlmostEqual(max(map(abs, b)), .7)


class Catalog(unittest.TestCase):
    def test_every_generated_sound_is_in_sounds_json(self) -> None:
        with open(os.path.join(ROOT, 'sounds.json'), encoding='utf-8') as f:
            data = json.load(f)
        listed = {s['file'] for s in data['loops'] + data['sfx']}
        generated = ({f'sounds/loops/{n}.wav' for n in m.LOOPS}
                     | {f'sounds/sfx/{n}.wav' for n in m.JINGLES}
                     | {f'sounds/sfx/{v[0]}.mp3' for v in m.VOICES})
        self.assertEqual(generated - listed, set())

    def test_voices_are_unique_and_use_known_styles(self) -> None:
        names = [v[0] for v in m.VOICES]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(v[2] in m.STYLE for v in m.VOICES))


if __name__ == '__main__':
    unittest.main()
