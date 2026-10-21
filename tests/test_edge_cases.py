"""Edge case test suite for AssertVet."""

import unittest
from assertvet.diff_parser import DiffParser
from assertvet.scanner import AssertVetScanner
from assertvet.models import RuleID, Severity


BINARY_DIFF = """diff --git a/assets/logo.png b/assets/logo.png
index 123..456 100644
Binary files a/assets/logo.png and b/assets/logo.png differ
"""

PARAMETRIZE_EXPANSION_DIFF = """diff --git a/tests/test_math.py b/tests/test_math.py
--- a/tests/test_math.py
+++ b/tests/test_math.py
@@ -10,3 +10,4 @@
 @pytest.mark.parametrize("a,b,expected", [
     (1, 2, 3),
+    (2, 3, 5),
 ])
 def test_sum(a, b, expected):
     assert sum(a, b) == expected
"""

MULTIPLE_ASSERTS_SAME_HUNK = """diff --git a/tests/test_matrix.py b/tests/test_matrix.py
--- a/tests/test_matrix.py
+++ b/tests/test_matrix.py
@@ -5,4 +5,3 @@ def test_matrix():
     m = Matrix([[1, 2], [3, 4]])
-    assert m.rows == 2
-    assert m.cols == 2
+    assert m.shape == (2, 2)
"""

CHAINED_JEST_MATCHER = """diff --git a/src/api.test.ts b/src/api.test.ts
--- a/src/api.test.ts
+++ b/src/api.test.ts
@@ -10,2 +10,2 @@ it("returns user object", async () => {
-  expect(res.body).toEqual({ id: 1, name: "Alice" });
+  expect(res.body).toBeDefined();
 });
"""


class TestEdgeCases(unittest.TestCase):
    def setUp(self):
        self.scanner = AssertVetScanner()

    def test_binary_diff_ignored(self):
        result = self.scanner.scan_diff_text(BINARY_DIFF)
        self.assertTrue(result.is_clean)
        self.assertEqual(result.files_scanned, 1)
        self.assertEqual(result.test_files_analyzed, 0)

    def test_parametrize_expansion_is_clean(self):
        result = self.scanner.scan_diff_text(PARAMETRIZE_EXPANSION_DIFF)
        self.assertTrue(result.is_clean)

    def test_chained_jest_matcher_softening(self):
        result = self.scanner.scan_diff_text(CHAINED_JEST_MATCHER)
        self.assertFalse(result.is_clean)
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(result.violations[0].rule_id, RuleID.AV002)

    def test_empty_diff_returns_clean(self):
        result = self.scanner.scan_diff_text("")
        self.assertTrue(result.is_clean)
        self.assertEqual(result.files_scanned, 0)


if __name__ == "__main__":
    unittest.main()
