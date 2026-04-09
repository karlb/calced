# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Calced is a notepad calculator that evaluates math expressions in plain text. Two implementations share the same syntax and test suite:

- **Python CLI** (`python/calced.py`) — single file, stdlib only, uses `Decimal` for precision
- **JavaScript web app** (`web/index.html`) — single HTML file with embedded JS engine + big.js, no build step

When referring to "JS" or "JavaScript", that means the web version in `web/index.html`.

## Commands

```bash
make test              # Run all tests (Python + JS)
make test-py           # Python unit tests + .md integration tests
make test-js           # JavaScript tests (node web/test.mjs)
make test-property     # Property-based tests (requires hypothesis + pytest)

# Run a single Python test file
python3 -m unittest tests/test_evaluate.py

# Run a single .md integration test
python/calced.py tests/basic_arithmetic.md
git diff --exit-code -- tests/basic_arithmetic.md  # verify no changes

# Regenerate README (uses cogapp to run inline examples)
make README.md
```

## Architecture

Both implementations follow the same pipeline: **tokenize → classify line → parse → evaluate → format result → align output**.

- `python/calced.py` (~1500 lines): recursive descent parser, `Decimal` arithmetic, CLI with argparse (modes: single-run, watch, show, url, json, dry-run)
- `web/index.html` (~1400 lines): same engine between `// -- CALCED ENGINE BEGIN --` and `// END CALCED ENGINE` markers, big.js for precision, real-time evaluation, URL compression for sharing

Key concepts: variable assignments (`x = 5`), format/separator directives (`@format fixed 2`), SI prefixes, unit conversions, date arithmetic, percentages, totals.

## Test Structure

- **`tests/*.md`** — Integration tests. Each line with `# =>` has an expected result. The Python CLI processes these in-place; `git diff --exit-code` verifies nothing changed.
- **`tests/evaluate_vectors.json`** / **`tests/classify_vectors.json`** — Shared unit test vectors used by both Python and JS test runners.
- **`tests/test_*.py`** — Python unit tests (unittest framework). `test_cli.py` tests CLI flags via subprocess.
- **`web/test.mjs`** — JS test runner that extracts the engine from `index.html` and runs against the same vectors and `.md` files.

New tests should use `.md` fixture files or add vectors to the JSON files — these are run against both implementations. Only use Python unittest classes for Python-specific CLI behavior.

## Cross-Language Consistency

Features must work identically in both Python and JS. When implementing a change, check both implementations and run `make test` to verify both pass. The `.md` integration tests and JSON vectors are shared across both.
