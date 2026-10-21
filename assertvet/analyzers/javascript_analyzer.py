"""JavaScript and TypeScript test integrity analyzer for AssertVet.

Detects deleted assertions, softened matchers, added .skip modifiers,
swallowed try/catch blocks, and empty test stubs in JS/TS test diffs.
"""

import re
from typing import List, Optional, Set, Tuple

from assertvet.analyzers.base import BaseAnalyzer
from assertvet.diff_parser import is_javascript_test_file
from assertvet.models import (
    FileDiff,
    Hunk,
    RuleID,
    Severity,
    Violation,
)


JS_SKIP_PATTERNS = [
    re.compile(r"\b(?:it|test|describe)\.skip(?:\.each)?\(", re.IGNORECASE),
    re.compile(r"\b(?:xit|xtest|xdescribe)\(", re.IGNORECASE),
    re.compile(r"\b(?:it|test)\.todo\(", re.IGNORECASE),
    re.compile(r"\btest\.fixme\(", re.IGNORECASE),
]

JS_STRICT_ASSERT_PATTERNS = [
    re.compile(r"\.to(?:Be|Equal|StrictEqual|Match|HaveLength|ContainEqual)\("),
    re.compile(r"\bassert\.(?:strictEqual|deepStrictEqual|equal|deepEqual)\("),
]

JS_SOFTENED_PATTERNS = [
    re.compile(r"\.to(?:BeDefined|BeTruthy|NotBeNull|BeInstanceOf)\("),
    re.compile(r"\.not\.toBe(?:Null|Undefined)\("),
    re.compile(r"\bassert\.(?:ok|isTrue|isDefined)\("),
]

JS_COMMENTED_ASSERT_PATTERN = re.compile(
    r"^\s*//+\s*(?:TODO:?|FIXME:?|TEMP:?)?\s*(expect\(|assert\(|assert\.)",
    re.IGNORECASE,
)


def _is_js_assertion_line(line: str) -> bool:
    """Return True if line contains an assertion call in Jest/Vitest/Chai/Node:test."""
    stripped = line.strip()
    if re.search(r"\bexpect\(.*?\)\.", stripped):
        return True
    if re.search(r"\bassert(?:\.|\()", stripped):
        return True
    if re.search(r"\.should\.", stripped):
        return True
    return False


def _extract_js_assert_subject(line: str) -> Optional[str]:
    """Extract expression under test, e.g. expect(user.role) -> 'user.role'."""
    m = re.search(r"expect\(\s*([^)]+)\s*\)", line)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"assert\.[a-zA-Z]+\(\s*([^,]+)", line)
    if m2:
        return m2.group(1).strip()
    return None


