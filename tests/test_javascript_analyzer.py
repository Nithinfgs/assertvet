"""Unit tests for JavaScript/TypeScript test analyzer."""

import unittest
from assertvet.analyzers.javascript_analyzer import JavaScriptAnalyzer
from assertvet.diff_parser import DiffParser
from assertvet.models import RuleID, Severity


class TestJavaScriptAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = JavaScriptAnalyzer()

    def _analyze_diff(self, diff_text: str):
        parser = DiffParser(diff_text)
        diffs = parser.parse()
        self.assertTrue(len(diffs) > 0)
        return self.analyzer.analyze(diffs[0])

    def test_detect_deleted_expect(self):
        diff = """diff --git a/src/auth.test.ts b/src/auth.test.ts
--- a/src/auth.test.ts
+++ b/src/auth.test.ts
@@ -10,3 +10,2 @@ it("validates token", () => {
-  expect(token.isValid).toBe(true);
   expect(token.exp).toBeGreaterThan(0);
 });
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV001)

    def test_detect_commented_expect(self):
        diff = """diff --git a/src/auth.test.ts b/src/auth.test.ts
--- a/src/auth.test.ts
+++ b/src/auth.test.ts
@@ -10,2 +10,2 @@ it("validates token", () => {
-  expect(token.isValid).toBe(true);
+  // expect(token.isValid).toBe(true);
 });
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV001)

    def test_detect_softened_expect(self):
        diff = """diff --git a/src/user.test.ts b/src/user.test.ts
--- a/src/user.test.ts
+++ b/src/user.test.ts
@@ -15,2 +15,2 @@ it("loads profile", () => {
-  expect(profile.role).toBe("admin");
+  expect(profile.role).toBeDefined();
 });
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV002)

    def test_detect_skipped_test(self):
        diff = """diff --git a/src/order.test.ts b/src/order.test.ts
--- a/src/order.test.ts
+++ b/src/order.test.ts
@@ -20,1 +20,1 @@
-it("processes payment", () => {
+it.skip("processes payment", () => {
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV003)

    def test_detect_empty_test_stub(self):
        diff = """diff --git a/src/checkout.test.ts b/src/checkout.test.ts
--- a/src/checkout.test.ts
+++ b/src/checkout.test.ts
@@ -30,0 +30,2 @@
+it("handles refunds", () => {});
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].rule_id, RuleID.AV005)

    def test_clean_legitimate_js_test(self):
        diff = """diff --git a/src/sum.test.ts b/src/sum.test.ts
--- a/src/sum.test.ts
+++ b/src/sum.test.ts
@@ -5,1 +5,2 @@ it("adds numbers", () => {
   expect(sum(1, 2)).toBe(3);
+  expect(sum(-1, 1)).toBe(0);
 });
"""
        violations = self._analyze_diff(diff)
        self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
