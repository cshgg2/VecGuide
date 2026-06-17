# API Boundary

Updated: 2026-06-17

This document records which public VecGuide commands may call an LLM API and which commands are safe for local inspection, testing, or table rebuilding.

## Does Not Call An LLM API

These commands operate on local files, compiler diagnostics, existing run artifacts, or generated summaries:

| Command pattern | Purpose |
| --- | --- |
| `python3 -m unittest ...` | run non-API regression tests |
| `python3 main.py analyze ...` | collect compiler vectorization diagnostics |
| `python3 main.py evaluate ...` | evaluate saved optimized code |
| `python3 main.py verify ...` | run correctness checks on saved code |
| `python3 main.py benchmark ...` | benchmark existing original or saved optimized code |
| `python3 main.py results-table ...` | rebuild result tables from existing run artifacts |
| `python3 main.py experiment --dry-run ...` | create a run manifest only |
| `python3 main.py experiment --collect-only --run-id <run_id>` | rebuild paper summaries from an existing run |
| `python3 main.py experiment --cleanup-run-id <run_id>` | remove a named run directory |

`--dry-run`, `--collect-only`, and `--cleanup-run-id` are intended for artifact inspection or maintenance. They should not call the optimizer or contact an LLM provider.

## May Call An LLM API

These commands may call the configured LLM provider when they include optimizer-enabled strategies or normal optimization flow:

| Command pattern | Why it may call an API |
| --- | --- |
| `python3 main.py optimize ...` | invokes `optimizer_pipeline.py` to request rewritten source code |
| `python3 main.py pipeline ...` | includes the optimize stage |
| `python3 main.py experiment ...` without `--dry-run` or `--collect-only` | executes selected strategies; LLM strategies request rewritten source code |
| `python3 optimizer_pipeline.py ...` | direct optimizer entry |
| `python3 experiment_runner.py ...` without `--dry-run` or `--collect-only` | direct experiment runner entry |

The `origin` strategy benchmarks original code and does not require an LLM rewrite. Strategies such as `strong_plain`, `diagnostic_only`, `case_card_only`, and `full_method` are optimizer-enabled and may consume API quota.

## Operating Rule

Run API-consuming commands manually, with a deliberate `--run-id`, after confirming `.env` and quota state. Promote new results into public evidence only after correctness, benchmark protocol, and result-table eligibility have been checked.
