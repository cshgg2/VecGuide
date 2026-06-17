# VecGuide

**VecGuide: Compiler-Diagnostic-Guided LLM Source Rewriting for Automatic Vectorization**

VecGuide is an experimental system for studying how compiler diagnostics can guide large language models to rewrite C source code for automatic vectorization. The current artifact focuses on TSVC-style loop kernels, Clang vectorization diagnostics, correctness checking, benchmark protocols, and paper-facing run archives.

## What This Repository Contains

- `main.py`: command-line entry for analysis, optimization, experiments, and result-table generation.
- `data_collector.py`: Clang diagnostic collection and problem-map construction.
- `optimizer_pipeline.py`: LLM rewrite pipeline, strategy execution, correctness checks, and benchmark integration.
- `experiment_config.py`, `experiment_runner.py`: paper-facing strategy configuration and run orchestration.
- `paper_table_builder.py`: result-table generation from existing run artifacts.
- `prompts/`: prompt templates, case cards, and vectorization knowledge.
- `TSVC_2/`: TSVC benchmark source tree used by the experiments.
- `experiments/`: selected public run, table, and frozen evidence artifacts.
- `docs/`: public documentation for reproduction, evidence classification, and protocol rules.

## Public Documentation

Start here if you are reviewing the artifact:

- `PROJECT_INDEX.md`: repository map.
- `docs/reproduction.md`: how to inspect existing results and run non-API checks.
- `docs/api_boundary.md`: which commands may call an LLM API and which do not.
- `docs/current_status.md`: current public project state and near-term work.
- `docs/evidence_map.md`: current public evidence classification.
- `docs/experiment_protocol.md`: strategy names, benchmark protocol, and main-table eligibility.
- `docs/submission_readiness.md`: current paper-use classification and remaining evidence gap.
- `docs/submission_narrative.md`: current paper-story wording and claim guardrails.
- `docs/formal_repeat_plan.md`: minimal manual repeat plan for the current main evidence.
- `docs/engineering_boundaries.md`: module responsibilities and strategy naming boundaries.
- `docs/artifact_index.md`: migrated run/table/frozen-package inventory.
- `experiments/runs/README.md`: run-level evidence index.
- `experiments/final_packages/cgo2027_current_evidence_20260612/`: frozen evidence package.

## Current Evidence Snapshot

The current public evidence map treats `s275` and `s258` as the clearest formal method-advantage materials, with `s253` as a weaker same-family supplement. Runtime-stride and selected control-flow cases are kept as supplemental evidence. Timeout-limited, origin-only screening, and boundary cases are separated from formal main-table evidence.

See `docs/evidence_map.md` for the detailed classification.

## Setup

Create a local `.env` from the public template:

```bash
cp .env.example .env
```

Fill local values in `.env`, for example:

```bash
DEEPSEEK_API_KEY=your-api-key-here
ANTHROPIC_MODEL=glm-4.7
DEEPSEEK_BASE_URL=https://open.bigmodel.cn/api/anthropic
CLANG_PATH=/path/to/clang
SOURCE_FILE=./TSVC_2/src/tsvc.c
```

`.env` is ignored by git. Do not commit local API keys, proxy settings, or machine-specific paths.

Install dependencies:

```bash
pip install -r acpo_train_requirements.txt
```

## Non-API Checks

These checks do not call an LLM API:

```bash
python3 -m unittest \
  tests.test_public_api_boundary \
  tests.test_experiment_strategy_config \
  tests.test_prompt_case_card_format \
  tests.test_diagnostic_rag_routing \
  tests.test_paper_table_builder \
  tests.test_experiment_run_structure
```

For the command-level API boundary, see `docs/api_boundary.md`.

Regenerate a table from existing run artifacts without calling an API:

```bash
python3 main.py results-table \
  --run-dir experiments/runs/<run_id_1> \
  --run-dir experiments/runs/<run_id_2> \
  --problem-map problem_map.json \
  --output-dir experiments/tables/<table_id>
```

## Formal Experiment Template

LLM experiments may consume API quota and create new evidence. Run them manually:

```bash
python3 main.py experiment <functions...> \
  --strategies origin,strong_plain,diagnostic_only,case_card_only,full_method \
  --benchmark-protocol formal \
  --run-id <descriptive_run_id>
```

The paper-facing strategy names are `origin`, `strong_plain`, `diagnostic_only`, `case_card_only`, and `full_method`.

## Public/Private Boundary

This public repository contains code, reproducibility notes, and selected evidence artifacts. Local planning notes, weekly reports, terminal transcripts, thesis drafts, raw API credentials, and scratch archives are intentionally excluded through `.gitignore`.
