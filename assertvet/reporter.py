"""Console and JSON output formatters for AssertVet scan results."""

import json
import os
import sys
from typing import List, Optional

from assertvet.models import ScanResult, Severity, Violation


# ANSI Color Codes
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_DIM = "\033[2m"
COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_BLUE = "\033[34m"
COLOR_MAGENTA = "\033[35m"
COLOR_CYAN = "\033[36m"
COLOR_GRAY = "\033[90m"


def _supports_color() -> bool:
    """Return True if terminal supports ANSI color output."""
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


def _color(text: str, color_code: str, use_color: bool = True) -> str:
    if not use_color:
        return text
    return f"{color_code}{text}{COLOR_RESET}"


def _severity_badge(severity: Severity, use_color: bool = True) -> str:
    badges = {
        Severity.CRITICAL: (_color(" CRITICAL ", f"{COLOR_BOLD}\033[41m\033[37m", use_color)),
        Severity.HIGH: (_color(" HIGH ", f"{COLOR_BOLD}\033[43m\033[30m", use_color)),
        Severity.MEDIUM: (_color(" MEDIUM ", f"{COLOR_BOLD}{COLOR_YELLOW}", use_color)),
        Severity.LOW: (_color(" LOW ", f"{COLOR_BOLD}{COLOR_BLUE}", use_color)),
        Severity.INFO: (_color(" INFO ", f"{COLOR_DIM}{COLOR_CYAN}", use_color)),
    }
    return badges.get(severity, str(severity.value))


class ConsoleReporter:
    """Renders human-readable, colorized output to stdout."""

    def __init__(self, use_color: Optional[bool] = None):
        self.use_color = _supports_color() if use_color is None else use_color

    def render(self, result: ScanResult, verbose: bool = False) -> str:
        lines: List[str] = []

        # Header
        lines.append("")
        header = f"🛡️  AssertVet v0.1.0 — Test Integrity Guard"
        lines.append(_color(header, f"{COLOR_BOLD}{COLOR_CYAN}", self.use_color))
        lines.append(_color("─" * 60, COLOR_GRAY, self.use_color))

        if result.is_clean:
            success_msg = (
                f"✓ All test assertions intact. No tampering or evasion detected "
                f"across {result.test_files_analyzed} test file(s)."
            )
            lines.append(_color(success_msg, f"{COLOR_BOLD}{COLOR_GREEN}", self.use_color))
            lines.append(
                _color(
                    f"Scanned {result.files_scanned} file(s) in {result.duration_ms:.1f}ms.",
                    COLOR_DIM,
                    self.use_color,
                )
            )
            lines.append("")
            return "\n".join(lines)

        # Violations present
        lines.append(
            _color(
                f"✖ Detected {len(result.violations)} test integrity violation(s) "
                f"in {result.test_files_analyzed} test file(s):",
                f"{COLOR_BOLD}{COLOR_RED}",
                self.use_color,
            )
        )
        lines.append("")

        # Group violations by file
        by_file = {}
        for v in result.violations:
            by_file.setdefault(v.file_path, []).append(v)

        for file_path, violations in by_file.items():
            lines.append(f"  📄 {_color(file_path, COLOR_BOLD, self.use_color)}")
            for v in violations:
                loc = f":{v.line_number}" if v.line_number else ""
                badge = _severity_badge(v.severity, self.use_color)
                rule_tag = _color(f"[{v.rule_id.value} {v.rule_name}]", COLOR_BOLD, self.use_color)

                lines.append(f"    {badge} {rule_tag}{loc}")
                lines.append(f"      {_color(v.message, COLOR_YELLOW, self.use_color)}")

                # Diff snippet
                if v.snippet:
                    lines.append(f"      {_color('Diff snippet:', COLOR_DIM, self.use_color)}")
                    for snip_line in v.snippet.splitlines():
                        if snip_line.startswith("+"):
                            colored_snip = _color(f"        {snip_line}", COLOR_GREEN, self.use_color)
                        elif snip_line.startswith("-"):
                            colored_snip = _color(f"        {snip_line}", COLOR_RED, self.use_color)
                        else:
                            colored_snip = _color(f"        {snip_line}", COLOR_GRAY, self.use_color)
                        lines.append(colored_snip)

                if v.suggestion:
                    tip = _color(f"      💡 Remedy: {v.suggestion}", COLOR_CYAN, self.use_color)
                    lines.append(tip)

                lines.append("")

        # Summary footer
        lines.append(_color("─" * 60, COLOR_GRAY, self.use_color))
        summary_counts = (
            f"Summary: {result.critical_count} CRITICAL, "
            f"{result.high_count} HIGH, "
            f"{result.medium_count} MEDIUM, "
            f"{result.low_count} LOW | "
            f"{result.files_scanned} files scanned ({result.duration_ms:.1f}ms)"
        )
        lines.append(_color(summary_counts, COLOR_BOLD, self.use_color))
        lines.append("")

        return "\n".join(lines)


class JsonReporter:
    """Renders machine-readable JSON output for CI pipelines and scripts."""

    def render(self, result: ScanResult) -> str:
        return json.dumps(result.to_dict(), indent=2)
