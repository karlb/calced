#!/usr/bin/env python3
"""Test classify_line against shared test vectors."""

import json
import os
import sys
import unittest

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "python"))
from calced import classify_line

with open(os.path.join(here, "classify_vectors.json")) as f:
    vectors = json.load(f)


class TestClassify(unittest.TestCase):
    def test_vectors(self):
        for i, v in enumerate(vectors):
            with self.subTest(i=i, text=v["text"]):
                result = classify_line(v["text"], v["variables"])
                self.assertEqual(result, v["expected"])


if __name__ == "__main__":
    unittest.main()
