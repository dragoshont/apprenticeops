# Contributing to ApprenticeOps

Thanks for your interest in contributing! This is an open research project, and we welcome:

- **Bug reports** — found a crash or incorrect result? File an issue with reproduction steps.
- **Model contributions** — tested a model not in `MODELS.md`? Submit a PR with size/quant/license/capability/source.
- **Scenario additions** — have real ops incidents from your cluster that would strengthen the benchmark? (Scrub for PII and submit.)
- **Harness improvements** — found a more efficient telemetry pattern or a cleaner way to score? Let's discuss in an issue first.
- **Documentation** — unclear instructions or missing details? PRs welcome.

## Code of conduct

Be kind, be specific, assume good faith. We're a small academic community here.

## Process

1. **Open an issue first** for design questions. We want to discuss big changes before implementation.
2. **Fork, branch, commit** with clear messages (reference the issue: "Fixes #123").
3. **Keep the harness stdlib-first** — `run.py` and `baselines.py` must stay zero-dependency. Analysis tools can use numpy/scipy.
4. **Pin versions** if adding dependencies (see `requirements.txt`).
5. **Test locally** — at least a pilot run (`python3 run.py --models one.txt`) before submitting.
6. **PR description** should link the issue and explain *why* (not just *what*).

## Reporting bugs

Include:
- OS + Python version + Ollama version (`ollama --version`)
- The command you ran
- The error message (full traceback)
- A minimal reproduction case if possible

## Discussing results

ApprenticeOps is designed for reproducibility. If you:
- Run the benchmark yourself and get different numbers,
- Believe a model is mis-scored,
- Found a threat to validity,

**Please open an issue with**:
- Your environment (see `REPRODUCE.md` §6 for the capture command).
- The command you ran.
- The result that differs and why you think it's wrong.

We'll investigate together.

---

**Thanks for helping make apprentice ops better.** 🛠️
