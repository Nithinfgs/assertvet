"""Parser for unified git diff output."""

import re
from pathlib import PurePath
from typing import List, Optional

from assertvet.models import DiffLine, FileDiff, Hunk


HUNK_HEADER_PATTERN = re.compile(
    r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)$"
)

PYTHON_TEST_PATTERNS = [
    r"(?:^|[/\\])test_[^/\\]+\.py$",
    r"(?:^|[/\\])[^/\\]+_test\.py$",
    r"(?:^|[/\\])tests?[/\\]+.*\.py$",
]

JS_TEST_PATTERNS = [
    r"\.(?:test|spec)\.(?:js|jsx|ts|tsx|mjs|cjs)$",
    r"(?:^|[/\\])__tests__[/\\]+.*\.(?:js|jsx|ts|tsx|mjs|cjs)$",
]

CONFIG_PATTERNS = [
    r"(?:^|[/\\])package\.json$",
    r"(?:^|[/\\])pyproject\.toml$",
    r"(?:^|[/\\])Makefile$",
    r"(?:^|[/\\])\.github[/\\]workflows[/\\]+.*\.ya?ml$",
]


def is_python_test_file(path: str) -> bool:
    """Return True if path matches standard Python test naming conventions."""
    normalized = path.replace("\\", "/")
    return any(re.search(pat, normalized, re.IGNORECASE) for pat in PYTHON_TEST_PATTERNS)


def is_javascript_test_file(path: str) -> bool:
    """Return True if path matches standard JS/TS test naming conventions."""
    normalized = path.replace("\\", "/")
    return any(re.search(pat, normalized, re.IGNORECASE) for pat in JS_TEST_PATTERNS)


def is_config_file(path: str) -> bool:
    """Return True if path is a package manifest, CI workflow, or Makefile."""
    normalized = path.replace("\\", "/")
    return any(re.search(pat, normalized, re.IGNORECASE) for pat in CONFIG_PATTERNS)


def is_relevant_test_or_config(path: str) -> bool:
    """Check if the file is a test file or relevant build/CI config."""
    return is_python_test_file(path) or is_javascript_test_file(path) or is_config_file(path)


def _strip_git_prefix(path: str) -> str:
    """Strip 'a/' or 'b/' prefix from git diff path header."""
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


class DiffParser:
    """Parses unified git diff text into structured FileDiff objects."""

    def __init__(self, diff_text: str):
        self.raw_text = diff_text
        self.lines = diff_text.splitlines()

    def parse(self) -> List[FileDiff]:
        """Parse all file diffs contained in the diff text."""
        file_diffs: List[FileDiff] = []
        current_file: Optional[FileDiff] = None
        current_hunk: Optional[Hunk] = None

        old_line_cursor = 0
        new_line_cursor = 0

        i = 0
        while i < len(self.lines):
            line = self.lines[i]

            # Detect git diff header
            if line.startswith("diff --git "):
                if current_file:
                    file_diffs.append(current_file)

                parts = line.split(" ")
                old_p = _strip_git_prefix(parts[2]) if len(parts) > 2 else None
                new_p = _strip_git_prefix(parts[3]) if len(parts) > 3 else None

                current_file = FileDiff(old_path=old_p, new_path=new_p)
                current_hunk = None
                i += 1
                continue

            if not current_file:
                # Standalone diff without "diff --git"
                if line.startswith("--- "):
                    raw_old = line[4:].strip()
                    old_p = None if raw_old == "/dev/null" else _strip_git_prefix(raw_old)
                    current_file = FileDiff(old_path=old_p, new_path=None)
                i += 1
                continue

            # Check new file mode
            if line.startswith("new file mode "):
                current_file.is_new = True
                i += 1
                continue

            # Check deleted file mode
            if line.startswith("deleted file mode "):
                current_file.is_deleted = True
                i += 1
                continue

            # Check binary diff
            if line.startswith("Binary files ") or "differ" in line:
                current_file.is_binary = True
                i += 1
                continue

            # --- path header
            if line.startswith("--- "):
                raw_old = line[4:].strip()
                if raw_old == "/dev/null":
                    current_file.is_new = True
                    current_file.old_path = None
                else:
                    current_file.old_path = _strip_git_prefix(raw_old)
                i += 1
                continue

            # +++ path header
            if line.startswith("+++ "):
                raw_new = line[4:].strip()
                if raw_new == "/dev/null":
                    current_file.is_deleted = True
                    current_file.new_path = None
                else:
                    current_file.new_path = _strip_git_prefix(raw_new)
                i += 1
                continue

            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            match = HUNK_HEADER_PATTERN.match(line)
            if match:
                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1
                header_extra = match.group(5)

                current_hunk = Hunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    header=header_extra.strip(),
                )
                current_file.hunks.append(current_hunk)
                old_line_cursor = old_start
                new_line_cursor = new_start
                i += 1
                continue

            # Inside hunk lines
            if current_hunk is not None:
                if line.startswith("+"):
                    diff_line = DiffLine(
                        prefix="+",
                        content=line[1:],
                        new_line_no=new_line_cursor,
                    )
                    current_hunk.lines.append(diff_line)
                    new_line_cursor += 1
                elif line.startswith("-"):
                    diff_line = DiffLine(
                        prefix="-",
                        content=line[1:],
                        old_line_no=old_line_cursor,
                    )
                    current_hunk.lines.append(diff_line)
                    old_line_cursor += 1
                elif line.startswith(" ") or line == "":
                    # Context line
                    diff_line = DiffLine(
                        prefix=" ",
                        content=line[1:] if line.startswith(" ") else "",
                        old_line_no=old_line_cursor,
                        new_line_no=new_line_cursor,
                    )
                    current_hunk.lines.append(diff_line)
                    old_line_cursor += 1
                    new_line_cursor += 1
                elif line.startswith("\\ No newline at end of file"):
                    # Ignore git metadata
                    pass
                else:
                    # Next file diff or unexpected line
                    pass

            i += 1

        if current_file:
            file_diffs.append(current_file)

        return file_diffs
