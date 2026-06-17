# Submission Narrative

Updated: 2026-06-17

This document records the current paper narrative supported by the public VecGuide evidence. It is a writing guide, not a new experiment record.

## Core Story

VecGuide studies how compiler diagnostics can guide LLM source rewriting for automatic vectorization. The current evidence supports a focused claim: diagnostic and case-card guidance can make LLM rewriting more targeted and useful on selected compiler-blocked loops, but the method should not be presented as broadly dominating a strong generic prompt.

The strongest paper story is therefore:

1. Compilers expose useful diagnostic signals about why loops fail to vectorize.
2. Generic LLM rewriting can sometimes solve these kernels, so the baseline must be strong.
3. VecGuide uses diagnostics, case cards, and multi-round feedback to steer rewrites toward compiler-relevant transformations.
4. The evidence shows clear benefits in selected cases, plus important limits where strong prompting or individual components are competitive.

## Main Evidence Use

| Evidence | How to use it in the paper | Guardrail |
| --- | --- | --- |
| `s275` | Primary method-advantage example. The original matrix shows `full_method` reaching vectorized speedup, and the clean repeat keeps a large speedup advantage over `strong_plain`. | Do not claim full vectorization reliably repeats; the clean repeat is `non_vectorized_speedup`. |
| `s258` | Scalar-carry / scalar-expansion support. The clean repeat confirms multiple strategies can produce vectorized speedups. | Do not present it as a `full_method` dominance case; `strong_plain` is slightly faster in the clean repeat. |
| `s253` | Weaker same-family supplement for scalar-carry behavior. | Keep it secondary. |
| Runtime-stride and selected control-flow cases | Breadth and discussion evidence. | Avoid making them headline claims. |

## Claims To Make

The current evidence can support these claims:

- Compiler diagnostics and case-card guidance help structure LLM rewrites for automatic vectorization.
- VecGuide can produce meaningful formal speedups on selected TSVC kernels that the original compiler path does not vectorize.
- Strong generic prompting is a serious baseline; the contribution is not simply that an LLM can rewrite code.
- The method is most credible when described as targeted guidance with measurable benefits and visible failure modes.

## Claims To Avoid

Avoid these stronger claims unless future evidence changes:

- VecGuide broadly dominates strong generic prompting.
- `full_method` reliably achieves full vectorization on the main cases.
- Every component is necessary on every benchmark.
- Timeout-limited, screening-only, or boundary evidence belongs in the formal main table.
- The high `s1232` case-card-only result can be discussed without the timeout context for other LLM strategies.

## Suggested Paper Framing

Use `s275` to explain the intended method advantage: diagnostics and case-card guidance can steer the model away from a flat strong-prompt result and toward a faster rewrite. Use `s258` to show that scalar-carry rewriting is feasible and repeatable, while acknowledging that strong generic prompting can also solve it. Use boundary cases to make the evaluation credible: some kernels are strong-baseline-solvable, some are protocol-limited, and some expose correctness or performance-selection risks.

The safest abstract-level contribution wording is: VecGuide provides a compiler-diagnostic-guided LLM rewriting workflow for automatic vectorization, with evidence that diagnostic/case guidance improves selected cases and with an evaluation that separates method wins from strong-baseline and boundary behavior.

## Current Writing Priority

Before running more experiments, update the paper draft to match this evidence hierarchy:

1. Rephrase the main claim around targeted compiler-diagnostic guidance, not broad dominance.
2. Present `s275` as the main advantage case, with the repeat caveat.
3. Present `s258` as scalar-carry support, not as an exclusive method win.
4. Move timeout-limited and boundary cases into limitations or discussion.
