"""Data models and structures for AssertVet."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    """Violation severity levels."""
    CRITICAL = "CRITICAL"  # Blatant test evasion or assertion removal
    HIGH = "HIGH"          # Assertion softening, skips, swallowed exceptions
    MEDIUM = "MEDIUM"      # Empty test cases, deleted test files
    LOW = "LOW"            # Suspicious patterns, loose assertions
    INFO = "INFO"          # Informational diagnostics

    @property
    def rank(self) -> int:
        """Numerical rank for severity comparison (higher = more severe)."""
        ranks = {
            Severity.INFO: 0,
            Severity.LOW: 1,
            Severity.MEDIUM: 2,
            Severity.HIGH: 3,
            Severity.CRITICAL: 4,
        }
        return ranks.get(self, 0)

    def is_at_least(self, other: "Severity") -> bool:
        """Return True if this severity is greater than or equal to other."""
        return self.rank >= other.rank


class RuleID(str, Enum):
    """AssertVet Rule Identifiers."""
    AV001 = "AV001"  # DELETED_ASSERTION
    AV002 = "AV002"  # SOFTENED_ASSERTION
    AV003 = "AV003"  # SKIPPED_TEST
    AV004 = "AV004"  # SWALLOWED_EXCEPTION
    AV005 = "AV005"  # EMPTY_TEST
    AV006 = "AV006"  # TEST_SCRIPT_EVASION
    AV007 = "AV007"  # DELETED_TEST_FILE


RULE_METADATA = {
    RuleID.AV001: {
        "name": "DELETED_ASSERTION",
        "default_severity": Severity.CRITICAL,
        "description": "An existing test assertion was deleted or commented out without replacement.",
    },
    RuleID.AV002: {
        "name": "SOFTENED_ASSERTION",
        "default_severity": Severity.HIGH,
        "description": "A strict assertion was replaced with a weaker, truthy, or presence-only check.",
    },
    RuleID.AV003: {
        "name": "SKIPPED_TEST",
        "default_severity": Severity.HIGH,
        "description": "A skip decorator or modifier was added to silence a test.",
    },
    RuleID.AV004: {
        "name": "SWALLOWED_EXCEPTION",
        "default_severity": Severity.HIGH,
        "description": "An exception-swallowing try/except or try/catch block was added inside a test.",
    },
    RuleID.AV005: {
        "name": "EMPTY_TEST",
        "default_severity": Severity.MEDIUM,
        "description": "A new test function was added with zero assertions or only placeholder pass.",
    },
    RuleID.AV006: {
        "name": "TEST_SCRIPT_EVASION",
        "default_severity": Severity.CRITICAL,
        "description": "Test execution command modified with bypass flags (e.g. '|| true', 'exit 0').",
    },
    RuleID.AV007: {
        "name": "DELETED_TEST_FILE",
        "default_severity": Severity.MEDIUM,
        "description": "An entire test file was deleted in the diff.",
    },
}


@dataclass
class Violation:
    """Represents a single test integrity violation detected in a diff."""
    rule_id: RuleID
    rule_name: str
    severity: Severity
    file_path: str
    line_number: Optional[int]
    message: str
    snippet: str
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert violation to a serializable dictionary."""
        return {
            "rule_id": self.rule_id.value,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "message": self.message,
            "snippet": self.snippet,
            "suggestion": self.suggestion,
        }


@dataclass
class DiffLine:
    """A single line within a diff hunk."""
    prefix: str  # '+', '-', ' '
    content: str  # text without the leading prefix character
    old_line_no: Optional[int] = None
    new_line_no: Optional[int] = None


@dataclass
class Hunk:
    """A hunk within a unified diff."""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: List[DiffLine] = field(default_factory=list)

    @property
    def added_lines(self) -> List[DiffLine]:
        return [l for l in self.lines if l.prefix == "+"]

    @property
    def removed_lines(self) -> List[DiffLine]:
        return [l for l in self.lines if l.prefix == "-"]

    @property
    def context_lines(self) -> List[DiffLine]:
        return [l for l in self.lines if l.prefix == " "]


@dataclass
class FileDiff:
    """A diff corresponding to a single file."""
    old_path: Optional[str]
    new_path: Optional[str]
    is_new: bool = False
    is_deleted: bool = False
    is_binary: bool = False
    hunks: List[Hunk] = field(default_factory=list)

    @property
    def target_path(self) -> str:
        """Path of the file being modified or created, fallback to old_path."""
        return self.new_path or self.old_path or "unknown"


@dataclass
class ScanResult:
    """Summary of the AssertVet inspection run."""
    violations: List[Violation] = field(default_factory=list)
    files_scanned: int = 0
    test_files_analyzed: int = 0
    duration_ms: float = 0.0

    @property
    def is_clean(self) -> bool:
        """True if no violations were detected."""
        return len(self.violations) == 0

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == Severity.LOW)

    def has_violations_at_or_above(self, threshold: Severity) -> bool:
        """Check if any violation meets or exceeds the given severity threshold."""
        return any(v.severity.is_at_least(threshold) for v in self.violations)

    def to_dict(self) -> dict:
        """Convert scan result to a serializable dictionary."""
        return {
            "is_clean": self.is_clean,
            "files_scanned": self.files_scanned,
            "test_files_analyzed": self.test_files_analyzed,
            "duration_ms": round(self.duration_ms, 2),
            "summary": {
                "total": len(self.violations),
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
            "violations": [v.to_dict() for v in self.violations],
        }
