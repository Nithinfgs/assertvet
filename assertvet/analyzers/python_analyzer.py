"""Python test integrity analyzer for AssertVet.

Detects deleted assertions, softened checks, added skip decorators,
swallowed exceptions, and empty test stubs in Python test diffs.
"""

import ast
import re
from typing import List, Optional, Set, Tuple

from assertvet.analyzers.base import BaseAnalyzer
from assertvet.diff_parser import is_python_test_file
from assertvet.models import (
    FileDiff,
    Hunk,
    RuleID,
    Severity,
    Violation,
)


SKIP_PATTERNS = [
    re.compile(r"^\s*@pytest\.mark\.skip(?:\(|$)", re.IGNORECASE),
    re.compile(r"^\s*@pytest\.mark\.skipif(?:\(|$)", re.IGNORECASE),
    re.compile(r"^\s*@pytest\.mark\.xfail(?:\(|$)", re.IGNORECASE),
    re.compile(r"^\s*@unittest\.skip(?:\(|$)", re.IGNORECASE),
    re.compile(r"^\s*@unittest\.skipIf(?:\(|$)", re.IGNORECASE),
    re.compile(r"^\s*pytest\.skip\(", re.IGNORECASE),
    re.compile(r"^\s*(?:self\.)?skipTest\(", re.IGNORECASE),
    re.compile(r"^\s*raise\s+unittest\.SkipTest\(", re.IGNORECASE),
]

# Patterns representing strict assertion checks
STRICT_ASSERT_PATTERNS = [
    re.compile(r"assert\s+.*?(?:==|!=|<=|>=|<|>)\s+.*"),
    re.compile(r"self\.assert(?:Equal|Equals|NotEqual|SequenceEqual|DictEqual|ListEqual|SetEqual)\("),
]

# Patterns representing softened checks
SOFTENED_PATTERNS = [
    re.compile(r"assert\s+.*?is\s+not\s+None\b"),
    re.compile(r"assert\s+(?:bool\()?[a-zA-Z0-9_\.]+\)?(?:\s*,\s*.*)?$"),  # assert x (truthiness)
    re.compile(r"assert\s+isinstance\("),
    re.compile(r"assert\s+hasattr\("),
    re.compile(r"assert\s+len\(.*?\)\s*>=\s*0\b"),
    re.compile(r"self\.assert(?:IsNotNone|True|False)\("),
]

COMMENTED_ASSERT_PATTERN = re.compile(
    r"^\s*#+\s*(?:TODO:?|FIXME:?|TEMP:?|DEPRECATED:?)?\s*(assert\s+.*|self\.assert.*)",
    re.IGNORECASE,
)


def _is_assertion_line(line: str) -> bool:
    """Return True if line contains a standard Python assertion statement or unittest method."""
    stripped = line.strip()
    if stripped.startswith("assert ") or stripped.startswith("assert("):
        return True
    if re.search(r"\bself\.assert[a-zA-Z]+\(", stripped):
        return True
    return False


def _extract_assert_subject(line: str) -> Optional[str]:
    """Attempt to extract the primary subject/variable of an assertion."""
    m = re.search(r"assert\s+([a-zA-Z0-9_\.\[\]'\"]+)", line)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"self\.assert[a-zA-Z]+\(\s*([a-zA-Z0-9_\.\[\]'\"]+)", line)
    if m2:
        return m2.group(1).strip()
    return None


