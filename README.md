# Plain-Language Government Benefits Forms (gemma4:e4b)

Extract-and-highlight pipeline for the HCI & AI Mini Project. Turns a government
benefits eligibility notice into plain-language bullets **on-device**, while keeping
every deadline/dollar-amount verbatim and flagging anything the model can't tie back
to the source.

**Design point:** the model is small and will reshape numbers when asked to *do*
things with them, so numbers are extracted verbatim and highlighted, never freely
rewritten. A regex verification step catches any number not present in the source.

## Requirements

- [Ollama](https://ollama.com) running locally (tested on 0.30.10)
- `gemma4:e4b` pulled: `ollama pull gemma4:e4b`
- Python 3.9+ (standard library only — no pip install, no venv)

## Run

```bash
# 1. make sure the Ollama server is up (ollama serve, or the desktop app)
# 2. from this folder:
python3 simplify.py benefits.txt          # guarded pipeline
python3 simplify.py benefits.txt --raw    # unguarded, no mitigations
```

Guarded output shows plain bullets, `[extracted verbatim: ...]` for each section's
numbers, and `⚠` flags when a value isn't found in the source or when jargon survives.

## Web UI (for the demo)

A 3-panel browser app over the same pipeline — used for the demo video.

```bash
python3 app.py        # then open http://localhost:8000
```

- **Left — chat.** The sample notice auto-loads; **upload your own PDF** any time. Ask
  questions ("what's my deadline?") — answers are grounded **only** in the notice text,
  with the quote they used. If the answer isn't in the notice it says so (check a
  caseworker), and won't link.
- **Middle — the PDF**, with each section's clauses highlighted in its own colour.
- **Right — the plain-language version.** Each bullet carries a verbatim source quote the
  model cited; only quotes that actually appear in the notice become linkable. Numbers are
  extracted verbatim as chips. `⚠` flags jargon that survived.
- **Hover** any bullet, number chip, or PDF highlight → a line connects it to its partner
  across the panels, the rest dims, both ends pop. Bidirectional.

Server is stdlib-only; the browser side uses a **vendored** copy of PDF.js in `static/`
(no network, no pip). The sample PDF (`benefits.pdf`) is generated from `benefits.txt` on
first run via macOS `cupsfilter`. Needs the same local Ollama + `gemma4:e4b`.

> A weak model won't cite a real quote for every bullet; those simply render without a
> link rather than pointing at the wrong place — the verify step decides what may link.

## Reproduce the Model Limits Log

```bash
python3 probes.py > results-probes.md 2>&1
```

Probes drive the targeted failure modes (free-number generation / inconsistency /
advise-vs-explain framing / grounding / context-limit). Raw output lands in
`results-probes.md`; `findings.md` is the hand-classified summary that feeds the
report's Model Limits Log.

## Layout

```
simplify.py         the pipeline (chunk → extract → simplify → verify)
app.py              3-panel web UI over the pipeline (for the demo video)
test_app.py         self-check for the UI's guard wiring (no Ollama needed)
static/             vendored PDF.js (pdf.min.js + worker) — offline, no pip
probes.py           failure probes
benefits.txt        fabricated source notice
benefits.pdf        generated from benefits.txt on first run (cupsfilter)
results-pipeline.md guarded pipeline run
results-probes.md   probe run
findings.md         classified failures + honest negatives
```

## Note on the mock data

`benefits.txt` is entirely fabricated for testing — not a real government
document, and not legal or financial advice.
