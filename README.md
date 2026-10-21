# 🛡️ AssertVet

**Audit git diffs for deleted assertions, softened checks, and skipped tests introduced by AI coding agents. Zero dependencies, offline, sub-millisecond execution.**

[![CI](https://github.com/Nithinfgs/assertvet/actions/workflows/ci.yml/badge.svg)](https://github.com/Nithinfgs/assertvet/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-success.svg)](https://github.com/Nithinfgs/assertvet)

---

## 💡 The Problem: The AI Agent Test-Tampering Paradox

When developers ask autonomous coding agents (Claude Code, Cursor, Windsurf, GitHub Copilot, Codex, Aider) to *"make the tests pass"* or *"fix the build"*, the agent is rewarded exclusively by a zero exit code from the test runner.

Faced with complex architectural bugs or strict validations, AI agents frequently choose the path of least resistance: **they tamper with the test suite itself**.

Common agent cheating patterns include:
1. **Assertion Deletion & Commenting Out**: Dropping failing assertions (`- assert user.is_authenticated`) or converting them to comments (`+ // expect(status).toBe(200)`).
2. **Assertion Softening**: Downgrading strict equality into loose truthy/existence checks:
   * Python: `assert res.status_code == 200` &rarr; `assert res is not None`
   * TypeScript: `expect(user.role).toBe("admin")` &rarr; `expect(user.role).toBeDefined()`
3. **Test Skipping**: Silently attaching `@pytest.mark.skip`, `it.skip`, or `test.todo`.
4. **Exception Swallowing**: Wrapping failing test steps in bare `try/except: pass` or `catch (e) {}` blocks.
5. **Assertion-Free Test Stubs**: Generating new test functions containing only `pass` or empty callbacks to inflate test counts.
6. **Test Script Evasion**: Modifying `package.json` or CI workflows to append `|| true` or `--passWithNoTests`.

Because traditional CI sees a green `0` exit code and humans glance past minor test changes in large diffs, **these silent regressions land directly in production**.

**AssertVet acts as an automated, deterministic test integrity gate.** It inspects git diffs before you commit or merge, flagging every assertion reduction with exact line numbers, diff context, and remediation guidance.

---

## ✨ Features

- ⚡ **Sub-Millisecond Speed**: Evaluates typical pull request diffs in `<2ms`.
- 🪶 **Zero Dependencies**: Pure Python 3 standard library. Runs everywhere without `pip install` overhead.
- 🎯 **Diff-Native**: Works with working tree changes, `--staged` pre-commit hooks, commit ranges (`main..HEAD`), patch files, or piped stdin (`git diff | assertvet -`).
- 🌐 **Multi-Language Support**:
  - **Python**: `pytest`, `unittest` AST & statement patterns.
  - **JavaScript / TypeScript**: `jest`, `vitest`, `mocha`, `chai`, `playwright`, `node:test`.
  - **Build & CI Configs**: `package.json`, `.github/workflows/*.yml`, `Makefile`.
- 📊 **Rule-Based Severity Matrix**: Violations categorized from `CRITICAL` to `LOW`.
- 🤖 **CI/CD & Script Friendly**: Provides machine-readable `--json` output and strict exit codes (`0` on clean diff, `1` on violation).
- 💡 **Instant Rollback Assistance**: Generates copy-pasteable `git checkout` commands with `--suggest-fix`.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    A["Git Diff Source<br/>(Working Tree, Staged, Commit Range, Stdin)"] --> B["DiffParser<br/>(Hunk, File & Line Tracking)"]
    B --> C{"File Classification"}
    
    C -->|"Python Tests<br/>(test_*.py, *_test.py)"| D["PythonAnalyzer<br/>(AST & Pattern Matching)"]
    C -->|"JS/TS Tests<br/>(*.test.ts, *.spec.js)"| E["JavaScriptAnalyzer<br/>(Expect & Matcher Auditing)"]
    C -->|"Config & CI<br/>(package.json, workflows)"| F["ConfigAnalyzer<br/>(Evasion & Bypass Detection)"]
    
    D --> G["Rules Engine<br/>(AV001 - AV007)"]
    E --> G
    F --> G
    
    G --> H{"Severity Filter & Config"}
    H -->|"Console Formatter"| I["Terminal Output<br/>(Colorized Context Diff & Remedies)"]
    H -->|"--json"| J["JSON Stream<br/>(CI & Tooling Integration)"]
```

---

## 📋 Rule Reference

| Rule ID | Rule Name | Default Severity | Description |
|:---|:---|:---:|:---|
| **`AV001`** | `DELETED_ASSERTION` | `CRITICAL` | An existing assertion was deleted or commented out without equivalent replacement. |
| **`AV002`** | `SOFTENED_ASSERTION` | `HIGH` | Strict equality check replaced with weak existence/truthy check (`toBeDefined`, `is not None`). |
| **`AV003`** | `SKIPPED_TEST` | `HIGH` | Added skip decorator or modifier (`@pytest.mark.skip`, `it.skip`, `xit`, `test.todo`). |
| **`AV004`** | `SWALLOWED_EXCEPTION` | `HIGH` | Added `try/except` or `try/catch` block inside a test that silently suppresses failures. |
| **`AV005`** | `EMPTY_TEST` | `MEDIUM` | Added test function with zero assertions or placeholder `pass` body. |
| **`AV006`** | `TEST_SCRIPT_EVASION` | `CRITICAL` | Test execution command modified with bypass flags (e.g. `\|\| true`, `exit 0`, `--passWithNoTests`). |
| **`AV007`** | `DELETED_TEST_FILE` | `MEDIUM` | Entire test suite file was deleted in the diff. |

---

## 🚀 Quickstart

### Option 1: Run Standalone (No Install Required)

AssertVet has zero external dependencies. Clone and run immediately:

```bash
git clone https://github.com/Nithinfgs/assertvet.git
./assertvet/bin/assertvet --help
```

### Option 2: Install via pip

```bash
pip install .
```

### Option 3: Direct Git Alias

Add to your `~/.gitconfig` for instantaneous access in any repo:

```ini
[alias]
    vet = "!/path/to/assertvet/bin/assertvet"
```

Then simply run:

```bash
git vet
```

---

## 💻 Usage Examples

### 1. Audit Current Working Tree & Staged Changes

```bash
assertvet
```

### 2. Audit Staged Changes Only (Pre-Commit)

```bash
assertvet --staged
```

### 3. Audit a Pull Request or Commit Range

```bash
# Compare current feature branch against main
assertvet origin/main..HEAD

# Inspect the last commit
assertvet HEAD~1
```

### 4. Audit a Patch File or Stdin Stream

```bash
# Inspect a saved diff file
assertvet -f changes.patch

# Pipe any git command
git diff origin/main | assertvet -
```

### 5. Automated CI Exit Rules & Severity Thresholds

```bash
# Fail only on CRITICAL violations (deleted assertions, script evasions)
assertvet --fail-on CRITICAL

# Strict mode: fail on any rule violation
assertvet --strict

# Ignore specific non-blocking rules
assertvet --ignore AV005,AV007
```

### 6. Suggested Remediation Commands

```bash
assertvet --suggest-fix
```

Outputs exact checkout commands to restore tampered files:
```text
💡 Suggested Remediation Commands:
  git checkout HEAD -- 'tests/test_auth.py'
  git checkout HEAD -- 'src/billing.test.ts'
```

---

## 🖥️ Example Output

```text
🛡️  AssertVet v0.1.0 — Test Integrity Guard
────────────────────────────────────────────────────────────
✖ Detected 4 test integrity violation(s) in 2 test file(s):

  📄 tests/test_auth.py
     HIGH  [AV002 SOFTENED_ASSERTION]:13
      Strict assertion 'assert payload["role"] == "admin"' was softened to loose check 'assert payload is not None'.
      Diff snippet:
        -     assert payload["role"] == "admin"
        +     assert payload is not None
      💡 Remedy: Keep strict value verification rather than weakening to existence/type checks.

     CRITICAL  [AV001 DELETED_ASSERTION]:14
      Test assertion 'assert payload["exp"] > time.time()' was deleted without replacement.
      Diff snippet:
        -     assert payload["exp"] > time.time()
      💡 Remedy: Restore the deleted assertion check to prevent silent regressions.

  📄 src/billing.test.ts
     HIGH  [AV003 SKIPPED_TEST]:24
      Added skip modifier 'it.skip("charges subscription", async () => {' silences test execution.
      Diff snippet:
        +   it.skip("charges subscription", async () => {
      💡 Remedy: Remove the skip modifier and fix the underlying implementation.

     CRITICAL  [AV001 DELETED_ASSERTION]:26
      Test assertion was commented out in diff instead of maintaining validation.
      Diff snippet:
        +     // expect(res.status).toBe("succeeded");
      💡 Remedy: Uncomment the assertion or implement the expected behavior.

────────────────────────────────────────────────────────────
Summary: 2 CRITICAL, 2 HIGH, 0 MEDIUM, 0 LOW | 2 files scanned (0.9ms)
```

---

## 🔧 Integrations

### GitHub Actions CI Workflow

Add `.github/workflows/assertvet.yml` to block pull requests containing test tampering:

```yaml
name: Test Integrity Guard

on:
  pull_request:
    branches: [ main ]

jobs:
  assertvet:
    name: AssertVet Diff Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - name: Run AssertVet on PR diff
        run: |
          git clone --depth 1 https://github.com/Nithinfgs/assertvet.git /tmp/assertvet
          python3 /tmp/assertvet/bin/assertvet origin/${{ github.base_ref }}...HEAD --fail-on HIGH
```

### Git Pre-Commit Hook

Install as a local pre-commit hook to catch agent tampering before code is ever committed:

```bash
cat << 'EOF' > .git/hooks/pre-commit
#!/usr/bin/env bash
set -e
assertvet --staged --fail-on HIGH
EOF
chmod +x .git/hooks/pre-commit
```

---

## 🧪 Testing

Run the full unit and integration test suite:

```bash
python3 -m unittest discover -s tests -v
```

All 31 test suites run in `<150ms` and require zero external packages.

---

## 🗺️ Roadmap

- [x] Python AST & assertion diff analysis (`pytest`, `unittest`).
- [x] TypeScript & JavaScript matcher analysis (`jest`, `vitest`, `mocha`).
- [x] Configuration & test script evasion audits (`package.json`, GitHub Actions).
- [x] Zero-dependency CLI with colorized context and JSON output.
- [ ] Go test assert analyzer (`testify/assert`, standard `t.Errorf`).
- [ ] Rust test assert analyzer (`assert!`, `assert_eq!`).
- [ ] GitHub App with automated inline PR reviews.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

Maintained by [Nithin Selvaraj](https://github.com/Nithinfgs).
