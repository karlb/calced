#!/usr/bin/env python3
"""Test evaluate_line against shared test vectors."""

import datetime
import json
import os
import sys
import unittest

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "python"))
from calced import evaluate_line, classify_line, process_json
from decimal import Decimal

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
        content = "2025-01-15 + 3 days\n100\n200\ntotal"
        output = process_json(content)
        # total should be 300 (skipping the date)
        self.assertEqual(output[-1]["result"], 300.0)

    # --- Nesting and combination edge cases ---

    def test_nested_functions(self):
        """Nested function calls should evaluate correctly."""
        r, _ = evaluate_line("sqrt(abs(-16))", {})
        self.assertEqual(r, 4)
        r, _ = evaluate_line("max(sqrt(4), sqrt(9))", {})
        self.assertEqual(r, 3)

    def test_function_with_conversion(self):
        """Function result used in unit conversion."""
        r, _ = evaluate_line("sqrt(4) km in miles", {})
        self.assertIsNotNone(r)
        self.assertAlmostEqual(float(r), 1.2427, places=3)

    def test_percentage_in_parens_then_multiply(self):
        """(val + pct%) * factor should work."""
        r, _ = evaluate_line("(200 + 10%) * 2", {})
        self.assertEqual(r, 440)

    def test_chained_percentages(self):
        """Multiple percentage operations chain correctly."""
        r, _ = evaluate_line("200 + 10% + 5%", {})
        self.assertEqual(r, 231)

    def test_percentage_plus_then_addition(self):
        """Percentage then plain addition: (200*1.1) + 50."""
        r, _ = evaluate_line("200 + 10% + 50", {})
        self.assertEqual(r, 270)

    def test_si_prefix_in_expression(self):
        r, _ = evaluate_line("1k + 500", {})
        self.assertEqual(r, 1500)

    def test_label_with_operator(self):
        """Text labels around operators should be ignored."""
        r, _ = evaluate_line("price 10 + tax 5", {})
        self.assertEqual(r, 15)

    def test_label_with_conversion(self):
        """Text label before unit conversion."""
        r, _ = evaluate_line("distance 100 km in miles", {})
        self.assertIsNotNone(r)
        self.assertAlmostEqual(float(r), 62.137, places=2)

    def test_variable_with_conversion(self):
        """Variable used as value in unit conversion."""
        r, _ = evaluate_line("x km in miles", {"x": Decimal(10)})
        self.assertIsNotNone(r)
        self.assertAlmostEqual(float(r), 6.214, places=2)

    def test_date_with_expression_days(self):
        """Date + (expression) days."""
        r, _ = evaluate_line("2025-01-01 + (2 * 7) days", {})
        self.assertEqual(r, datetime.date(2025, 1, 15))

    def test_negative_date_difference(self):
        """Earlier - later gives negative days."""
        r, _ = evaluate_line("2025-01-01 - 2025-03-01", {})
        self.assertEqual(r, -59)

    def test_leap_year_plus_one_year(self):
        """Feb 29 + 1 year clamps to Feb 28."""
        r, _ = evaluate_line("2024-02-29 + 1 year", {})
        self.assertEqual(r, datetime.date(2025, 2, 28))

    def test_leap_year_plus_four_years(self):
        """Feb 29 + 4 years preserves Feb 29."""
        r, _ = evaluate_line("2024-02-29 + 4 years", {})
        self.assertEqual(r, datetime.date(2028, 2, 29))

    def test_variable_chain(self):
        """Variables referencing other variables."""
        _, v = evaluate_line("a = 10", {})
        _, v = evaluate_line("b = a + 5", v)
        _, v = evaluate_line("c = b * 2", v)
        r, _ = evaluate_line("a + b + c", v)
        self.assertEqual(r, 55)

    def test_total_with_mixed_expressions(self):
        """Total sums labeled lines, percentages, and skips dates."""
        content = "# Budget\n2025-01-01 + 3 days\n100\n200\n50% of 400\ntotal"
        output = process_json(content)
        self.assertEqual(output[-1]["result"], 500.0)

    def test_multiline_var_then_convert(self):
        """Variable defined on one line, used in conversion on next."""
        content = "x = 100\nx km in miles"
        output = process_json(content)
        self.assertIsNotNone(output[1]["result"])
        self.assertAlmostEqual(output[1]["result"], 62.137, places=2)

    def test_assign_conversion_then_use(self):
        """Variable assigned from conversion, used in plain arithmetic."""
        content = "d = 5 km in miles\nd * 2"
        output = process_json(content)
        self.assertIsNotNone(output[1]["result"])
        self.assertAlmostEqual(output[1]["result"], 6.214, places=2)

    # --- Known limitations: document current behavior ---

    def test_leading_paren_label_returns_none(self):
        """(label) before expression currently returns None.

        Known limitation: _build_math keeps LPAREN/RPAREN but skips the WORD
        inside, creating empty parens () that the parser can't handle.
        """
        r, _ = evaluate_line("(just) 100", {})
        self.assertIsNone(r)

    def test_pct_then_multiply_returns_none(self):
        """200 + 10% * 2 currently returns None.

        The expression is ambiguous: standard precedence gives 200.2
        (10% = 0.1, * 2 = 0.2, + 200), while treating +10% as one
        operation gives 440. Returning None avoids a surprising result.
        Workaround: (200 + 10%) * 2.
        """
        r, _ = evaluate_line("200 + 10% * 2", {})
        self.assertIsNone(r)

    def test_compound_date_durations_fall_through(self):
        """2025-01-01 + 1 week + 3 days falls through to plain arithmetic.

        Known limitation: the date pattern matcher only supports a single
        duration unit. Compound durations like '1 week + 3 days' fail
        pattern matching and fall through to arithmetic (1 + 3 = 4).
        """
        r, _ = evaluate_line("2025-01-01 + 1 week + 3 days", {})
        # Currently evaluates as 1 + 3 = 4 (plain arithmetic fallthrough)
        self.assertEqual(r, 4)


if __name__ == "__main__":
    unittest.main()
