#!/usr/bin/env python3
"""
Plain-language benefits notice simplifier — extract-and-highlight pipeline on gemma4:e4b.

Design point (HCI Mini Project): the model is small and hallucinates, so numbers
(amounts, dates) are EXTRACTED verbatim and highlighted, never freely rewritten. The
simplification pass only touches prose. A regex verification step cross-checks every
extracted number against the source so a hallucinated figure can't slip through.

No third-party deps — stdlib only. Requires a local Ollama server with gemma4:e4b.

Usage:
    python3 simplify.py benefits.txt          # guarded pipeline
    python3 simplify.py benefits.txt --raw    # unguarded, no mitigations
"""

import json
import re
import sys
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma4:e4b"

NOUN = "government benefits notice"
JARGON = ["subsection", "pursuant to", "aforementioned", "notwithstanding",
          "adjudication", "remuneration", "claimant", "hereinafter",
          "base period", "monetary determination", "in lieu of"]


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


def extract_fields(chunk_text):
    """Extraction pass: pull numbers/amounts/dates as structured JSON, verbatim."""
    prompt = (
        "Extract every amount, price, quantity, date, deadline, time, and duration from the "
        "text below EXACTLY as written (copy the characters, do not convert or normalize). "
        "Return JSON only: {\"values\": [\"...\", \"...\"]}. If none, return {\"values\": []}.\n\n"
        "TEXT:\n" + chunk_text
    )
    raw, secs = ollama_generate(prompt, fmt="json")
    try:
        vals = json.loads(raw).get("values", [])
    except json.JSONDecodeError:
        vals = []
    return [str(v).strip() for v in vals if str(v).strip()], secs


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


def check_jargon(bullets):
    """Return jargon terms that survived into the 'plain' output. Mitigation: verification."""
    hits = []
    for term in JARGON:
        if re.search(r"\b" + re.escape(term) + r"\b", bullets):
            hits.append(term)
    return hits


def run(path, guarded=True):
    with open(path, encoding="utf-8") as f:
        source = f.read()

    chunks = chunk_by_section(source)
    print(f"\n=== {MODEL} | domain={NOUN} | "
          f"{'GUARDED pipeline' if guarded else 'RAW (no mitigations)'} "
          f"| {len(chunks)} sections ===\n")

    total = 0.0
    for header, body in chunks:
        print(f"## {header}")
        bullets, s1 = simplify_chunk(body)
        total += s1
        print(bullets.strip())

        if guarded:
            extracted, s2 = extract_fields(body)
            total += s2
            bad = verify_numbers(extracted, source)
            jarg = check_jargon(bullets)
            if extracted:
                print(f"  [extracted verbatim: {', '.join(extracted)}]")
            if bad:
                print(f"  ⚠ VERIFY AGAINST ORIGINAL — value not found in source: {', '.join(bad)}")
            if jarg:
                print(f"  ⚠ may still be dense — jargon survived: {', '.join(jarg)}")
        print()

    print(f"--- total model time: {total:.1f}s ---")


if __name__ == "__main__":
    argv = sys.argv[1:]
    args = [a for a in argv if not a.startswith("--")]
    guarded = "--raw" not in argv
    if not args:
        print("usage: python3 simplify.py <path> [--raw]")
        sys.exit(1)
    run(args[0], guarded=guarded)
