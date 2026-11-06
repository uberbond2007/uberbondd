import json, os, re, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from grounding_gate import REFUSAL, gate, gated_verdict, summarise
import eval_freeze as ef

# Synthetic, non-book fixtures (paraphrased general anatomy; no textbook text).
EV_ICA = ["The internal carotid artery ends by dividing into the anterior cerebral artery and the larger middle cerebral artery."]


class Gate(unittest.TestCase):
    def test_extrinsic_structure_is_abstained(self):
        g = gate("Which is the larger terminal branch of the internal carotid artery?", "The middle meningeal artery.", EV_ICA)
        self.assertEqual(g["decision"], "ABSTAIN")
        self.assertIn("mening", " ".join(g["unsupported"]))

    def test_grounded_answer_passes(self):
        g = gate("Which is the larger terminal branch of the internal carotid artery?", "The middle cerebral artery.", EV_ICA)
        self.assertEqual(g["decision"], "PASS", g)

    def test_known_limitation_inversion_passes(self):
        # H1 cannot detect a polarity inversion built from evidence terms. This test pins the limitation so nobody
        # reports H1 as a fix for the Parkinson's-class error.
        ev = ["Phenothiazines block dopamine receptors and can produce drug-induced parkinsonism; levodopa replaces dopamine."]
        g = gate("Which drugs treat Parkinson disease?", "Phenothiazines, which block dopamine receptors.", ev)
        self.assertEqual(g["decision"], "PASS")

    def test_refusal_untouched(self):
        self.assertEqual(gate("q", "NOT_IN_BOOK", EV_ICA)["decision"], "ALREADY_REFUSED")

    def test_refusal_pattern_matches_harness(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "qwen_eval.py"), encoding="utf-8").read()
        m = re.search(r'REFUSAL = re\.compile\((r".*?"), re\.I\)', src)
        self.assertEqual(eval(m.group(1)), REFUSAL.pattern)

    def test_lenient_variant(self):
        ev = ["The recurrent laryngeal nerve runs close to the inferior thyroid artery near the gland."]
        ans = "The recurrent laryngeal nerve, beside the gland, near the lobe."
        q = "Which nerve is at risk with the inferior thyroid artery?"
        self.assertEqual(gate(q, ans, ev, "strict")["decision"], "ABSTAIN")
        self.assertEqual(gate(q, ans, ev, "lenient")["decision"], "PASS")

    def test_gating_never_upgrades(self):
        self.assertEqual(gated_verdict("supported", "wrong", "ABSTAIN"), "refused")
        self.assertEqual(gated_verdict("supported", "correct", "ABSTAIN"), "refused")
        self.assertEqual(gated_verdict("unsupported", "false_answer", "ABSTAIN"), "correct_refusal")
        self.assertEqual(gated_verdict("supported", "wrong", "PASS"), "wrong")
        s = summarise([{"kind": "supported", "graded": "wrong", "gated": "refused"},
                       {"kind": "supported", "graded": "correct", "gated": "correct"}])
        self.assertEqual(s["wrong_rate"], 0.0); self.assertEqual(s["gate_flips"]["wrong->refused"], 1)


class Freeze(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = os.path.join(self.d, "t2.json"); json.dump([{"id": "x1"}, {"id": "x2"}], open(self.p, "w"))
        self.s = os.path.join(self.d, "seal.json")
        self.c = [{"name": "control", "config_sha": "f89d3e2", "model_sha256": "aa", "hypothesis": "control"},
                  {"name": "h1", "config_sha": "abc1234", "model_sha256": "aa", "hypothesis": "H1"}]
        ef.seal([self.p], self.c, self.s)

    def test_happy_path_and_one_run(self):
        ef.admit(self.s, [self.p], "h1", "abc1234", "aa")
        with self.assertRaises(ef.FreezeError):
            ef.admit(self.s, [self.p], "h1", "abc1234", "aa")
        out = os.path.join(self.d, "run.json"); json.dump({"rows": []}, open(out, "w"))
        ef.record(self.s, "h1", out)
        self.assertEqual(ef.check_grade(self.s, out)["candidate"], "h1")
        json.dump({"rows": [1]}, open(out, "w"))
        with self.assertRaises(ef.FreezeError):
            ef.check_grade(self.s, out)

    def test_unregistered_or_changed_config_refused(self):
        with self.assertRaises(ef.FreezeError):
            ef.admit(self.s, [self.p], "h9", "abc1234", "aa")
        with self.assertRaises(ef.FreezeError):
            ef.admit(self.s, [self.p], "h1", "tuned999", "aa")

    def test_probe_edit_refused(self):
        json.dump([{"id": "x1"}], open(self.p, "w"))
        with self.assertRaises(ef.FreezeError):
            ef.admit(self.s, [self.p], "h1", "abc1234", "aa")

    def test_seal_tamper_and_reseal_refused(self):
        with self.assertRaises(ef.FreezeError):
            ef.seal([self.p], self.c, self.s)
        doc = json.load(open(self.s)); doc["candidates"].append({"name": "late", "config_sha": "x", "model_sha256": "y"})
        json.dump(doc, open(self.s, "w"))
        with self.assertRaises(ef.FreezeError):
            ef.admit(self.s, [self.p], "late", "x", "y")

    def test_record_requires_admit(self):
        out = os.path.join(self.d, "r.json"); json.dump({}, open(out, "w"))
        with self.assertRaises(ef.FreezeError):
            ef.record(self.s, "control", out)


if __name__ == "__main__":
    unittest.main()
