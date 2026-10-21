"""Unit tests for unified git diff parser."""

import unittest
from assertvet.diff_parser import (
    DiffParser,
    is_config_file,
    is_javascript_test_file,
    is_python_test_file,
)


SAMPLE_DIFF = """diff --git a/tests/test_auth.py b/tests/test_auth.py
index 1234567..89abcdef 100644
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -10,7 +10,6 @@ def test_login():
     user = authenticate("alice", "secret")
-    assert user.is_authenticated is True
     assert user.username == "alice"
"""

SAMPLE_NEW_FILE_DIFF = """diff --git a/src/app.test.ts b/src/app.test.ts
new file mode 100644
--- /dev/null
+++ b/src/app.test.ts
@@ -0,0 +1,5 @@
+it("works", () => {
+  expect(1 + 1).toBe(2);
+});
"""

SAMPLE_DELETED_FILE_DIFF = """diff --git a/tests/test_legacy.py b/tests/test_legacy.py
deleted file mode 100644
--- a/tests/test_legacy.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def test_old():
-    assert True
"""


class TestDiffParser(unittest.TestCase):
    def test_file_type_detection(self):
        self.assertTrue(is_python_test_file("tests/test_auth.py"))
        self.assertTrue(is_python_test_file("test_user.py"))
        self.assertTrue(is_python_test_file("src/foo_test.py"))
        self.assertFalse(is_python_test_file("src/auth.py"))

        self.assertTrue(is_javascript_test_file("src/button.test.tsx"))
        self.assertTrue(is_javascript_test_file("tests/auth.spec.js"))
        self.assertTrue(is_javascript_test_file("__tests__/engine.ts"))
        self.assertFalse(is_javascript_test_file("src/button.tsx"))

        self.assertTrue(is_config_file("package.json"))
        self.assertTrue(is_config_file(".github/workflows/ci.yml"))
        self.assertTrue(is_config_file("Makefile"))
        self.assertFalse(is_config_file("src/index.js"))

    def test_parse_standard_diff(self):
        parser = DiffParser(SAMPLE_DIFF)
        diffs = parser.parse()

        self.assertEqual(len(diffs), 1)
        file_diff = diffs[0]
        self.assertEqual(file_diff.old_path, "tests/test_auth.py")
        self.assertEqual(file_diff.new_path, "tests/test_auth.py")
        self.assertFalse(file_diff.is_new)
        self.assertFalse(file_diff.is_deleted)
        self.assertEqual(len(file_diff.hunks), 1)

        hunk = file_diff.hunks[0]
        self.assertEqual(len(hunk.removed_lines), 1)
        self.assertEqual(hunk.removed_lines[0].content, "    assert user.is_authenticated is True")

    def test_parse_new_and_deleted_file(self):
        p1 = DiffParser(SAMPLE_NEW_FILE_DIFF)
        d1 = p1.parse()
        self.assertEqual(len(d1), 1)
        self.assertTrue(d1[0].is_new)
        self.assertEqual(d1[0].target_path, "src/app.test.ts")

        p2 = DiffParser(SAMPLE_DELETED_FILE_DIFF)
        d2 = p2.parse()
        self.assertEqual(len(d2), 1)
        self.assertTrue(d2[0].is_deleted)
        self.assertEqual(d2[0].target_path, "tests/test_legacy.py")


if __name__ == "__main__":
    unittest.main()
