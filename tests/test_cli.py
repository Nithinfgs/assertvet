"""Unit tests for AssertVet CLI logic and options."""

import io
import json
import unittest
from unittest.mock import patch

from assertvet.cli import main, parse_args
from assertvet.models import RuleID, Severity


TAMPERED_DIFF = """diff --git a/tests/test_auth.py b/tests/test_auth.py
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -10,2 +10,1 @@ def test_auth():
-    assert user.is_authenticated is True
     assert user.id > 0
"""

CLEAN_DIFF = """diff --git a/tests/test_auth.py b/tests/test_auth.py
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -10,1 +10,2 @@ def test_auth():
     assert user.id > 0
+    assert user.role == "member"
"""


class TestCLI(unittest.TestCase):
    def test_parse_args_defaults(self):
        args = parse_args([])
        self.assertIsNone(args.target)
        self.assertFalse(args.staged)
        self.assertEqual(args.fail_on, "HIGH")
        self.assertFalse(args.strict)
        self.assertFalse(args.json)

    def test_stdin_tampered_diff_fails(self):
        with patch("sys.stdin", io.StringIO(TAMPERED_DIFF)):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                exit_code = main(["-", "--fail-on", "CRITICAL"])
                output = mock_stdout.getvalue()
                self.assertEqual(exit_code, 1)
                self.assertIn("DELETED_ASSERTION", output)
                self.assertIn("CRITICAL", output)

    def test_stdin_clean_diff_passes(self):
        with patch("sys.stdin", io.StringIO(CLEAN_DIFF)):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                exit_code = main(["-"])
                output = mock_stdout.getvalue()
                self.assertEqual(exit_code, 0)
                self.assertIn("All test assertions intact", output)

    def test_json_output(self):
        with patch("sys.stdin", io.StringIO(TAMPERED_DIFF)):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                exit_code = main(["-", "--json"])
                self.assertEqual(exit_code, 1)
                data = json.loads(mock_stdout.getvalue())
                self.assertFalse(data["is_clean"])
                self.assertEqual(data["summary"]["critical"], 1)
                self.assertEqual(data["violations"][0]["rule_id"], "AV001")

    def test_ignore_rule_flag(self):
        with patch("sys.stdin", io.StringIO(TAMPERED_DIFF)):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                # AV001 is the violation in TAMPERED_DIFF; ignoring it should pass
                exit_code = main(["-", "--ignore", "AV001"])
                self.assertEqual(exit_code, 0)

    def test_fail_on_threshold(self):
        with patch("sys.stdin", io.StringIO(TAMPERED_DIFF)):
            with patch("sys.stdout", new_callable=io.StringIO):
                # When threshold is set higher than violation (or if violation is CRITICAL and fail-on is CRITICAL)
                self.assertEqual(main(["-", "--fail-on", "CRITICAL"]), 1)


if __name__ == "__main__":
    unittest.main()
