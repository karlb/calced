#!/usr/bin/env python3
"""Test evaluate_line against shared test vectors."""

import json
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "python"))
from calced import evaluate_line

with open(os.path.join(here, "evaluate_vectors.json")) as f:
    vectors = json.load(f)

failures = 0
for i, v in enumerate(vectors):
    result, _ = evaluate_line(v["text"], v["variables"])
    expected = v["expected"]
    if result != expected:
        print(f"FAIL vector {i}: {v['text']!r}")
        print(f"  expected: {expected}")
        print(f"  got:      {result}")
        failures += 1

if failures:
    print(f"\n{failures}/{len(vectors)} vectors failed")
    exit(1)
else:
    print(f"All {len(vectors)} vectors passed")
