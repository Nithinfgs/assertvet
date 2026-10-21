# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-21

### Added
- Core diff parser supporting unified git diffs, working tree diffs, commit ranges, patch files, and stdin streams.
- Language analyzers for Python (`pytest`, `unittest`) and JavaScript/TypeScript (`jest`, `vitest`, `mocha`, `chai`, `node:test`).
- Config analyzer for `package.json`, `.github/workflows/*.yml`, and `Makefile`.
- Rule `AV001` (DELETED_ASSERTION): Flag assertions deleted or commented out.
- Rule `AV002` (SOFTENED_ASSERTION): Flag strict equality checks downgraded to presence/truthy checks (e.g. `assert x == 200` -> `assert x is not None`, `.toBe()` -> `.toBeDefined()`).
- Rule `AV003` (SKIPPED_TEST): Flag added skip decorators (`@pytest.mark.skip`, `it.skip`, `xit`, `test.todo`).
- Rule `AV004` (SWALLOWED_EXCEPTION): Flag exception-swallowing try/catch or try/except blocks in tests.
- Rule `AV005` (EMPTY_TEST): Flag added test functions with zero assertions.
- Rule `AV006` (TEST_SCRIPT_EVASION): Flag test command bypasses like `|| true`, `exit 0`, `--passWithNoTests`.
- Rule `AV007` (DELETED_TEST_FILE): Flag deleted test suites.
- High-performance, zero-dependency CLI (`bin/assertvet`, `python -m assertvet`).
- Colorized console reporter with contextual diff snippets and remediation advice.
- Machine-readable `--json` reporter for CI/CD pipelines.
- Remediation generator (`--suggest-fix`) with exact `git checkout` commands.
- Sample diffs and pre-commit hook template in `examples/`.
- GitHub Actions multi-OS and multi-version CI test matrix.
