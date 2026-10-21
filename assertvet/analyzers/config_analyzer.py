"""Configuration and build script evasion analyzer for AssertVet.

Detects bypasses in package.json, GitHub Actions workflows, Makefiles,
and deleted test files.
"""

import re
from typing import List

from assertvet.analyzers.base import BaseAnalyzer
from assertvet.diff_parser import (
    is_config_file,
    is_javascript_test_file,
    is_python_test_file,
)
from assertvet.models import (
    FileDiff,
    RuleID,
    Severity,
    Violation,
)


EVASION_PATTERNS = [
    re.compile(r"\|\|\s*(?:true|exit\s+0)\b", re.IGNORECASE),
    re.compile(r";\s*exit\s+0\b", re.IGNORECASE),
    re.compile(r"--passWithNoTests\b", re.IGNORECASE),
    re.compile(r"continue-on-error:\s*true\b", re.IGNORECASE),
]


class ConfigAnalyzer(BaseAnalyzer):
    """Detects test command evasions and deleted test files."""

    def can_handle(self, file_diff: FileDiff) -> bool:
        path = file_diff.target_path
        # Handles config files or deleted test files
        if is_config_file(path):
            return True
        if file_diff.is_deleted and (is_python_test_file(path) or is_javascript_test_file(path)):
            return True
        return False

    def analyze(self, file_diff: FileDiff) -> List[Violation]:
        violations: List[Violation] = []
        path = file_diff.target_path

        # 1. AV007: Deleted test file
        if file_diff.is_deleted and (is_python_test_file(path) or is_javascript_test_file(path)):
            violations.append(
                Violation(
                    rule_id=RuleID.AV007,
                    rule_name="DELETED_TEST_FILE",
                    severity=Severity.MEDIUM,
                    file_path=path,
                    line_number=None,
                    message=f"Entire test file '{path}' was deleted in this diff.",
                    snippet=f"deleted file: {path}",
                    suggestion="Verify whether deleting this entire test suite was intentional.",
                )
            )
            return violations

        # 2. AV006: Test script evasion in config / CI files
        if is_config_file(path):
            for hunk in file_diff.hunks:
                for line in hunk.added_lines:
                    content = line.content.strip()
                    for pattern in EVASION_PATTERNS:
                        if pattern.search(content):
                            violations.append(
                                Violation(
                                    rule_id=RuleID.AV006,
                                    rule_name="TEST_SCRIPT_EVASION",
                                    severity=Severity.CRITICAL,
                                    file_path=path,
                                    line_number=line.new_line_no,
                                    message=f"Test script evasion pattern detected: '{content}'.",
                                    snippet=f"+ {line.content}",
                                    suggestion="Remove bypass flags like '|| true' so failing tests properly block CI.",
                                )
                            )
                            break

        return violations
