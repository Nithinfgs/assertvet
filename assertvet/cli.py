"""Command-line interface for AssertVet."""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Set

from assertvet import __version__
from assertvet.models import RuleID, Severity
from assertvet.reporter import ConsoleReporter, JsonReporter
from assertvet.scanner import AssertVetScanner


def _run_git_command(args: List[str]) -> str:
    """Execute a git command and return stdout as string."""
    try:
        proc = subprocess.run(
            ["git"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        return proc.stdout
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"git error: {e.stderr.strip()}\n")
        sys.exit(2)
    except FileNotFoundError:
        sys.stderr.write("Error: 'git' executable not found in PATH.\n")
        sys.exit(2)


def _get_diff_text(args: argparse.Namespace) -> str:
    """Retrieve diff text from stdin, file, or git invocation."""
    # Stdin mode
    if args.stdin or args.target == "-":
        return sys.stdin.read()

    # File mode
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            sys.stderr.write(f"Error: Diff file '{args.file}' does not exist.\n")
            sys.exit(2)
        return file_path.read_text(encoding="utf-8", errors="replace")

    # Git diff mode
    git_args = ["diff"]

    if args.staged:
        git_args.append("--staged")
    elif args.target:
        git_args.append(args.target)
    else:
        # Default: check working tree + staged (diff against HEAD if repo has commits)
        # Check if HEAD exists
        has_head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0

        if has_head:
            git_args.append("HEAD")
        else:
            # Empty repo without initial commit, diff staged
            git_args.append("--staged")

    return _run_git_command(git_args)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="assertvet",
        description=(
            "Audit git diffs for deleted assertions, softened checks, and skipped tests "
            "introduced by AI coding agents or automated pull requests."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        help="Git revision or commit range (e.g. 'HEAD~1', 'origin/main...HEAD', or '-' for stdin).",
    )
    parser.add_argument(
        "-s", "--staged",
        action="store_true",
        help="Audit only staged changes (git diff --staged).",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read diff from standard input.",
    )
    parser.add_argument(
        "-f", "--file",
        metavar="PATH",
        help="Read diff from a patch/diff file instead of running git.",
    )
    parser.add_argument(
        "--fail-on",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
        default="HIGH",
        help="Minimum severity level required to trigger a non-zero exit code (default: HIGH).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any violation regardless of severity (equivalent to --fail-on LOW).",
    )
    parser.add_argument(
        "--ignore",
        metavar="RULES",
        help="Comma-separated list of rule IDs to ignore (e.g. 'AV005,AV007').",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output.",
    )
    parser.add_argument(
        "--suggest-fix",
        action="store_true",
        help="Print git checkout / restore suggestions for flagged test files.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"assertvet {__version__}",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    # Parse ignored rules
    ignored_rules: Set[RuleID] = set()
    if args.ignore:
        for r in args.ignore.split(","):
            r_clean = r.strip().upper()
            try:
                ignored_rules.add(RuleID(r_clean))
            except ValueError:
                sys.stderr.write(f"Warning: Unknown rule ID '{r_clean}' in --ignore option.\n")

    diff_text = _get_diff_text(args)

    if not diff_text.strip():
        if args.json:
            empty_res = {
                "is_clean": True,
                "files_scanned": 0,
                "test_files_analyzed": 0,
                "duration_ms": 0.0,
                "summary": {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
                "violations": [],
            }
            import json
            print(json.dumps(empty_res, indent=2))
        else:
            print("AssertVet: No diff changes detected to audit.")
        return 0

    # Run scanner
    scanner = AssertVetScanner(ignored_rules=ignored_rules)
    result = scanner.scan_diff_text(diff_text)

    # Render output
    if args.json:
        reporter = JsonReporter()
        print(reporter.render(result))
    else:
        use_color = False if args.no_color else None
        reporter = ConsoleReporter(use_color=use_color)
        print(reporter.render(result))

        if args.suggest_fix and not result.is_clean:
            print("\n💡 Suggested Remediation Commands:")
            touched_files = sorted(set(v.file_path for v in result.violations))
            for f in touched_files:
                print(f"  git checkout HEAD -- '{f}'")
            print("")

    # Determine exit code based on threshold
    threshold = Severity.LOW if args.strict else Severity(args.fail_on)

    if result.has_violations_at_or_above(threshold):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
