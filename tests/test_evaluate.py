#!/usr/bin/env python3
"""Test evaluate_line against shared test vectors."""

import datetime
import json
import os
import sys
import unittest

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "python"))
from calced import evaluate_line

with open(os.path.join(here, "evaluate_vectors.json")) as f:
    vectors = json.load(f)


class TestEvaluate(unittest.TestCase):
    def test_vectors(self):
        for i, v in enumerate(vectors):
            with self.subTest(i=i, text=v["text"]):
                result, _ = evaluate_line(v["text"], v["variables"])
                expected = v["expected"]
                if isinstance(expected, str):
                    # Date result: compare ISO string
                    self.assertEqual(result.isoformat(), expected)
                else:
                    self.assertEqual(result, expected)

    def test_today(self):
        result, _ = evaluate_line("today + 0 days", {})
        self.assertEqual(result, datetime.date.today())

    def test_date_variable(self):
        _, v = evaluate_line("d = 2025-01-15 + 2 weeks", {})
        result, _ = evaluate_line("d - 2025-01-15", v)
        self.assertEqual(result, 14)

    def test_dates_skip_total(self):
        """Dates in accumulator should not break total."""
        from calced import process_json
        content = "2025-01-15 + 3 days\n100\n200\ntotal"
        output = process_json(content)
        # total should be 300 (skipping the date)
        self.assertEqual(output[-1]["result"], 300.0)


if __name__ == "__main__":
    unittest.main()
