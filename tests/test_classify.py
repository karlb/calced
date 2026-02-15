#!/usr/bin/env python3
"""Test classify_line against shared test vectors."""

import json
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "python"))
from calced import classify_line

with open(os.path.join(here, "classify_vectors.json")) as f:
    vectors = json.load(f)

failures = 0
for i, v in enumerate(vectors):
    result = classify_line(v["text"], v["variables"])
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
