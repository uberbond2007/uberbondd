import math, os, random, struct, sys, tempfile, unittest, wave
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench"))
import pdm_channel_map as pm

FS, N = 16000, 4000


def tone(f, amp):
    return [amp * math.sin(2 * math.pi * f * i / FS) for i in range(N)]


def noise(seed, amp=30):
    r = random.Random(seed); return [r.gauss(0, amp) for _ in range(N)]


def cap(s0, s1):
    return FS, [[int(v) for v in s0], [int(v) for v in s1]]


def scene(vib_slot, air_leak=0.02, contact_leak=0.05):
    mic = 1 - vib_slot
    def mk(vib_sig, mic_sig, seed):
        ch = [None, None]
        ch[vib_slot] = [a + b for a, b in zip(vib_sig, noise(seed))]
        ch[mic] = [a + b for a, b in zip(mic_sig, noise(seed + 1))]
        return cap(*ch)
    z = [0.0] * N
    silence = mk(z, z, 1)
    air = mk(tone(1000, 3000 * air_leak), tone(1000, 3000), 3)
    contact = mk(tone(200, 4000), tone(200, 4000 * contact_leak), 5)
    return silence, air, contact


class T(unittest.TestCase):
    def test_maps_both_orders(self):
        for v in (0, 1):
            r = pm.analyse(*scene(v))
            self.assertEqual((r["decision"], r["vib_slot"], r["mic_slot"]), ("MAPPED", v, 1 - v), r)

    def test_inconclusive_when_not_separable(self):
        r = pm.analyse(*scene(0, air_leak=1.0))
        self.assertEqual(r["decision"], "INCONCLUSIVE"); self.assertIsNone(r["vib_slot"])

    def test_dead_and_duplicated_slots(self):
        s, a, c = scene(0)
        dead = lambda x: (x[0], [x[1][0], [0] * N])
        self.assertEqual(pm.analyse(dead(s), dead(a), dead(c))["decision"], "INCONCLUSIVE")
        dup = lambda x: (x[0], [x[1][0], list(x[1][0])])
        r = pm.analyse(dup(s), dup(a), dup(c))
        self.assertTrue(any("identical" in m for m in r["reasons"]))

    def test_wav_roundtrip_cli(self):
        d = tempfile.mkdtemp(); paths = {}
        for name, (fs, ch) in zip(("silence", "air", "contact"), scene(1)):
            p = os.path.join(d, name + ".wav"); paths[name] = p
            with wave.open(p, "wb") as w:
                w.setnchannels(2); w.setsampwidth(2); w.setframerate(fs)
                w.writeframes(struct.pack("<%dh" % (2 * N), *[v for pair in zip(*ch) for v in pair]))
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = pm.main(["--silence", paths["silence"], "--air", paths["air"], "--contact", paths["contact"]])
        self.assertEqual(rc, 0); self.assertIn('"vib_slot": 1', out.getvalue())


if __name__ == "__main__":
    unittest.main()
