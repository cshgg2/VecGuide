# Formal Repeat Plan

Updated: 2026-06-17

This plan records the next minimal API-consuming experiments to strengthen the current main evidence. It should be run manually by the repository owner, following `docs/api_boundary.md`.

## Goal

Strengthen the two current main evidence threads without broad exploratory batches:

- `s275`: primary method-advantage case where `full_method` currently outperforms the strong plain baseline.
- `s258`: scalar-carry case where diagnostic and case-card guided strategies are consistently useful.

## Manual Commands

Run these only after checking `.env`, model settings, and API quota.

```bash
python3 main.py experiment s275   --strategies origin,strong_plain,diagnostic_only,case_card_only,full_method   --benchmark-protocol formal   --run-id cgo_repeat_s275_formal_<date>
```

```bash
python3 main.py experiment s258   --strategies origin,strong_plain,diagnostic_only,case_card_only,full_method   --benchmark-protocol formal   --run-id cgo_repeat_s258_formal_<date>
```

Use an exact date in the run id, for example `20260617`.

## Promotion Rule

Promote a repeat run into public evidence only if:

- correctness passes for the row being discussed;
- benchmark succeeds under the formal protocol;
- `paper_main_table_eligible=true` is preserved;
- result-table generation succeeds through `python3 main.py results-table`;
- the interpretation is consistent with `docs/submission_readiness.md`.

## Table Rebuild Template

After a successful run, rebuild a table without calling the API:

```bash
python3 main.py results-table   --run-dir experiments/runs/<repeat_run_id>   --problem-map problem_map.json   --output-dir experiments/tables/<repeat_table_id>
```

## Interpretation Guardrails

- If `s275` repeats the current pattern, use it as the main method-advantage example.
- If `s275` does not repeat, keep the original result but downgrade the claim strength.
- If `s258` repeats, use it as scalar-carry support rather than an exclusive `full_method` win.
- If `s258` does not repeat, keep it as a candidate family and avoid making it a headline result.


## Completed Repeats

- `cgo_repeat_s275_formal_clean_20260617`: clean repeat completed. It preserves a speedup advantage for `full_method` over `strong_plain`, but it does not repeat the full-vectorization result. Use it to moderate the `s275` claim.
