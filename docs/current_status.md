# Current Status

Updated: 2026-06-16

VecGuide has completed its first public artifact migration. The repository now contains the core implementation, selected paper-facing run artifacts, generated tables, a frozen evidence package, and public documentation for reproducing non-API checks.

## Repository State

- Project name: `VecGuide`.
- Tentative paper title: `VecGuide: Compiler-Diagnostic-Guided LLM Source Rewriting for Automatic Vectorization`.
- Local-only notes, terminal transcripts, thesis drafts, raw credentials, and scratch archives are excluded through `.gitignore`.
- API and machine-specific paths are loaded from a local `.env` file. The public template is `.env.example`.
- Public run artifacts have been sanitized to remove local absolute paths and private working-tree snapshots.

## Current Evidence Position

The current public evidence map separates formal method evidence from supplemental, protocol-limited, screening, and boundary evidence.

- Main formal evidence: `s275`, `s258`, with `s253` as a weaker same-family supplement.
- Supplemental evidence: runtime-stride cases and selected control-flow cases.
- Protocol-limited evidence: timeout-limited cases such as `s235/s115`, which should not enter the formal main table.
- Screening evidence: origin-only runs used for candidate filtering only.
- Boundary evidence: cases such as recurrence, guard/goto, correctness, and strong-baseline-solvable examples.

See `docs/evidence_map.md` for the detailed evidence classification.

## Current Verification Baseline

The public non-API regression checks are:

```bash
python3 -m unittest \
  tests.test_experiment_strategy_config \
  tests.test_prompt_case_card_format \
  tests.test_diagnostic_rag_routing \
  tests.test_paper_table_builder \
  tests.test_experiment_run_structure
```

These checks validate strategy naming, prompt/case-card formatting, diagnostic routing, table generation, and run structure without calling an LLM API.

## Next Work

Near-term work should focus on:

- refining the public README and documentation entry points;
- keeping evidence classifications aligned with new formal runs;
- improving engineering clarity around strategy configuration, prompt construction, run contracts, and result-table generation;
- adding new experiments only when they target a clear evidence gap.

New LLM experiment commands should be run manually by the repository owner and promoted into public evidence only after correctness, benchmark protocol, and table eligibility have been checked.
