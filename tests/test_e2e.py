"""End-to-end integration tests for AssertVet."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from assertvet.scanner import AssertVetScanner


MULTI_FILE_AGENT_SLOP = """diff --git a/src/service.py b/src/service.py
index abc..def 100644
--- a/src/service.py
+++ b/src/service.py
@@ -10,1 +10,2 @@ def calculate():
-    return 42
+    return 0  # quick fix
diff --git a/tests/test_service.py b/tests/test_service.py
index 111..222 100644
--- a/tests/test_service.py
+++ b/tests/test_service.py
@@ -5,3 +5,2 @@ def test_calculate():
-    assert calculate() == 42
-    assert calculate() > 0
+    assert calculate() is not None
diff --git a/src/client.test.ts b/src/client.test.ts
index 333..444 100644
--- a/src/client.test.ts
+++ b/src/client.test.ts
@@ -15,1 +15,1 @@
-it("connects to websocket", async () => {
+it.skip("connects to websocket", async () => {
diff --git a/package.json b/package.json
index 555..666 100644
--- a/package.json
+++ b/package.json
@@ -8,1 +8,1 @@
-    "test": "jest"
+    "test": "jest || true"
"""


class TestE2E(unittest.TestCase):
    def test_multi_file_agent_slop_diff(self):
        scanner = AssertVetScanner()
        result = scanner.scan_diff_text(MULTI_FILE_AGENT_SLOP)

        self.assertFalse(result.is_clean)
        self.assertEqual(result.files_scanned, 4)
        self.assertEqual(result.test_files_analyzed, 3)

        rule_ids = [v.rule_id.value for v in result.violations]
        self.assertIn("AV001", rule_ids)  # Deleted assertion
        self.assertIn("AV002", rule_ids)  # Softened assertion
        self.assertIn("AV003", rule_ids)  # it.skip
        self.assertIn("AV006", rule_ids)  # jest || true

    def test_git_repo_integration(self):
        """Test AssertVet against an actual temporary Git repository with staged commits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Initialize mock git repository
            subprocess.run(["git", "init"], cwd=tmppath, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmppath, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmppath, check=True)

            # Commit initial test
            test_file = tmppath / "test_math.py"
            test_file.write_text("def test_add():\n    assert 1 + 1 == 2\n")
            subprocess.run(["git", "add", "."], cwd=tmppath, check=True)
            subprocess.run(["git", "commit", "-m", "Initial test"], cwd=tmppath, check=True)

            # Tamper with test (soften assertion)
            test_file.write_text("def test_add():\n    assert 1 + 1 is not None\n")

            # Run assertvet CLI directly via python -m assertvet
            cli_path = Path(__file__).resolve().parent.parent / "bin" / "assertvet"
            proc = subprocess.run(
                ["python3", str(cli_path)],
                cwd=tmppath,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(proc.returncode, 1)
            self.assertIn("SOFTENED_ASSERTION", proc.stdout)


if __name__ == "__main__":
    unittest.main()
