# Prompt and Case-Card Versions (2026-06-01)

This file records the prompt/template versions used by CGO-oriented formal runs.
When changing the wording, structure, retrieval format, or case-card contents in a way that can affect results, bump the corresponding version string and add a short note here.

## Template Versions

- `method_system_v1_20260601`: full-method base system prompt in `prompts/templates.py`.
- `strong_plain_system_v1_20260601`: strong foundation-model baseline system prompt in `prompts/templates.py`.
- `multi_round_system_v1_20260601`: full-method multi-round system prompt in `prompts/templates.py`.
- `optimization_user_v1_20260601`: user prompt assembly logic in `build_optimization_prompt`.
- `retry_prompt_v1_20260601`: compile-error retry prompt in `build_retry_prompt`.
- `structured_feedback_v1_20260601`: structured diagnostic summary formatting in `format_structured_feedback_for_prompt`.

## Case-Card Versions

- `experiment_case_cards_v1_20260601`: current `EXPERIMENT_CASE_CARDS` set in `prompts/knowledge_base.py`.
- `case_card_format_v1_20260601`: current case-card rendering and audit format in `format_case_cards_for_prompt` / `build_case_card_audit_snapshot`.

## Snapshot Rule

Formal experiment runs launched through `main.py experiment` set `PROMPT_SNAPSHOT_DIR` for each strategy. The optimizer writes:

- `prompt_snapshot/index.json`
- `prompt_snapshot/<function>/roundXX_<kind>.json`
- `prompt_snapshot/<function>/roundXX_<kind>.md`
- `prompt_snapshot/<function>/roundXX_<kind>_case_cards.json`

The JSON snapshot stores the exact `system_prompt`, exact `user_prompt`, strategy `prompt_version`, template versions, structured diagnostics, and selected case-card IDs.

## Change Log

- 2026-06-01: Initial version record for CGO 2027 preparation. Added auditable prompt snapshots and case-card retrieval snapshots.
