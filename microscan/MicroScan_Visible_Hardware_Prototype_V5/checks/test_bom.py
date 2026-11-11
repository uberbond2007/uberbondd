"""Cost arithmetic and honesty checks on BOM.csv."""
import csv
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = list(csv.DictReader((ROOT / 'BOM.csv').open(encoding='utf-8')))
BUDGET = Decimal('1500')


def known(rows):
    return [r for r in rows if r['Line_EGP'] != 'UNKNOWN']


class Bom(unittest.TestCase):
    def test_every_line_total_equals_qty_times_unit(self):
        for r in known(ROWS):
            self.assertEqual(Decimal(r['Qty']) * Decimal(r['Unit_EGP']), Decimal(r['Line_EGP']), r['Part'])

    def test_known_subtotal(self):
        total = sum(Decimal(r['Line_EGP']) for r in known(ROWS))
        self.assertEqual(total, Decimal('653.02'))

    def test_unknowns_are_not_given_numbers(self):
        unknown = [r for r in ROWS if r['Line_EGP'] == 'UNKNOWN']
        self.assertEqual(len(unknown), 4)
        for r in unknown:
            self.assertEqual(r['Unit_EGP'], 'UNKNOWN')
            self.assertIn(r['Price_class'], ('NO QUOTE', 'NO LISTING FOUND'))

    def test_every_priced_line_has_a_source_url_and_date(self):
        for r in known(ROWS):
            if Decimal(r['Line_EGP']) > 0:
                self.assertTrue(r['Source'].startswith('https://'), r['Part'])
                self.assertEqual(r['Checked'], '2026-11-11')

    def test_budget_statement_is_conditional(self):
        total = sum(Decimal(r['Line_EGP']) for r in known(ROWS))
        headroom = BUDGET - total
        self.assertEqual(headroom, Decimal('846.98'))
        text = (ROOT / 'docs' / 'SOURCING_AND_DFM.md').read_text()
        self.assertIn('653.02', text)
        self.assertIn('846.98', text)
        self.assertIn('NOT PROVEN', text)

    def test_no_purchase_claims(self):
        for name in ('README.md', 'PHYSICAL_BLOCKERS.md', 'docs/SOURCING_AND_DFM.md'):
            text = (ROOT / name).read_text().lower()
            for phrase in ('order placed', 'purchased on', 'has been ordered', 'we bought'):
                self.assertNotIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
