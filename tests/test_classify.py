#!/usr/bin/env python3
"""Test classify_line against shared test vectors."""

import importlib.machinery
import importlib.util
import json
import os

# Import classify_line from the calced package
here = os.path.dirname(os.path.abspath(__file__))
calced_path = os.path.join(here, "..", "python", "calced.py")
loader = importlib.machinery.SourceFileLoader("calced", calced_path)
spec = importlib.util.spec_from_file_location("calced", calced_path, loader=loader,
                                                submodule_search_locations=[])
calced = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calced)

classify_line = calced.classify_line

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
