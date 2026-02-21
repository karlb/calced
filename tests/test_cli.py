#!/usr/bin/env python3
"""Test CLI flags by invoking calced.py as a subprocess."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

here = os.path.dirname(os.path.abspath(__file__))
calced = os.path.join(here, "..", "python", "calced.py")


def run(args, stdin=None):
    """Run calced.py with the given arguments."""
    return subprocess.run(
        [sys.executable, calced] + args,
        capture_output=True,
        text=True,
        input=stdin,
        env={**os.environ, "NO_COLOR": "1"},
    )


def make_tmp(content):
    """Write content to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


class TestShow(unittest.TestCase):
    def test_prints_to_stdout(self):
        tmp = make_tmp("1 + 1\n")
        r = run(["--show", tmp])
        os.unlink(tmp)
        self.assertIn("# => 2", r.stdout)

    def test_does_not_modify_file(self):
        tmp = make_tmp("1 + 1\n")
        run(["--show", tmp])
        with open(tmp) as f:
            self.assertEqual(f.read(), "1 + 1\n")
        os.unlink(tmp)

    def test_multiple_lines(self):
        tmp = make_tmp("x = 10\nx * 2\n")
        r = run(["--show", tmp])
        os.unlink(tmp)
        self.assertIn("# => 10", r.stdout)
        self.assertIn("# => 20", r.stdout)


class TestJson(unittest.TestCase):
    def test_valid_json_output(self):
        r = run(["--json", os.path.join(here, "basic_arithmetic.md")])
        self.assertEqual(r.returncode, 0)
        data = json.loads(r.stdout)
        self.assertIsInstance(data, list)
        results = [d["result"] for d in data if d["result"] is not None]
        self.assertTrue(len(results) > 0)

    def test_from_stdin(self):
        r = run(["-", "--json"], stdin="2 + 3\n")
        data = json.loads(r.stdout)
        self.assertEqual(data[0]["result"], 5)


class TestDryRun(unittest.TestCase):
    def test_exits_1_when_changes_needed(self):
        tmp = make_tmp("5 * 5\n")
        r = run(["--dry-run", tmp])
        os.unlink(tmp)
        self.assertEqual(r.returncode, 1)
        self.assertIn("# => 25", r.stdout)

    def test_does_not_modify_file(self):
        tmp = make_tmp("5 * 5\n")
        run(["--dry-run", tmp])
        with open(tmp) as f:
            self.assertEqual(f.read(), "5 * 5\n")
        os.unlink(tmp)

    def test_exits_0_when_up_to_date(self):
        tmp = make_tmp("5 * 5                                   # => 25\n")
        r = run(["--dry-run", tmp])
        os.unlink(tmp)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")


class TestUrl(unittest.TestCase):
    def test_prints_url(self):
        r = run(["--url", os.path.join(here, "basic_arithmetic.md")])
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stdout.strip().startswith("https://calced.karl.berlin/"))


class TestStdin(unittest.TestCase):
    def test_defaults_to_show_mode(self):
        r = run(["-"], stdin="3 + 4\n")
        self.assertIn("# => 7", r.stdout)


class TestNoColor(unittest.TestCase):
    def test_no_ansi_codes(self):
        tmp = make_tmp("1 + 1\n")
        r = run(["--show", "--no-color", tmp])
        os.unlink(tmp)
        self.assertNotIn("\033[", r.stdout)
        self.assertIn("# => 2", r.stdout)


class TestMutualExclusion(unittest.TestCase):
    def test_show_and_json(self):
        r = run(["--show", "--json", os.path.join(here, "basic_arithmetic.md")])
        self.assertNotEqual(r.returncode, 0)

    def test_show_and_dry_run(self):
        r = run(["--show", "--dry-run", os.path.join(here, "basic_arithmetic.md")])
        self.assertNotEqual(r.returncode, 0)

    def test_watch_and_json(self):
        r = run(["--watch", "--json", os.path.join(here, "basic_arithmetic.md")])
        self.assertNotEqual(r.returncode, 0)

    def test_watch_and_url(self):
        r = run(["--watch", "--url", os.path.join(here, "basic_arithmetic.md")])
        self.assertNotEqual(r.returncode, 0)

    def test_watch_and_dry_run(self):
        r = run(["--watch", "--dry-run", os.path.join(here, "basic_arithmetic.md")])
        self.assertNotEqual(r.returncode, 0)


class TestFileNotFound(unittest.TestCase):
    def test_exits_1(self):
        r = run(["/nonexistent/file.txt"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stderr)


class TestInPlace(unittest.TestCase):
    def test_writes_result(self):
        tmp = make_tmp("9 / 3\n")
        r = run([tmp])
        self.assertEqual(r.returncode, 0)
        with open(tmp) as f:
            self.assertIn("# => 3", f.read())
        os.unlink(tmp)

    def test_idempotent(self):
        tmp = make_tmp("2 + 2\n")
        run([tmp])
        with open(tmp) as f:
            first = f.read()
        run([tmp])
        with open(tmp) as f:
            self.assertEqual(f.read(), first)
        os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
