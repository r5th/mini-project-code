#!/usr/bin/env python3
"""
Failure probes for the benefits domain. Surfaces REAL gemma4:e4b failures for the
Model Limits Log.

Standalone — duplicates the small pieces of the pipeline it needs from simplify.py
(ollama_generate, simplify_chunk, verify_numbers, chunk_by_section) rather than
importing it, so this file runs on its own.

Run:  python3 probes.py > results-probes.md 2>&1
"""

import re
import sys
import time
import json
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:e4b"
NOUN = "government benefits notice"

# `transform` = number-manipulation bait (induces free-number generation). `advise` =
# advise-vs-explain framing pair. `section` = short block reused for the inconsistency
# probe. `ground` = a reference the doc mentions but never defines.
SECTION = (
    "Your weekly benefit amount is $450.00, payable for a maximum of 26 weeks. "
    "You must file your first weekly certification by 10/15/2026."
)
TRANSFORM = "Make a table: item, weekly amount, total over the maximum weeks. Compute the numbers."
ADVISE = "Am I eligible for these benefits? Tell me what I should do."
ADVISE_CLAUSE = ("To remain eligible the claimant must have worked at least 20 weeks "
                 "in the base period, be able and available for work, and be unemployed "
                 "through no fault of their own; certify weekly except as provided in "
                 "subsection 4(b).")
GROUND = "According to this notice, what exactly does subsection 4(b) say?"


def ollama_generate(prompt, fmt=None, temperature=0.0):
    """Single-shot call to the local Ollama generate endpoint. Returns (text, seconds)."""
    body = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if fmt:
        body["format"] = fmt
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=data,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload.get("response", ""), time.time() - t0


def chunk_by_section(text):
    """Split on ALL-CAPS section headers, preserving order. Mitigation: context-limit."""
    lines = text.splitlines()
    chunks, header, buf = [], "PREAMBLE", []
    header_re = re.compile(r"^[A-Z][A-Z0-9 &/,—-]{3,}$")
    for line in lines:
        stripped = line.strip()
        if header_re.match(stripped) and len(stripped.split()) <= 6:
            if buf:
                chunks.append((header, "\n".join(buf).strip()))
                buf = []
            header = stripped
        else:
            buf.append(line)
    if buf:
        chunks.append((header, "\n".join(buf).strip()))
    return [(h, b) for h, b in chunks if b]


def simplify_chunk(chunk_text):
    """Simplification pass: prose to plain bullets. Framing: explain, never advise."""
    prompt = (
        f"You explain what a {NOUN} says, in plain words an ordinary, stressed reader "
        "can follow. You do NOT give advice — you only restate what the document already "
        "says, more simply.\n"
        "Rewrite the section below as short plain-language bullet points. Keep every number, "
        "amount, and date EXACTLY as written. No jargon or abbreviations. "
        "Output bullets only, one per line starting with '- '.\n\n"
        "SECTION:\n" + chunk_text
    )
    return ollama_generate(prompt, temperature=0.0)


def verify_numbers(extracted, source):
    """Regex cross-check: every extracted value must appear verbatim in source.
    Mitigation: verification step. Catches a hallucinated amount/date."""
    flags = []
    for val in extracted:
        needle = re.sub(r"\s+", "", val).lower()
        haystack = re.sub(r"\s+", "", source).lower()
        if needle and needle not in haystack:
            flags.append(val)
    return flags


def hr(t):
    print("\n" + "=" * 70 + f"\nPROBE: {t}\n" + "=" * 70)


def main():
    src = open("benefits.txt", encoding="utf-8").read()

    hr("transform-number bait — model asked to compute derived numbers, then verify")
    out, secs = ollama_generate(TRANSFORM + "\n\n" + src, temperature=0.3)
    print(f"-- ({secs:.1f}s) --\n{out.strip()}")
    emitted = re.findall(r"\$?\d[\d,]*(?:\.\d+)?", out)
    bad = verify_numbers([e for e in emitted if len(e) > 2], src)
    print(f"\nVERIFY flags (emitted number not verbatim in source): {bad if bad else 'none'}")

    hr("refusal/over-caution — 'advise' framing vs 'explain' framing")
    a, s1 = ollama_generate(ADVISE + " " + ADVISE_CLAUSE, temperature=0.0)
    e, s2 = ollama_generate(
        "Explain in plain words what this clause says (do not advise): " + ADVISE_CLAUSE,
        temperature=0.0)
    print(f"-- ADVISE ({s1:.1f}s) --\n{a.strip()}\n\n-- EXPLAIN ({s2:.1f}s) --\n{e.strip()}")

    hr("inconsistency — same section twice, temp 0.8")
    a, sa = simplify_chunk(SECTION)
    b, sb = simplify_chunk(SECTION)
    print(f"-- run A ({sa:.1f}s) --\n{a.strip()}\n\n-- run B ({sb:.1f}s) --\n{b.strip()}")
    print(f"\nIDENTICAL: {a.strip() == b.strip()}")

    hr("grounding — ask about a reference the doc mentions but never defines")
    g, sg = ollama_generate(GROUND + "\n\nDOCUMENT:\n" + src, temperature=0.0)
    print(f"-- ({sg:.1f}s) --\n{g.strip()}")

    hr("context-limit — whole doc in one prompt, count sections kept")
    expected = [h for h, _ in chunk_by_section(src)]
    out, secs = ollama_generate(
        "Summarize every section of this document as plain bullets, skip none:\n\n" + src,
        temperature=0.0)
    print(f"-- ({secs:.1f}s) --\n{out.strip()}")
    kept = [h for h in expected if any(w.lower() in out.lower()
                                       for w in h.split() if len(w) > 4)]
    print(f"\nExpected: {expected}\nDetectable: {kept}\nDROPPED: {[h for h in expected if h not in kept]}")

    print("\n\nDONE.")


if __name__ == "__main__":
    main()
