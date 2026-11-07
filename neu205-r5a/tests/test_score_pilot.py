import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "experiment"))
import score_pilot as sp


def rows(cfg, n=20, hyp=None, strain=1, silence_words="", leak=None):
    r = [{"config": cfg, "kind": "utterance", "reference": f"open the door number {i}",
          "hypothesis": hyp(i) if hyp else f"Open the door, number {i}.", **({"leak_hypothesis": leak} if leak is not None else {})}
         for i in range(n)]
    r.append({"config": cfg, "kind": "silence", "reference": "", "hypothesis": silence_words, "duration_s": 120})
    r.append({"config": cfg, "kind": "comfort", "strain_0_10": strain})
    return r


class T(unittest.TestCase):
    def test_wer_strict_vs_lenient(self):
        self.assertEqual(sp.wer([("open the door 5", "Open the door five.")], sp.lenient_tokens), 0.0)
        self.assertGreater(sp.wer([("open the door 5", "Open the door five.")], sp.strict_tokens), 0.0)

    def test_pass_reject_and_scope(self):
        r = sp.score(rows("A_nearlip_1p5cm", leak="") + rows("A_phone_5cm", hyp=lambda i: "something else"))
        self.assertEqual(r["configs"]["A_nearlip_1p5cm"]["decision"], "CONFIG_PASSES")
        self.assertEqual(r["configs"]["A_nearlip_1p5cm"]["privacy_label"], "LOW_LEAKAGE_AT_1M")
        self.assertEqual(r["configs"]["A_phone_5cm"]["decision"], "CONFIG_REJECTED")
        self.assertEqual(r["configs"]["A_phone_5cm"]["scope"], "this configuration only")
        self.assertFalse(r["stop_all_vocal_trials"])

    def test_safety_stop_and_insufficient_and_silence(self):
        r = sp.score(rows("A_x", strain=5))
        self.assertEqual(r["configs"]["A_x"]["decision"], "STOP_SAFETY"); self.assertTrue(r["stop_all_vocal_trials"])
        self.assertEqual(sp.score(rows("A_y", n=5))["configs"]["A_y"]["decision"], "INSUFFICIENT_N")
        r = sp.score(rows("A_z", silence_words="hello there my friend"))
        self.assertIn("false words during silence", r["configs"]["A_z"]["reasons"])

    def test_command_mode(self):
        cmds = ["next slide", "go back", "read answer", "stop"]
        rs = [{"config": "B_cam", "kind": "command", "reference": cmds[i % 4], "hypothesis": cmds[i % 4].replace("e", "a")}
              for i in range(40)] + [{"config": "B_cam", "kind": "comfort", "strain_0_10": 0}]
        r = sp.score(rs, cmds)["configs"]["B_cam"]
        self.assertEqual(r["command_accuracy"], 1.0); self.assertEqual(r["decision"], "CONFIG_PASSES")
        with self.assertRaises(ValueError):
            sp.score(rs)


if __name__ == "__main__":
    unittest.main()
