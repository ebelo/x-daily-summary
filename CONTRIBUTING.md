# Contributing to X Daily Summary Tool

Thank you for your interest in contributing! This project is open source under the [Apache 2.0 License](LICENSE). Contributions of all kinds are welcome — bug fixes, new features, documentation improvements, and new AI backend integrations.

---

## 🚀 Getting Started

### 1. Fork and clone the repository

```bash
git clone https://github.com/ebelo/x-daily-summary.git
cd x-daily-summary
```

### 2. Set up your environment

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your X API credentials — see README for details
```

### 3. Run the tests to confirm everything works

```bash
pytest
```

All tests should pass before you start making changes.

---

## 🌿 Branching Strategy

- Always branch off `main`.
- Use descriptive branch names:
  - `feature/async-batching`
  - `fix/category-hallucination`
  - `docs/update-readme`
- Keep your branch focused on a single concern. If you have multiple unrelated changes, open separate PRs.

```bash
git checkout -b feature/your-feature-name
```

---

## ✅ Before Opening a Pull Request

Please make sure of the following:

- [ ] **All tests pass:** `pytest`
- [ ] **New logic is tested:** If you add a function, add a test for it in the appropriate `tests/test_*.py` file.
- [ ] **No secrets committed:** Double-check that `.env` is not included. It is gitignored by default.
- [ ] **Code is readable:** Function names are clear, complex logic has a comment explaining *why*, not just *what*.
- [ ] **The PR description explains the problem and solution** — not just what you changed, but why.

---

## 📐 Code Style

- Python 3.10+ syntax.
- Functions should do one thing. If a function is hard to name, it is probably doing too much.
- Avoid deeply nested logic (SonarCloud will flag Cognitive Complexity > 15). Extract helpers.
- Use `f-strings` for string formatting.
- All new files should have a module-level docstring.

---

## 🤖 Adding a New AI Backend

The intelligence layer (`intel_report.py`) is designed to be extensible. To add a new backend:

1. Add a new `generate_intel_report_<backend>(raw_summary_md: str) -> str` function.
2. Register it in the `generate_intel_report()` dispatcher under a new `INTEL_BACKEND` value.
3. Add tests in `tests/test_intel_report.py` mocking the backend's API client.
4. Document the new `INTEL_BACKEND` value and any required `.env` keys in the README.

---

## 🐛 Reporting Bugs

Open a [GitHub Issue](https://github.com/ebelo/x-daily-summary/issues) with:
- A clear title describing the problem.
- Steps to reproduce.
- Expected vs actual behaviour.
- Your OS, Python version, and which `INTEL_BACKEND` you are using.

---

## 💡 Suggesting Features

Open a [GitHub Issue](https://github.com/ebelo/x-daily-summary/issues) with the label `enhancement`. Describe:
- The problem you are trying to solve.
- Your proposed solution or design.
- Any tradeoffs or alternatives you considered.

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
