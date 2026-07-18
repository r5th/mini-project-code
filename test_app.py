#!/usr/bin/env python3
"""Self-check for app.py's guard wiring — no Ollama needed.

Fakes the model so the provenance guard is exercised deterministically: a bullet whose
cited source is verbatim in the notice verifies (may draw a line); a bullet with a
fabricated citation does not; a grounded answer with a real quote verifies. Run:
    python3 test_app.py
"""

import simplify

SOURCE = (
    "DETERMINATION\n"
    "Your weekly benefit amount is $450.00, payable for a maximum of 26 weeks.\n"
    "DEADLINES\n"
    "You must file your first weekly certification by 10/15/2026.\n"
)


def fake_generate(prompt, fmt=None, temperature=0.0):
    if "Extract every amount" in prompt:                 # extract_fields
        return '{"values": ["$450.00", "26"]}', 0.01
    if '"bullets"' in prompt:                            # simplify_chunk_cited
        return ('{"bullets":[{"text":"You get $450.00 a week.",'
                '"source":"weekly benefit amount is $450.00"},'
                '{"text":"Made-up bullet.","source":"a phrase not in the notice"}]}'), 0.01
    if "QUESTION:" in prompt:                            # answer_question
        return ('{"answer":"File your first certification by 10/15/2026.",'
                '"source":"file your first weekly certification by 10/15/2026"}'), 0.01
    return "{}", 0.01


def main():
    simplify.ollama_generate = fake_generate            # patch the source module...
    import app
    app.ollama_generate = fake_generate                 # ...and app's own import binding

    recs = [r for r in app.simplify_sections(SOURCE)]
    final = recs[-1]
    sections = recs[:-1]
    assert final.get("done") and final["sections"] == len(sections), final

    det = sections[0]
    b = {x["text"]: x for x in det["bullets"]}
    assert b["You get $450.00 a week."]["verified"] is True, det      # real citation -> linkable
    assert b["Made-up bullet."]["verified"] is False, det            # fabricated -> not linkable
    assert [n["value"] for n in det["numbers"]] == ["$450.00", "26"], det["numbers"]
    assert all("id" in n for n in det["numbers"])

    ans = app.answer_question("when is my deadline?", SOURCE)
    assert ans["verified"] is True and "10/15/2026" in ans["answer"], ans

    miss = app.answer_question("x?", SOURCE)  # fake returns the deadline quote regardless;
    assert miss["verified"] is True, miss     # quote is in SOURCE, so it verifies — sanity only

    print("ok — real citations verify (linkable), fabricated ones don't; numbers pinned; QA grounded")


if __name__ == "__main__":
    main()
