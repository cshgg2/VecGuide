# Experiment Protocol

Updated: 2026-06-12

This document is the public protocol summary for VecGuide experiments.

## Strategies

The paper-facing strategy names are:

- `origin`: original source baseline.
- `strong_plain`: strong LLM rewrite prompt without compiler-diagnostic guidance or case cards.
- `diagnostic_only`: compiler-diagnostic-guided rewrite without case cards.
- `case_card_only`: case-card-guided rewrite without diagnostic routing.
- `full_method`: VecGuide full method, combining compiler diagnostics and case-card guidance.

Older internal names may exist in historical artifacts, but new public experiments should use the names above.

## Formal Benchmark Protocol

The default formal protocol is:

- warmup runs: `3`
- timing runs: `10`
- batches: `5`
- protocol tag: `formal`
- main-table flag: `paper_main_table_eligible=true`

A result is eligible for the paper main table only when all of the following hold:

- `paper_main_table_eligible=true`
- correctness passes
- benchmark succeeds
- speedup is available

`screening`, `timeout_limited`, `custom`, and manually changed warmup/timing/batch settings are useful for diagnosis, but they should not be presented as formal main-table results.

## Non-API Checks

The following checks do not call an LLM API:

```bash
python3 -m unittest \
  tests.test_experiment_strategy_config \
  tests.test_prompt_case_card_format \
  tests.test_diagnostic_rag_routing \
  tests.test_paper_table_builder \
  tests.test_experiment_run_structure
```

Regenerating tables from existing run artifacts also does not call an API:

```bash
python3 main.py results-table \
  --run-dir experiments/runs/<run_id_1> \
  --run-dir experiments/runs/<run_id_2> \
  --problem-map problem_map.json \
  --output-dir experiments/tables/<table_id>
```

## LLM Experiment Commands

Commands using `python3 main.py experiment` with LLM strategies should be run manually by the repository owner, because they may consume API quota and create new experimental evidence.

Example template:

```bash
python3 main.py experiment <functions...> \
  --strategies origin,strong_plain,diagnostic_only,case_card_only,full_method \
  --benchmark-protocol formal \
  --run-id <descriptive_run_id>
```
