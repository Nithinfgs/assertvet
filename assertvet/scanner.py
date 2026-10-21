"""Diff scanner engine for AssertVet."""

import time
from typing import List, Optional, Set

from assertvet.analyzers import get_default_analyzers
from assertvet.diff_parser import DiffParser, is_relevant_test_or_config
from assertvet.models import FileDiff, RuleID, ScanResult, Violation


class AssertVetScanner:
    """Core scanning engine that coordinates diff parsing and analyzer passes."""

    def __init__(self, ignored_rules: Optional[Set[RuleID]] = None):
        self.analyzers = get_default_analyzers()
        self.ignored_rules = ignored_rules or set()

    def scan_diff_text(self, diff_text: str) -> ScanResult:
        """Parse unified diff text and analyze for test integrity violations."""
        start_time = time.perf_counter()

        parser = DiffParser(diff_text)
        file_diffs = parser.parse()

        all_violations: List[Violation] = []
        test_files_count = 0

        for file_diff in file_diffs:
            path = file_diff.target_path
            is_relevant = is_relevant_test_or_config(path) or file_diff.is_deleted

            if is_relevant:
                test_files_count += 1
                for analyzer in self.analyzers:
                    if analyzer.can_handle(file_diff):
                        violations = analyzer.analyze(file_diff)
                        for v in violations:
                            if v.rule_id not in self.ignored_rules:
                                all_violations.append(v)

        duration = (time.perf_counter() - start_time) * 1000.0

        return ScanResult(
            violations=all_violations,
            files_scanned=len(file_diffs),
            test_files_analyzed=test_files_count,
            duration_ms=duration,
        )