class PythonAnalyzer(BaseAnalyzer):
    """Inspects Python test diffs for AI-assisted test tampering and evasion."""

    def can_handle(self, file_diff: FileDiff) -> bool:
        path = file_diff.target_path
        return is_python_test_file(path) and not file_diff.is_binary

    def analyze(self, file_diff: FileDiff) -> List[Violation]:
        violations: List[Violation] = []
        path = file_diff.target_path

        for hunk in file_diff.hunks:
            violations.extend(self._check_skips(path, hunk))
            violations.extend(self._check_assertions(path, hunk))
            violations.extend(self._check_swallowed_exceptions(path, hunk))
            violations.extend(self._check_empty_tests(path, hunk))

        return violations

    def _check_skips(self, path: str, hunk: Hunk) -> List[Violation]:
        """Detect newly added skip decorators (AV003)."""
        violations: List[Violation] = []
        for line in hunk.added_lines:
            content = line.content.strip()
            for pattern in SKIP_PATTERNS:
                if pattern.search(content):
                    violations.append(
                        Violation(
                            rule_id=RuleID.AV003,
                            rule_name="SKIPPED_TEST",
                            severity=Severity.HIGH,
                            file_path=path,
                            line_number=line.new_line_no,
                            message=f"Added skip directive/decorator '{content}' silences test execution.",
                            snippet=f"+ {line.content}",
                            suggestion="Remove the skip directive and fix the underlying code rather than skipping.",
                        )
                    )
                    break
        return violations

    def _check_assertions(self, path: str, hunk: Hunk) -> List[Violation]:
        """Detect deleted assertions (AV001) or softened checks (AV002)."""
        violations: List[Violation] = []

        removed_asserts = [l for l in hunk.removed_lines if _is_assertion_line(l.content)]
        added_asserts = [l for l in hunk.added_lines if _is_assertion_line(l.content)]
        added_commented = [
            l for l in hunk.added_lines if COMMENTED_ASSERT_PATTERN.search(l.content)
        ]

        # 1. Check for assertions that were replaced by commented-out versions
        commented_removed_ids: Set[int] = set()
        for added_c in added_commented:
            for rem in removed_asserts:
                rem_c = rem.content.strip()
                if rem_c in added_c.content:
                    commented_removed_ids.add(id(rem))
            violations.append(
                Violation(
                    rule_id=RuleID.AV001,
                    rule_name="DELETED_ASSERTION",
                    severity=Severity.CRITICAL,
                    file_path=path,
                    line_number=added_c.new_line_no,
                    message="Test assertion was commented out in diff instead of maintaining validation.",
                    snippet=f"+ {added_c.content}",
                    suggestion="Uncomment the assertion or implement the expected behavior.",
                )
            )

        # 2. Check for assertion softening (AV002) vs pure deletion (AV001)
        matched_added_indices: Set[int] = set()

        for removed in removed_asserts:
            if id(removed) in commented_removed_ids:
                continue
            rem_content = removed.content.strip()
            rem_subject = _extract_assert_subject(rem_content)
            is_strict_removed = any(p.search(rem_content) for p in STRICT_ASSERT_PATTERNS)

            # Check if this removed strict assertion has a corresponding softened added assertion
            softened_match = None
            for idx, added in enumerate(added_asserts):
                if idx in matched_added_indices:
                    continue
                add_content = added.content.strip()
                add_subject = _extract_assert_subject(add_content)

                # Same or related subject variable
                subjects_match = (
                    rem_subject and add_subject and (rem_subject in add_subject or add_subject in rem_subject)
                )

                is_softened = any(p.search(add_content) for p in SOFTENED_PATTERNS)
                if is_strict_removed and is_softened and (subjects_match or len(added_asserts) == 1):
                    softened_match = (idx, added)
                    break

            if softened_match:
                idx, added = softened_match
                matched_added_indices.add(idx)
                violations.append(
                    Violation(
                        rule_id=RuleID.AV002,
                        rule_name="SOFTENED_ASSERTION",
                        severity=Severity.HIGH,
                        file_path=path,
                        line_number=added.new_line_no,
                        message=(
                            f"Strict assertion '{rem_content}' was softened to loose check '{added.content.strip()}'."
                        ),
                        snippet=f"- {removed.content}\n+ {added.content}",
                        suggestion="Keep strict value verification rather than weakening to existence/type checks.",
                    )
                )
            else:
                # Check if this removed assertion was replaced by any added assertion
                # If total removed assertions > total added assertions, report deleted assertion
                if len(removed_asserts) > len(added_asserts):
                    violations.append(
                        Violation(
                            rule_id=RuleID.AV001,
                            rule_name="DELETED_ASSERTION",
                            severity=Severity.CRITICAL,
                            file_path=path,
                            line_number=removed.old_line_no,
                            message=f"Test assertion '{rem_content}' was deleted without replacement.",
                            snippet=f"- {removed.content}",
                            suggestion="Restore the deleted assertion check to prevent silent regressions.",
                        )
                    )

        return violations

    def _check_swallowed_exceptions(self, path: str, hunk: Hunk) -> List[Violation]:
        """Detect try/except blocks added inside test functions that swallow errors (AV004)."""
        violations: List[Violation] = []
        added_lines = hunk.added_lines

        for idx, line in enumerate(added_lines):
            content = line.content.strip()
            # Look for except blocks with pass or no raise
            if re.match(r"^except\s*(?:Exception|BaseException)?(?:\s+as\s+[a-zA-Z0-9_]+)?\s*:", content):
                # Inspect following added lines to see if it just passes or ignores
                swallowed = False
                if idx + 1 < len(added_lines):
                    next_line = added_lines[idx + 1].content.strip()
                    if next_line in ("pass", "continue", "..."):
                        swallowed = True
                    elif re.match(r"^(?:print|logger\.[a-z]+)\(", next_line):
                        swallowed = True

                if swallowed:
                    violations.append(
                        Violation(
                            rule_id=RuleID.AV004,
                            rule_name="SWALLOWED_EXCEPTION",
                            severity=Severity.HIGH,
                            file_path=path,
                            line_number=line.new_line_no,
                            message="Exception caught and silently swallowed inside test block.",
                            snippet=f"+ {line.content}",
                            suggestion="Allow exceptions to bubble up or use 'pytest.raises()' / 'assertRaises()'.",
                        )
                    )

        return violations

    def _check_empty_tests(self, path: str, hunk: Hunk) -> List[Violation]:
        """Detect newly added test functions with zero assertions (AV005)."""
        violations: List[Violation] = []
        added_lines = hunk.added_lines

        for idx, line in enumerate(added_lines):
            content = line.content.strip()
            match = re.match(r"^def\s+(test_[a-zA-Z0-9_]+)\s*\(.*?\)\s*:", content)
            if match:
                test_name = match.group(1)
                # Check lines within the function body
                has_assert = False
                has_body_code = False
                only_pass = False

                body_lines: List[str] = []
                for j in range(idx + 1, min(idx + 12, len(added_lines))):
                    l_content = added_lines[j].content.strip()
                    if l_content.startswith("def ") or (l_content and not added_lines[j].content.startswith("    ")):
                        break
                    if l_content and not l_content.startswith("#") and not l_content.startswith('"""'):
                        body_lines.append(l_content)
                        if _is_assertion_line(l_content) or "pytest.raises" in l_content:
                            has_assert = True
                        if l_content != "pass":
                            has_body_code = True
                        else:
                            only_pass = True

                if (only_pass and not has_body_code) or (body_lines and not has_assert and len(body_lines) <= 2):
                    violations.append(
                        Violation(
                            rule_id=RuleID.AV005,
                            rule_name="EMPTY_TEST",
                            severity=Severity.MEDIUM,
                            file_path=path,
                            line_number=line.new_line_no,
                            message=f"Test '{test_name}' has no assertions or validation logic.",
                            snippet=f"+ {line.content}",
                            suggestion="Add assertions to test real behavior, or remove the empty placeholder test.",
                        )
                    )

        return violations
