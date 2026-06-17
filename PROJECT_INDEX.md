# VecGuide Project Index

Updated: 2026-06-17

VecGuide is a compiler-diagnostic-guided LLM source rewriting system for automatic vectorization. This index is the public navigation entry for the repository.

## Public Entry Points

- `README.md`: project overview and basic usage.
- `docs/reproduction.md`: result inspection and reproduction notes.
- `docs/api_boundary.md`: command-level API boundary for tests, tables, and LLM experiments.
- `docs/current_status.md`: current public project state and near-term work.
- `docs/evidence_map.md`: current evidence classification for the paper draft.
- `docs/experiment_protocol.md`: strategy names, benchmark protocol, and result eligibility rules.
- `docs/submission_readiness.md`: current paper-use classification and remaining evidence gap.
- `docs/formal_repeat_plan.md`: minimal manual repeat plan for the current main evidence.
- `docs/engineering_boundaries.md`: module responsibilities and strategy naming boundaries.
- `docs/artifact_index.md`: public run/table/frozen-package inventory.
- `experiments/runs/README.md`: run-level evidence index.
- `experiments/final_packages/cgo2027_current_evidence_20260612/`: frozen evidence package.

## Code And Data Layout

| Path | Role |
| --- | --- |
| `main.py` | CLI entry for analysis, optimization, experiments, and table generation. |
| `config.py` | Global configuration. |
| `data_collector.py` | Clang diagnostic collection and problem-map construction. |
| `optimizer_pipeline.py` | LLM rewrite pipeline and strategy execution. |
| `feedback_structuring.py` | Compiler-feedback structuring and routing support. |
| `benchmark_protocols.py` | Benchmark protocol definitions. |
| `experiment_config.py`, `experiment_runner.py` | Paper-facing experiment configuration and run orchestration. |
| `paper_table_builder.py` | Result-table generation from existing run artifacts. |
| `correctness_verifier.py`, `verify_cli.py` | Correctness checking. |
| `prompts/` | Prompt templates, case cards, and vectorization knowledge. |
| `TSVC_2/` | TSVC benchmark source tree used by the experiments. |
| `tests/` | Non-API regression tests. |
| `experiments/runs/` | Public run-level artifacts. |
| `experiments/tables/` | Public generated table artifacts. |
| `experiments/final_packages/` | Frozen evidence packages. |

## Public/Private Boundary

The public repository keeps code, reproducibility notes, and selected evidence artifacts. Local planning notes, weekly reports, terminal transcripts, thesis drafts, and scratch archives are excluded through `.gitignore`. If a private note contains information that should be shared, summarize it into a public document under `docs/` instead of committing the private file directly.
