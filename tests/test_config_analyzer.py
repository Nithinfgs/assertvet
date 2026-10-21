"""Unit tests for config and evasion analyzer."""

import unittest
from assertvet.analyzers.config_analyzer import ConfigAnalyzer
from assertvet.diff_parser import DiffParser
from assertvet.models import RuleID, Severity


class TestConfigAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = ConfigAnalyzer()

    def test_detect_package_json_bypass(self):
        diff = """diff --git a/package.json b/package.json
--- a/package.json
+++ b/package.json
@@ -10,1 +10,1 @@
-    "test": "vitest run"
+    "test": "vitest run || true"
"""
        parser = DiffParser(diff)
        diffs = parser.parse()
        violations = self.analyzer.analyze(diffs[0])

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV006)
        self.assertEqual(violations[0].severity, Severity.CRITICAL)

    def test_detect_github_workflow_continue_on_error(self):
        diff = """diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -25,2 +25,3 @@
       - name: Run Tests
+        continue-on-error: true
         run: pytest
"""
        parser = DiffParser(diff)
        diffs = parser.parse()
        violations = self.analyzer.analyze(diffs[0])

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV006)

    def test_detect_deleted_test_file(self):
        diff = """diff --git a/tests/test_payments.py b/tests/test_payments.py
deleted file mode 100644
--- a/tests/test_payments.py
+++ /dev/null
@@ -1,10 +0,0 @@
-def test_charge():
-    assert True
"""
        parser = DiffParser(diff)
        diffs = parser.parse()
        violations = self.analyzer.analyze(diffs[0])

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV007)
        self.assertEqual(violations[0].severity, Severity.MEDIUM)


if __name__ == "__main__":
    unittest.main()
