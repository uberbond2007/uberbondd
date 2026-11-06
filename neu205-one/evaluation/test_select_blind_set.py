"""Synthetic integrity tests for select_blind_set.py. No book text; never counted as accuracy evidence."""
import json, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import select_blind_set as sb

WORDS = ("alpha beta gamma delta epsilon zeta theta kappa lambda sigma omega tau rho phi chi psi "
         "orbit vector prism quartz cobalt ember fjord glacier harbor island jungle kelp lagoon meadow nebula").split()


def page_text(p):
    return " ".join(f"fact{p}x{i} {WORDS[(p + i) % len(WORDS)]}{p}" for i in range(12)) + "."


def make_pool(n_sup=640, n_uns=160):
    pages = {p: page_text(p) for p in range(1, 300)}
    drafts, reviews = [], []
    for i in range(n_sup):
        p = 61 + (i * 7) % 239
        q = f"Which item marks fact{p}x{i % 12} token{i} in section{i}?"
        if i % 5 == 0:
            q = f"Is the left lesion token{i} at fact{p}x{i % 12} contralateral in section{i}?"
        d = dict(draft_id=f"S{i:04d}", question=q, supported=True, task_type="recall", page=p, quote=f"fact{p}x{i % 12}")
        drafts.append(d); reviews.append(dict(draft_id=d["draft_id"], decision="accept"))
    for i in range(n_uns):
        q = f"What dose of zorblex{i} quux{i} applies for wibble{i} family{i}?"
        d = dict(draft_id=f"U{i:04d}", question=q, supported=False, task_type=f"absent_type{i % 6}",
                 anchors=[f"zorblex{i}"], rationale="not in book")
        drafts.append(d); reviews.append(dict(draft_id=d["draft_id"], decision="accept"))
    return pages, drafts, reviews


