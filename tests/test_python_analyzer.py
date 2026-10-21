"""Unit tests for Python test analyzer."""

import unittest
from assertvet.analyzers.python_analyzer import PythonAnalyzer
from assertvet.diff_parser import DiffParser
from assertvet.models import RuleID, Severity


class TestPythonAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = PythonAnalyzer()

    def _analyze_diff(self, diff_text: str):
        parser = DiffParser(diff_text)
        diffs = parser.parse()
        self.assertTrue(len(diffs) > 0)
        return self.analyzer.analyze(diffs[0])

    def test_detect_deleted_assertion(self):
        diff = """diff --git a/tests/test_calc.py b/tests/test_calc.py
--- a/tests/test_calc.py
+++ b/tests/test_calc.py
@@ -10,3 +10,2 @@ def test_add():
-    assert add(2, 3) == 5
     assert add(0, 0) == 0
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV001)
        self.assertEqual(violations[0].severity, Severity.CRITICAL)

    def test_detect_commented_assertion(self):
        diff = """diff --git a/tests/test_calc.py b/tests/test_calc.py
--- a/tests/test_calc.py
+++ b/tests/test_calc.py
@@ -10,2 +10,2 @@ def test_add():
-    assert add(2, 3) == 5
+    # FIXME: assert add(2, 3) == 5
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV001)

    def test_detect_softened_assertion(self):
        diff = """diff --git a/tests/test_api.py b/tests/test_api.py
--- a/tests/test_api.py
+++ b/tests/test_api.py
@@ -15,2 +15,2 @@ def test_get_user():
-    assert resp.status_code == 200
+    assert resp.status_code is not None
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV002)
        self.assertEqual(violations[0].severity, Severity.HIGH)

    def test_detect_skip_decorator(self):
        diff = """diff --git a/tests/test_db.py b/tests/test_db.py
--- a/tests/test_db.py
+++ b/tests/test_db.py
@@ -20,2 +20,3 @@
+@pytest.mark.skip(reason="Fails in CI")
 def test_connection():
     assert db.ping() is True
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV003)

    def test_detect_swallowed_exception(self):
        diff = """diff --git a/tests/test_worker.py b/tests/test_worker.py
--- a/tests/test_worker.py
+++ b/tests/test_worker.py
@@ -30,2 +30,6 @@ def test_queue():
+    try:
+        worker.run_job()
+    except Exception:
+        pass
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV004)

    def test_detect_empty_test(self):
        diff = """diff --git a/tests/test_dummy.py b/tests/test_dummy.py
--- a/tests/test_dummy.py
+++ b/tests/test_dummy.py
@@ -40,0 +41,3 @@
+def test_new_feature():
+    pass
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV005)

    def test_clean_legitimate_test_update(self):
        # Adding a stronger assertion or refactoring should not flag
        diff = """diff --git a/tests/test_user.py b/tests/test_user.py
--- a/tests/test_user.py
+++ b/tests/test_user.py
@@ -10,2 +10,3 @@ def test_create():
     user = create_user("bob")
+    assert user.name == "bob"
     assert user.id > 0
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
