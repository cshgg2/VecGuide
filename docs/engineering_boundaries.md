# Engineering Boundaries

Updated: 2026-06-16

This document records the current low-risk engineering boundaries for VecGuide. It is meant to keep public experiments, paper terminology, and implementation modules aligned.

## Strategy Configuration

Owned by: `experiment_config.py`

Responsibilities:

- define paper-facing strategy names;
- preserve legacy aliases for old artifacts;
- freeze prompt-option switches and performance-guard defaults;
- expose strategy metadata for manifests and documentation.

Non-responsibilities:

- running experiments;
- writing run directories;
- building prompt text;
- deciding result-table eligibility.

Paper-facing strategy names are:

- `origin`
- `strong_plain`
- `diagnostic_only`
- `case_card_only`
- `full_method`

Legacy names such as `ours_full` and `llm_plain` are compatibility aliases. New public commands should use paper-facing names.

## Experiment Runner

Owned by: `experiment_runner.py`

Responsibilities:

- create isolated run directories;
- execute selected strategies;
- collect correctness, benchmark, prompt snapshot, and paper-row artifacts;
- write run-level summaries, manifests, and artifact indexes;
- support collect-only rebuilding from existing run artifacts.

Non-responsibilities:

- defining strategy semantics;
- changing prompt templates;
- changing benchmark protocol definitions;
- deciding which evidence belongs in the paper narrative.

## Benchmark Protocols

Owned by: `benchmark_protocols.py`

Responsibilities:

- define protocol presets such as `formal`, `screening`, and `timeout_limited`;
- validate warmup, timing, batch, and main-table eligibility settings.

Formal main-table eligibility should follow `docs/experiment_protocol.md`.

## Prompt Construction

Owned by: `prompts/` and prompt-related helpers in `optimizer_pipeline.py`

Responsibilities:

- build system prompts and user prompts;
- apply diagnostic routing and case-card selection;
- preserve prompt snapshots for reproducibility.

Prompt changes should be treated as method changes and reflected in prompt-version metadata.

## Result Tables

Owned by: `paper_table_builder.py`

Responsibilities:

- read existing run artifacts;
- apply result-table filters;
- generate long/wide result tables and summaries.

Result-table generation should not call an LLM API.
