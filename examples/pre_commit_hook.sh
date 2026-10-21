#!/usr/bin/env bash
# AssertVet pre-commit hook
# Install by copying to .git/hooks/pre-commit and making executable: chmod +x .git/hooks/pre-commit

set -e

# Audit only staged changes before commit
if command -v assertvet >/dev/null 2>&1; then
    assertvet --staged --fail-on HIGH
else
    # Fallback to local python module
    python3 -m assertvet --staged --fail-on HIGH
fi