class JavaScriptAnalyzer(BaseAnalyzer):
    """Inspects JS/TS test diffs for AI-assisted test tampering and evasion."""

    def can_handle(self, file_diff: FileDiff) -> bool:
        path = file_diff.target_path
        return is_javascript_test_file(path) and not file_diff.is_binary

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
        """Detect added it.skip, test.skip, xit, test.todo (AV003)."""
        violations: List[Violation] = []
        for line in hunk.added_lines:
            content = line.content.strip()
            for pattern in JS_SKIP_PATTERNS:
                if pattern.search(content):
                    violations.append(
                        Violation(
                            rule_id=RuleID.AV003,
                            rule_name="SKIPPED_TEST",
                            severity=Severity.HIGH,
                            file_path=path,
                            line_number=line.new_line_no,
                            message=f"Added skip modifier '{content}' silences test execution.",
                            snippet=f"+ {line.content}",
                            suggestion="Remove the skip modifier and fix the underlying implementation.",
                        )
                    )
                    break
        return violations

    def _check_assertions(self, path: str, hunk: Hunk) -> List[Violation]:
        """Detect deleted assertions (AV001) or softened matchers (AV002)."""
        violations: List[Violation] = []

        removed_asserts = [l for l in hunk.removed_lines if _is_js_assertion_line(l.content)]
        added_asserts = [l for l in hunk.added_lines if _is_js_assertion_line(l.content)]
        added_commented = [
            l for l in hunk.added_lines if JS_COMMENTED_ASSERT_PATTERN.search(l.content)
        ]

        # 1. Commented-out assertions
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

        # 2. Softened assertion vs deletion
        matched_added_indices: Set[int] = set()

        for removed in removed_asserts:
            if id(removed) in commented_removed_ids:
                continue
            rem_content = removed.content.strip()
            rem_subject = _extract_js_assert_subject(rem_content)
            is_strict = any(p.search(rem_content) for p in JS_STRICT_ASSERT_PATTERNS)

            softened_match = None
            for idx, added in enumerate(added_asserts):
                if idx in matched_added_indices:
                    continue
                add_content = added.content.strip()
                add_subject = _extract_js_assert_subject(add_content)

                subjects_match = (
                    rem_subject and add_subject and (rem_subject in add_subject or add_subject in rem_subject)
                )

                is_softened = any(p.search(add_content) for p in JS_SOFTENED_PATTERNS)
                if is_strict and is_softened and (subjects_match or len(added_asserts) == 1):
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
                            f"Strict matcher '{rem_content}' was softened to loose check '{added.content.strip()}'."
                        ),
                        snippet=f"- {removed.content}\n+ {added.content}",
                        suggestion="Retain exact value validation rather than softening to presence/truthiness.",
                    )
                )
            else:
                if len(removed_asserts) > len(added_asserts):
                    violations.append(
                        Violation(
                            rule_id=RuleID.AV001,
                            rule_name="DELETED_ASSERTION",
                            severity=Severity.CRITICAL,
                            file_path=path,
                            line_number=removed.old_line_no,
                            message=f"Assertion '{rem_content}' was deleted without replacement.",
                            snippet=f"- {removed.content}",
                            suggestion="Restore the deleted assertion check to prevent silent regressions.",
                        )
                    )

        return violations

    def _check_swallowed_exceptions(self, path: str, hunk: Hunk) -> List[Violation]:
        """Detect try/catch blocks added inside test that swallow errors (AV004)."""
        violations: List[Violation] = []
        added_lines = hunk.added_lines

        for idx, line in enumerate(added_lines):
            content = line.content.strip()
            # Catch block: catch (err) { }
            if re.search(r"catch\s*\([a-zA-Z0-9_]*\)\s*\{\s*\}", content):
                violations.append(
                    Violation(
                        rule_id=RuleID.AV004,
                        rule_name="SWALLOWED_EXCEPTION",
                        severity=Severity.HIGH,
                        file_path=path,
                        line_number=line.new_line_no,
                        message="Empty catch block silently swallows errors in test.",
                        snippet=f"+ {line.content}",
                        suggestion="Remove the empty catch or assert on the rejected promise/exception.",
                    )
                )
            elif re.search(r"catch\s*\([a-zA-Z0-9_]*\)\s*\{", content):
                # Check next line
                if idx + 1 < len(added_lines):
                    next_l = added_lines[idx + 1].content.strip()
                    if next_l == "}" or next_l.startswith("//") or next_l.startswith("console."):
                        violations.append(
                            Violation(
                                rule_id=RuleID.AV004,
                                rule_name="SWALLOWED_EXCEPTION",
                                severity=Severity.HIGH,
                                file_path=path,
                                line_number=line.new_line_no,
                                message="Catch block silently ignores exceptions inside test without assertion.",
                                snippet=f"+ {line.content}",
                                suggestion="Allow exceptions to fail the test or use expect().rejects.",
                            )
                        )

        return violations

    def _check_empty_tests(self, path: str, hunk: Hunk) -> List[Violation]:
        """Detect newly added test/it blocks that are empty (AV005)."""
        violations: List[Violation] = []
        added_lines = hunk.added_lines

        for line in added_lines:
            content = line.content.strip()
            # it('...', () => {}) or test('...', () => {})
            if re.search(r"\b(?:it|test)\s*\(\s*['\"`].*?['\"`]\s*,\s*(?:async\s*)?\(\s*\)\s*=>\s*\{\s*\}\s*\)", content):
                violations.append(
                    Violation(
                        rule_id=RuleID.AV005,
                        rule_name="EMPTY_TEST",
                        severity=Severity.MEDIUM,
                        file_path=path,
                        line_number=line.new_line_no,
                        message="Newly added test block has an empty body with zero assertions.",
                        snippet=f"+ {line.content}",
                        suggestion="Add assertions verifying expected behavior, or remove the empty test block.",
                    )
                )

        return violations
