import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_parity_report as g

PY = "        status='NONE' if not passages or best<.25 else 'WEAK' if best<.45 else 'OK'\n"
JAVA = ('    public static final double OK_COVERAGE = 0.50, WEAK_COVERAGE = 0.20;\n'
        '        String status = out.isEmpty() || best < WEAK_COVERAGE ? "NONE" : best < OK_COVERAGE ? "WEAK" : "OK";\n')


class T(unittest.TestCase):
    def test_parses_both_and_finds_two_bands(self):
        c, n = g.companion_thresholds(PY), g.native_thresholds(JAVA)
        self.assertEqual((c, n), ((0.25, 0.45), (0.20, 0.50)))
        r = g.report(c, n)
        self.assertFalse(r["identical"])
        self.assertEqual([b["band"] for b in r["divergent_bands"]], [[0.20, 0.25], [0.45, 0.50]])
        row = {x["coverage"]: x for x in r["boundary_table"]}
        self.assertEqual((row[0.22]["companion"], row[0.22]["native"]), ("NONE", "WEAK"))
        self.assertEqual((row[0.47]["companion"], row[0.47]["native"]), ("OK", "WEAK"))
        self.assertEqual(row[0.19]["companion"], row[0.19]["native"])

    def test_identical_and_shape_change(self):
        self.assertTrue(g.report((0.2, 0.5), (0.2, 0.5))["identical"])
        self.assertIsNone(g.native_thresholds("OK_COVERAGE = 0.5, WEAK_COVERAGE = 0.2;"))
        self.assertIsNone(g.companion_thresholds("status = gate(best)"))


if __name__ == "__main__":
    unittest.main()