class Rules(unittest.TestCase):
    def setUp(self):
        self.pages, self.drafts, self.reviews = make_pool()

    def run_sel(self, drafts=None, reviews=None, exposed=(), prereg=b"prereg-v1", triage=()):
        return sb.select(drafts or self.drafts, reviews or self.reviews, list(exposed), self.pages, prereg, triage)

    def test_floor_targets_and_shape(self):
        seed, sel, reasons = self.run_sel()
        sup = [r for _, r in sel if r["supported"]]; uns = [r for _, r in sel if not r["supported"]]
        self.assertEqual((len(sup), len(uns)), (400, 100))
        self.assertTrue(all(r["page"] > 60 for r in sup))
        per_page = {}
        for r in sup:
            per_page[r["page"]] = per_page.get(r["page"], 0) + 1
        self.assertLessEqual(max(per_page.values()), sb.PAGE_CAP)
        self.assertGreaterEqual(sum(sb.safety_critical(r) for r in sup), int(0.2 * 400))
        self.assertEqual(len({r["task_type"] for r in uns}), 6)
        with self.assertRaises(sb.SelectionError):
            sb.select(self.drafts, self.reviews, [], self.pages, b"x", target_s=300)

    def test_deterministic_and_seed_bound(self):
        a = self.run_sel()[1]; b = self.run_sel()[1]; c = self.run_sel(prereg=b"prereg-v2")[1]
        self.assertEqual([d for d, _ in a], [d for d, _ in b])
        self.assertNotEqual([d for d, _ in a], [d for d, _ in c])

    def test_exclusion_rules(self):
        d = [dict(x) for x in self.drafts]
        d[1]["page"] = 30                                   # dev page
        d[2]["quote"] = "not on that page"                  # bad quote
        d[3]["figure_dependent"] = True
        d[641]["anchors"] = ["fact100x1"]                    # absence anchor present in source
        d[4]["question"] = d[6]["question"] + " "           # within-pool duplicate of 6
        rv = [dict(x) for x in self.reviews]
        rv[7]["decision"] = "reject"; rv[8]["decision"] = "hold"; rv.pop(9)
        exposed = [d[10]["question"].upper(), d[11]["question"].replace("Which", "What")]
        triage = [dict(draft_id=d[12]["draft_id"], exposed_match="substantial"),
                  dict(draft_id=d[13]["draft_id"], exposed_match="distinct")]
        _, sel, reasons = sb.select(d, rv, exposed, self.pages, b"p", triage)
        want = {1: "EXCL_DEV_OR_PAGE", 2: "EXCL_QUOTE", 3: "EXCL_FIGURE", 641: "EXCL_ABSENCE_HIT",
                7: "EXCL_REVIEW_REJECT", 8: "EXCL_REVIEW_HOLD", 9: "EXCL_REVIEW_MISSING",
                10: "EXCL_EXPOSED_EXACT", 11: "EXCL_EXPOSED_NEAR", 12: "EXCL_EXPOSED_SEMANTIC"}
        for i, code in want.items():
            self.assertIn(code, reasons[d[i]["draft_id"]], (i, reasons.get(d[i]["draft_id"])))
        self.assertNotIn(d[13]["draft_id"], [x for x, _ in sel if x in reasons])
        pair = {d[4]["draft_id"], d[6]["draft_id"]}
        self.assertEqual(len(pair & {x for x, _ in sel}), 1)
        self.assertTrue(any("EXCL_WITHIN_DUP" in reasons.get(x, []) for x in pair))
        sel_ids = {x for x, _ in sel}
        self.assertFalse(sel_ids & {d[i]["draft_id"] for i in want})

    def test_template_cap(self):
        extra = [dict(draft_id=f"T{i}", question=f"What is the exact dose for patient case {i} today?", supported=False,
                      task_type="missing_patient", anchors=[f"qqq{i}zz"], rationale="r") for i in range(8)]
        rv = self.reviews + [dict(draft_id=e["draft_id"], decision="accept") for e in extra]
        _, sel, reasons = sb.select(self.drafts + extra, rv, [], self.pages, b"p")
        kept = [x for x, _ in sel if x.startswith("T")]
        capped = [x for x in reasons if x.startswith("T") and reasons[x] in (["EXCL_TEMPLATE_CAP"], ["EXCL_WITHIN_DUP"])]
        self.assertLessEqual(len(kept), sb.TEMPLATE_CAP)
        self.assertGreaterEqual(len(capped), 8 - sb.TEMPLATE_CAP)

    def test_every_draft_accounted(self):
        _, sel, reasons = self.run_sel()
        ids = {sb.draft_id(r) for r in self.drafts}
        self.assertEqual(ids, {x for x, _ in sel} | set(reasons))
        self.assertFalse({x for x, _ in sel} & set(reasons))


class Cli(unittest.TestCase):
    def test_cli_exclusive_and_aggregate_only(self):
        pages, drafts, reviews = make_pool()
        d = tempfile.mkdtemp()
        def w(name, rows):
            p = os.path.join(d, name); open(p, "w").write("".join(json.dumps(r) + "\n" for r in rows)); return p
        args = ["--drafts", w("drafts.jsonl", drafts), "--reviews", w("rev.jsonl", reviews),
                "--exposed", w("exp.json", [{"question": "unrelated question about nothing"}]),
                "--pages", w("pages.jsonl", [{"pdf_page_1based": p, "text": t} for p, t in pages.items()]),
                "--preregistration", w("prereg.md", [{"x": 1}]),
                "--selected", os.path.join(d, "sel.jsonl"), "--ledger", os.path.join(d, "led.jsonl"),
                "--receipt", os.path.join(d, "rec.json")]
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(sb.main(args), 0)
        rec = open(os.path.join(d, "rec.json")).read()
        self.assertNotIn("Which item", rec); self.assertNotIn("zorblex", rec)
        self.assertTrue(json.loads(rec)["freeze_ready"])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sb.main(args), 2)


if __name__ == "__main__":
    unittest.main()
