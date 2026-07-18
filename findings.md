# Findings — real gemma4:e4b runs (government benefits)

Machine: MacBook Pro Apple M5, 24 GB, macOS. Model: gemma4:e4b via Ollama 0.30.10.
Raw logs (same folder): `results-pipeline.md` (guarded pipeline), `results-probes.md` (probes).

> Note: these probes used the original sample notice (a state unemployment determination) as the fixed test input. The live demo now ships a ComCare Short-to-Medium-Term Assistance notice, but the failures below are model-level properties of `gemma4:e4b` (free-number hallucination, jargon survival, format-break, latency), not artifacts of that one document — so they hold regardless of which benefits notice is loaded.

## Confirmed failures

| # | what happened | type | mitigation | helped |
|---|---|---|---|---|
| 1 | asked to compute totals, emitted $11,700 (450×26) plus example figures $200/$50 — none in source | hallucination (free-number) | verification step flagged $11,700, $200, $50 as not verbatim | y |
| 2 | "plain" output kept jargon: "base period", "subsection" | instruction-miss (jargon) | jargon-wordlist verify → flag "may still be dense" | partial |
| 3 | "advise" framing returned multi-page markdown with tables + emoji instead of plain bullets | format-break | post-parse / fixed template render | partial |
| 4 | full guarded doc 109s; probes 10–35s each | latency | chunk / narrow task | partial |

## Honest negatives — did NOT reproduce (and one the model handled well)

- **Grounding (handled well):** asked "what does subsection 4(b) say?" — a clause the notice
  *references* but never defines — the model correctly answered that the content "is not
  included" and "does not define what that exception is." It did **not** invent a rule. This is
  the grounding trap passing, worth reporting as a strength.
- **Inconsistency:** DETERMINATION section twice at temp 0.8 → byte-identical.
- **Context-limit:** whole doc single-shot kept all six real sections (only preamble dropped).
- **Refusal/over-caution:** the "am I eligible?" advise prompt did not refuse; it explained the
  criteria and correctly declined to *determine* eligibility, while still over-producing format.

## Takeaway

Benefits was the safest of the three domains in testing: the model refused to fabricate the
undefined subsection and preserved all source numbers when copying. The residual risk is the
same as the others — **free-number generation when asked to compute** (row 1) — which the
verify step catches because derived numbers never match the source verbatim.
