# Contributing to AssertVet

Thank you for your interest in contributing to **AssertVet**!

AssertVet is an open-source, zero-dependency developer security and test integrity tool designed to detect assertion tampering, softened matchers, and evasion tactics in git diffs.

---

## 🛠️ Development Setup

AssertVet requires Python 3.10+ and uses only the Python standard library. No third-party wheels or virtual environments are strictly required to run or test the project.

```bash
# Clone repository
git clone https://github.com/Nithinfgs/assertvet.git
cd assertvet

# Run the test suite
python3 -m unittest discover -s tests -v

# Run the CLI against sample diffs
./bin/assertvet -f examples/ai_tampered_patch.diff
./bin/assertvet -f examples/legitimate_patch.diff
```

---

## 📐 Architecture & Principles

1. **Zero External Dependencies**: AssertVet must run instantly anywhere without requiring `pip install`. All parsing, AST inspections, and CLI formatting leverage the Python standard library.
2. **Sub-Millisecond Speed**: Scans must complete in <5ms for typical PR diffs so it can execute on every git pre-commit hook without perceptible delay.
3. **Deterministic & Offline**: Never make remote network requests or invoke external LLMs to make validation decisions.
4. **Actionable Explanations**: Every violation must include an exact line reference, code diff snippet, and remediation guidance.

---

## 🧪 Adding New Rules or Analyzers

1. Define the rule ID in `assertvet/models.py` (`RuleID.AV00X`).
2. Add the rule metadata and default severity in `RULE_METADATA`.
3. Implement detection logic in the appropriate analyzer under `assertvet/analyzers/`.
4. Add comprehensive unit tests in `tests/`.
5. Verify edge cases (e.g., ensure legitimate refactoring is not flagged).

---

## 📜 Pull Request Guidelines

- Ensure `python3 -m unittest discover -s tests -v` passes with 100% success.
- Ensure all Python files compile cleanly with `python3 -m py_compile assertvet/**/*.py`.
- Include sample diffs or tests covering new features or bug fixes.
- Follow PEP 8 style conventions.
