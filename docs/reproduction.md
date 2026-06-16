# VecGuide Result Inspection And Reproduction Notes

This document explains how to inspect the public VecGuide artifacts and rerun checks that do not require an LLM API call.

## 1. Public Evidence Entry Points

Read these files first:

- `PROJECT_INDEX.md`: repository-level navigation.
- `docs/evidence_map.md`: current public evidence classification.
- `docs/experiment_protocol.md`: strategy names, benchmark protocol, and main-table eligibility.
- `docs/artifact_index.md`: migrated run/table/frozen-package inventory.
- `experiments/runs/README.md`: run-level evidence index.
- `experiments/final_packages/cgo2027_current_evidence_20260612/`: frozen evidence package.

Local progress notes and terminal transcripts are not part of the public repository. Public conclusions should be traceable through run artifacts, table artifacts, and the documents above.

## 2. Environment

Run commands from the repository root:

```bash
cd <repo>
```

Install Python dependencies:

```bash
pip install -r acpo_train_requirements.txt
```

Compiler and source settings:

- Clang is selected through `CLANG_PATH` or `config.py`.
- The default TSVC source file is `TSVC_2/src/tsvc.c`.
- TSVC experiments depend on the source tree and shared headers, not just a copied single function.

Common environment variables:

```bash
export CLANG_PATH="/path/to/clang"
export SOURCE_FILE="./TSVC_2/src/tsvc.c"
export MAX_ROUNDS=3
```

LLM experiments also require model API configuration. Inspecting existing results, generating tables, and running the tests below do not call an API.

## 3. Inspect Existing Run Artifacts

Each formal run directory usually contains:

- `manifest.json`: functions, strategies, protocol, and environment summary.
- `strategy_config.json`: strategy configuration snapshot.
- `paper_results.csv`: per-function, per-strategy results.
- `paper_report.md`: readable run summary.
- `paper_summary.json` / `paper_comparison.json`: structured summaries.
- `artifact_index.json`: artifact inventory.

Example:

```bash
sed -n '1,120p' experiments/runs/cgo_candidate_s1232_triangular_loop_20260611/paper_report.md
```

The current frozen evidence scope is recorded in:

```bash
experiments/final_packages/cgo2027_current_evidence_20260612/
```

## 4. Rebuild Tables Without API Calls

Regenerate a result table from existing run artifacts:

```bash
python3 main.py results-table \
  --run-dir experiments/runs/<run_id_1> \
  --run-dir experiments/runs/<run_id_2> \
  --problem-map problem_map.json \
  --output-dir experiments/tables/<table_id>
```

The output usually includes:

- `result_table_long.csv`
- `result_table_wide.csv`
- `result_table_main_long.csv`
- `result_table_main_wide.csv`
- `result_table_summary.json`

Main-table eligibility follows `docs/experiment_protocol.md`.

## 5. Run Non-API Regression Tests

```bash
python3 -m unittest \
  tests.test_experiment_strategy_config \
  tests.test_prompt_case_card_format \
  tests.test_diagnostic_rag_routing \
  tests.test_paper_table_builder \
  tests.test_experiment_run_structure
```

These tests verify strategy naming, prompt/case-card formatting, diagnostic routing, table generation, and run structure.

## 6. Formal Experiment Template

New formal experiments should use the paper-facing strategy names:

```bash
python3 main.py experiment <functions...> \
  --strategies origin,strong_plain,diagnostic_only,case_card_only,full_method \
  --benchmark-protocol formal \
  --run-id <descriptive_run_id>
```

Commands that include LLM strategies should be launched manually by the repository owner because they may consume API quota and create new evidence. New formal results should be documented in a new run directory and, when promoted, summarized in a public `docs/` file or a new frozen package.
