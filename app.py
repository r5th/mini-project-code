#!/usr/bin/env python3
"""
Linked PDF demo UI over the benefits-notice pipeline — for the demo video.

Three panels: chat (left) · PDF viewer (middle) · plain-language output (right). Upload a
benefits notice as a PDF; each section is simplified into plain bullets, and every bullet
carries a VERBATIM source quote the model cited. We verify that quote actually appears in
the notice (same whitespace-normalized check the CLI uses on numbers) — only then is the
bullet allowed to draw a connector line to its exact spot in the PDF. Numbers are extracted
verbatim and pinned the same way. The chat answers questions grounded ONLY in the notice.

Reuses simplify.py unchanged. Stdlib only (PDF.js is a vendored client-side JS file, no pip).
Needs a local Ollama server with gemma4:e4b, plus macOS `cupsfilter` to build the sample PDF.

Usage:
    python3 app.py            # then open http://localhost:8000
"""

import json
import os
import re
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from simplify import (MODEL, NOUN, chunk_by_section, check_jargon,
                      extract_fields, ollama_generate)

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_TXT = os.path.join(HERE, "benefits.txt")
SAMPLE_PDF = os.path.join(HERE, "benefits.pdf")
STATIC = os.path.join(HERE, "static")
PORT = 8000


def _norm(s):
    return re.sub(r"\s+", "", s).lower()


def _verify(needle, haystack):
    """Verbatim check: needle appears in haystack ignoring whitespace/case.
    Same guard the CLI's verify_numbers uses — here it gates whether a line may be drawn."""
    n = _norm(needle)
    return bool(n) and n in _norm(haystack)


def ensure_sample_pdf():
    """Build benefits.pdf from benefits.txt on first need (macOS cupsfilter, no pip dep)."""
    if os.path.exists(SAMPLE_PDF):
        return
    with open(SAMPLE_PDF, "wb") as out:
        subprocess.run(["cupsfilter", SAMPLE_TXT], stdout=out,
                       stderr=subprocess.DEVNULL, check=True)


def simplify_chunk_cited(body):
    """Simplification pass that also cites, per bullet, the verbatim source phrase it used."""
    prompt = (
        f"You explain what a {NOUN} says, in plain words an ordinary, stressed reader can "
        "follow. You do NOT give advice — you only restate what the document says, more simply.\n"
        "Rewrite the SECTION below as short plain-language bullets. For EACH bullet, include "
        "the exact phrase from the SECTION it is based on, copied verbatim (same characters, "
        "long enough to locate — a clause, not one word). Keep every number, amount, and date "
        "EXACTLY as written. No jargon or abbreviations.\n"
        'Return JSON only: {"bullets":[{"text":"<plain bullet>",'
        '"source":"<verbatim phrase from the SECTION>"}]}.\n\n'
        "SECTION:\n" + body
    )
    raw, secs = ollama_generate(prompt, fmt="json")
    try:
        items = json.loads(raw).get("bullets", [])
    except (json.JSONDecodeError, AttributeError):
        items = []
    return items, secs


def simplify_sections(source):
    """Per-section generator. Yields dicts with cited+verified bullets and verbatim numbers."""
    chunks = chunk_by_section(source)
    total = 0.0
    for idx, (header, body) in enumerate(chunks):
        items, s1 = simplify_chunk_cited(body)
        total += s1
        extracted, s2 = extract_fields(body)
        total += s2
        bullets = []
        for i, it in enumerate(items):
            text = str(it.get("text", "")).strip()
            src = str(it.get("source", "")).strip()
            if not text:
                continue
            bullets.append({"id": f"b{idx}_{i}", "text": text, "source": src,
                            "verified": _verify(src, body)})
        numbers = [{"id": f"n{idx}_{i}", "value": v} for i, v in enumerate(extracted)]
        yield {"idx": idx, "header": header, "bullets": bullets, "numbers": numbers,
               "jargon": check_jargon(" ".join(b["text"] for b in bullets))}
    yield {"done": True, "seconds": round(total, 1), "sections": len(chunks)}


def answer_question(question, doc_text):
    """Grounded QA: answer using only the notice; cite a verbatim quote we can verify."""
    prompt = (
        f"You answer questions about a {NOUN} using ONLY the notice text below. Do not use "
        "outside knowledge. If the answer is not in the notice, say you can't find it and to "
        "check with a caseworker. Keep it to 1-3 short plain sentences. Do NOT decide whether "
        "the person qualifies — only restate what the notice says.\n"
        'Return JSON only: {"answer":"<plain answer>",'
        '"source":"<verbatim quote from the notice you used, or empty>"}.\n\n'
        "NOTICE:\n" + doc_text + "\n\nQUESTION: " + question
    )
    raw, _ = ollama_generate(prompt, fmt="json")
    try:
        d = json.loads(raw)
        answer = str(d.get("answer", "")).strip()
        source = str(d.get("source", "")).strip()
    except (json.JSONDecodeError, AttributeError):
        answer, source = raw.strip(), ""
    return {"answer": answer or "(no answer)", "source": source,
            "verified": _verify(source, doc_text)}


PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Plain-language benefits notice</title>
<script src="/static/pdf.min.js"></script>
<style>
  :root { color-scheme: light dark;
    --s0:#2563eb; --s1:#059669; --s2:#d97706; --s3:#7c3aed; --s4:#db2777; --s5:#0891b2; --s6:#65a30d; }
  * { box-sizing: border-box; }
  html,body { height:100%; margin:0; }
  body { font:14px/1.5 -apple-system, system-ui, sans-serif; background:#f6f7f9; color:#14171a; }
  .app { display:grid; grid-template-columns:300px 1fr 380px; height:100vh; }
  .app > * { min-height:0; }             /* let children scroll inside the grid */

  /* chat */
  #chat { display:flex; flex-direction:column; background:#111827; color:#e5e7eb; }
  #chat .hd { padding:12px 14px; font-weight:600; border-bottom:1px solid #1f2937; }
  #chat .hd small { display:block; font-weight:400; opacity:.6; font-size:11px; }
  #msgs { flex:1; overflow:auto; padding:12px; display:flex; flex-direction:column; gap:8px; }
  .msg { padding:7px 10px; border-radius:10px; max-width:92%; white-space:pre-wrap; font-size:13px; }
  .msg.sys { background:#1f2937; color:#9ca3af; align-self:center; text-align:center; font-size:12px; }
  .msg.user { background:#2563eb; color:#fff; align-self:flex-end; }
  .msg.bot { background:#1f2937; align-self:flex-start; }
  .msg.bot.link { cursor:pointer; border:1px solid #374151; }
  .msg .cite { display:block; margin-top:4px; font-size:11px; opacity:.6; }
  #chat .foot { display:flex; gap:6px; padding:10px; border-top:1px solid #1f2937; }
  #q { flex:1; background:#0b1220; color:#e5e7eb; border:1px solid #374151; border-radius:8px; padding:8px; font:inherit; }
  #chat button { background:#2563eb; color:#fff; border:0; border-radius:8px; padding:8px 10px; cursor:pointer; font:inherit; }
  #chat .up { margin:0 10px 10px; }
  #chat label.up { display:block; background:#1f2937; text-align:center; padding:9px; border-radius:8px; cursor:pointer; }
  #chat input[type=file] { display:none; }

  /* viewer */
  #viewer { overflow:auto; background:#4b5563; padding:16px; }
  .pdf-page { position:relative; margin:0 auto 16px; background:#fff; box-shadow:0 2px 12px rgba(0,0,0,.4); }
  .pdf-page canvas { position:absolute; inset:0; }
  .highlightLayer { position:absolute; inset:0; z-index:4; pointer-events:none; }  /* above text so hovering the clause hits a highlight */
  .textLayer { position:absolute; inset:0; overflow:hidden; opacity:1; line-height:1;
    z-index:3; color:transparent; user-select:none; pointer-events:none; }
  .textLayer span { position:absolute; white-space:pre; transform-origin:0 0; }
  .hl { position:absolute; border-radius:2px; background:var(--c); opacity:.28;
    pointer-events:auto; cursor:pointer; color:transparent; overflow:visible;
    display:flex; align-items:center; justify-content:flex-start; white-space:pre;
    font-family:ui-monospace,Menlo,monospace; transform-origin:left center;
    transition:transform .13s, box-shadow .13s, opacity .13s, color .13s; }

  /* panel */
  #panel { overflow:auto; background:#f6f7f9; padding:14px; }
  #panel .top { font-weight:600; margin:2px 4px 12px; }
  .card { background:#fff; border:1px solid #e5e7eb; border-left:4px solid var(--c);
    border-radius:10px; padding:12px 14px; margin-bottom:12px; }
  .card h3 { margin:0 0 8px; font-size:12px; letter-spacing:.04em; color:var(--c); text-transform:uppercase; }
  .bullet { padding:5px 8px; border-radius:7px; transition:opacity .15s, transform .15s, box-shadow .15s; }
  .bullet.link { cursor:pointer; }
  .bullet.link::before { content:"•"; color:var(--c); margin-right:6px; }
  .bullet.nolink { color:#6b7280; }
  .bullet.nolink::before { content:"◦"; color:#9ca3af; margin-right:6px; }
  .chips { margin-top:8px; display:flex; flex-wrap:wrap; gap:6px; }
  .chip { background:var(--c); color:#fff; border-radius:999px; padding:2px 10px; font-size:12px;
    font-variant-numeric:tabular-nums; cursor:pointer; transition:opacity .15s, transform .15s, box-shadow .15s; }
  .jargon { margin-top:8px; font-size:12px; color:#92400e; background:#fffbeb; border:1px solid #fde68a;
    border-radius:7px; padding:6px 8px; }

  /* focus / dim / pop */
  .app.focused .bullet.link, .app.focused .chip, .app.focused .msg.bot.link { opacity:.32; }
  .app.focused .hl { opacity:.12; }                    /* dim the other highlights (base .28) */
  .app.focused .active { opacity:1 !important; }
  .bullet.active, .chip.active, .msg.bot.active { transform:scale(1.06); box-shadow:0 6px 20px rgba(0,0,0,.18); }
  /* pop the highlighted clause: opaque coloured chip over its own glyphs — small lift, no spread */
  .hl.active { opacity:1 !important; color:#fff; transform:translateY(-1px) scale(1.04);
    box-shadow:0 4px 12px rgba(0,0,0,.4); z-index:6; border-radius:2px; }

  #wires { position:fixed; inset:0; width:100vw; height:100vh; pointer-events:none; z-index:50; }
  #wires path { fill:none; stroke-width:2.5; }

  @media (prefers-color-scheme: dark) {
    body { background:#0f1115; color:#e5e7eb; }
    #panel { background:#0f1115; } .card { background:#1a1d23; border-color:#2b303a; }
    .bullet.nolink { color:#9aa4b2; }
  }
</style></head>
<body>
<div class="app">
  <aside id="chat">
    <div class="hd">Benefits helper<small>MODEL_SLOT · on-device · answers only from your notice</small></div>
    <div id="msgs"></div>
    <label class="up">Upload a benefits notice (PDF)<input id="file" type="file" accept="application/pdf"></label>
    <div class="foot">
      <input id="q" placeholder="Ask about your notice…" autocomplete="off">
      <button id="send">Ask</button>
    </div>
  </aside>
  <main id="viewer"></main>
  <aside id="panel"><div class="top">Plain-language version</div><div id="out"></div></aside>
</div>
<svg id="wires"></svg>

<script>
// rAF is paused while a tab is backgrounded, which hangs pdf.js's render/text-layer promises.
// Fall back to a timer when hidden so rendering completes regardless of visibility.
const _raf = window.requestAnimationFrame.bind(window);
window.requestAnimationFrame = cb => document.hidden ? setTimeout(() => cb(performance.now()), 16) : _raf(cb);

pdfjsLib.GlobalWorkerOptions.workerSrc = "/static/pdf.worker.min.js";
const $ = s => document.querySelector(s);
const viewer = $("#viewer"), out = $("#out"), msgs = $("#msgs"), svg = $("#wires");
let PAGES = [];          // [{pageDiv, index}]  built after render
let DOC_TEXT = "";       // full notice text (for /ask)
const LINKS = {};        // id -> section idx (for wire color)

function chat(cls, html){ const d=document.createElement("div"); d.className="msg "+cls; d.innerHTML=html; msgs.appendChild(d); msgs.scrollTop=msgs.scrollHeight; return d; }
function esc(s){ return (s||"").replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
function cvar(idx){ return "var(--s"+(idx%7)+")"; }

/* ---------- PDF render ---------- */
async function renderPdf(data){
  viewer.innerHTML = ""; PAGES = [];
  const pdf = await pdfjsLib.getDocument({data}).promise;
  const avail = (viewer.getBoundingClientRect().width || 900) - 48;
  const base1 = (await pdf.getPage(1)).getViewport({scale:1}).width;
  const scale = Math.max(0.9, Math.min(1.7, avail / base1));
  let text = "";
  for (let p=1; p<=pdf.numPages; p++){
    const page = await pdf.getPage(p);
    const vp = page.getViewport({scale});
    const div = document.createElement("div");
    div.className = "pdf-page"; div.style.width = vp.width+"px"; div.style.height = vp.height+"px";
    const canvas = document.createElement("canvas");
    canvas.width = vp.width; canvas.height = vp.height;
    const hl = document.createElement("div"); hl.className = "highlightLayer";
    const tl = document.createElement("div"); tl.className = "textLayer";
    tl.style.setProperty("--scale-factor", scale);
    div.append(canvas, hl, tl); viewer.appendChild(div);
    await page.render({canvasContext:canvas.getContext("2d"), viewport:vp}).promise;
    const tc = await page.getTextContent();
    // Fire-and-forget: the DOM text layer is only for optional text selection; highlights are
    // computed from items. Its promise relies on rAF and never resolves in a backgrounded tab,
    // so awaiting it would hang the whole pipeline. (textContentSource renders 0 spans in 3.11.174.)
    pdfjsLib.renderTextLayer({textContent:tc, container:tl, viewport:vp, textDivs:[]}).promise.catch(()=>{});
    text += pageText(tc) + "\n";
    PAGES.push({pageDiv:div, vp, index:buildIndex(tc.items)});
  }
  await document.fonts.ready;
  DOC_TEXT = text;
  return text;
}

/* Reconstruct line breaks the CLI's chunk_by_section relies on (join(" ") would lose them,
   collapsing the whole notice into one section). Use pdf.js EOL flags + y-position jumps. */
function pageText(tc){
  let out = "", lastY = null;
  for (const it of tc.items){
    const y = it.transform ? it.transform[5] : null;
    if (lastY !== null && y !== null && Math.abs(y - lastY) > 2) out += "\n";
    out += it.str + " ";
    if (it.hasEOL) out += "\n";
    lastY = y;
  }
  return out;
}

/* ---------- string -> highlight boxes ----------
   Computed from getTextContent() items + the viewport transform, NOT the DOM text layer:
   pdf.js flushes text spans via requestAnimationFrame, which pauses in a backgrounded tab,
   so DOM-based anchoring is nondeterministic. Item geometry is exact and always available. */
function buildIndex(items){
  let norm = ""; const map = [];        // map[k] = index of the item normalized-char k came from
  items.forEach((it,i)=>{ for (const ch of it.str){ if (/\s/.test(ch)) continue; map.push(i); norm += ch.toLowerCase(); } });
  return {items, norm, map};
}
function locate(idx, target){
  const needle = (target||"").replace(/\s+/g,"").toLowerCase();
  if (!needle || !idx.norm) return null;
  const at = idx.norm.indexOf(needle);
  if (at < 0) return null;
  const set = new Set();
  for (let k=at; k<at+needle.length; k++) set.add(idx.map[k]);
  return [...set].sort((a,b)=>a-b);      // item indices covering the match
}
function itemRect(it, vp){
  const t = pdfjsLib.Util.transform(vp.transform, it.transform);
  const h = Math.hypot(t[2], t[3]);      // font height in device px
  return {left:t[4], top:t[5]-h, width:it.width*vp.scale, height:h};
}
function paint(source, id, secIdx){
  for (const pg of PAGES){
    const hits = locate(pg.index, source);
    if (!hits) continue;
    const layer = pg.pageDiv.querySelector(".highlightLayer");
    for (const i of hits){
      const r = itemRect(pg.index.items[i], pg.vp);
      if (r.width<1 || r.height<1) continue;
      const b = document.createElement("div");
      b.className = "hl"; b.dataset.link = id; b.style.setProperty("--c", cvar(secIdx));
      const s = pg.index.items[i].str;
      b.textContent = s;   // transparent at rest (canvas shows the glyphs); white on .active
      const fs = r.width/(0.6*Math.max(1,s.length));  // monospace advance ~0.6em → text fills box width, overlays the glyphs
      b.style.cssText += `left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;font-size:${fs}px;line-height:${r.height}px`;
      layer.appendChild(b);
    }
    LINKS[id] = secIdx;
    return true;
  }
  return false;
}

/* ---------- wires + focus ---------- */
let active = null, raf = 0;
function partnerPts(id){
  const hl = document.querySelector(`.hl[data-link="${id}"]`);
  const item = document.querySelector(`.link[data-link="${id}"]`);
  if (!hl || !item) return null;
  const vv = viewer.getBoundingClientRect(), pv = $("#panel").getBoundingClientRect();
  const h = hl.getBoundingClientRect(), t = item.getBoundingClientRect();
  if (h.bottom<vv.top || h.top>vv.bottom) return null;
  if (t.bottom<pv.top || t.top>pv.bottom) return null;
  return {a:{x:h.right,y:h.top+h.height/2}, b:{x:t.left,y:t.top+t.height/2}};
}
function redraw(){
  const p = active!=null && partnerPts(active);
  if (!p){ svg.innerHTML=""; return; }
  const dx = Math.max(40, (p.b.x-p.a.x)*0.4);
  svg.innerHTML = `<path d="M ${p.a.x} ${p.a.y} C ${p.a.x+dx} ${p.a.y}, ${p.b.x-dx} ${p.b.y}, ${p.b.x} ${p.b.y}" stroke="${cvar(LINKS[active]||0)}"/>`;
}
function schedule(){ if (active!=null && !raf) raf = requestAnimationFrame(()=>{ raf=0; redraw(); }); }
function focus(id){
  active = id; $(".app").classList.add("focused");
  document.querySelectorAll(`[data-link="${id}"]`).forEach(e=>e.classList.add("active"));
  redraw();
}
function blur(){
  active = null; $(".app").classList.remove("focused");
  document.querySelectorAll(".active").forEach(e=>e.classList.remove("active"));
  svg.innerHTML = "";
}
document.addEventListener("mouseover", e=>{ const el=e.target.closest("[data-link]"); if (el) focus(el.dataset.link); });
document.addEventListener("mouseout",  e=>{ const el=e.target.closest("[data-link]"); if (el && !el.contains(e.relatedTarget)) blur(); });
viewer.addEventListener("scroll", schedule, {passive:true});
$("#panel").addEventListener("scroll", schedule, {passive:true});
msgs.addEventListener("scroll", schedule, {passive:true});
addEventListener("resize", schedule);

/* ---------- simplify stream ---------- */
async function runSimplify(text){
  out.innerHTML = ""; Object.keys(LINKS).forEach(k=>delete LINKS[k]);
  chat("sys", "Simplifying the notice…");
  const resp = await fetch("/simplify", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({text})});
  const reader = resp.body.getReader(), dec = new TextDecoder(); let buf = "";
  while (true){
    const {value, done} = await reader.read(); if (done) break;
    buf += dec.decode(value, {stream:true}); let nl;
    while ((nl = buf.indexOf("\n")) >= 0){
      const line = buf.slice(0,nl).trim(); buf = buf.slice(nl+1);
      if (!line) continue;
      const rec = JSON.parse(line);
      if (rec.error){ chat("sys","Error: "+rec.error+" — is `ollama serve` running?"); return; }
      if (rec.done){ chat("sys", `Done — ${rec.sections} sections, ${rec.seconds}s of model time.`); return; }
      addCard(rec);
    }
  }
}
function addCard(rec){
  const c = cvar(rec.idx);
  const card = document.createElement("div"); card.className = "card"; card.style.setProperty("--c", c);
  let html = `<h3>${esc(rec.header)}</h3>`;
  for (const b of rec.bullets){
    if (b.verified && paint(b.source, b.id, rec.idx))
      html += `<div class="bullet link" data-link="${b.id}" style="--c:${c}">${esc(b.text)}</div>`;
    else
      html += `<div class="bullet nolink" title="not traceable to the source — unverified">${esc(b.text)}</div>`;
  }
  if (rec.numbers.length){
    html += `<div class="chips">`;
    for (const n of rec.numbers)
      html += paint(n.value, n.id, rec.idx)
        ? `<span class="chip link" data-link="${n.id}" style="--c:${c}">${esc(n.value)}</span>`
        : `<span class="chip" style="--c:${c};opacity:.6" title="not found in source">${esc(n.value)}</span>`;
    html += `</div>`;
  }
  if (rec.jargon.length) html += `<div class="jargon">⚠ jargon survived: ${esc(rec.jargon.join(", "))}</div>`;
  card.innerHTML = html; out.appendChild(card);
  // paint() ran before the .link nodes existed in the DOM; the highlights carry data-link,
  // and the panel nodes we just inserted carry the same — hover matches them up. No repaint needed.
}

/* ---------- upload / sample / ask ---------- */
async function load(data){
  const text = await renderPdf(data);
  await runSimplify(text);
}
$("#file").onchange = async e => {
  const f = e.target.files[0]; if (!f) return;
  chat("user", "📄 "+esc(f.name));
  load(new Uint8Array(await f.arrayBuffer()));
};
$("#send").onclick = ask; $("#q").addEventListener("keydown", e=>{ if (e.key==="Enter") ask(); });
async function ask(){
  const q = $("#q").value.trim(); if (!q) return;
  if (!DOC_TEXT){ chat("sys","Upload a notice first."); return; }
  $("#q").value = ""; chat("user", esc(q));
  const pending = chat("bot", "…");
  try {
    const r = await (await fetch("/ask", {method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({question:q, doc_text:DOC_TEXT})})).json();
    pending.remove();
    const id = "q"+Date.now();
    let ok = false;
    if (r.verified) ok = paint(r.source, id, 3);   // purple wire for answers
    const bub = chat(ok ? "bot link" : "bot", esc(r.answer) + (r.source ? `<span class="cite">“${esc(r.source)}”</span>` : ""));
    if (ok){ bub.dataset.link = id; bub.classList.add("link"); }
  } catch(err){ pending.remove(); chat("sys","Error: "+err.message); }
}

chat("sys","Upload a benefits notice (PDF) to get started.");
</script>
</body></html>
""".replace("MODEL_SLOT", MODEL)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode("utf-8"))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE)
        elif self.path.startswith("/static/"):
            name = os.path.basename(self.path)
            fp = os.path.join(STATIC, name)
            if os.path.isfile(fp):
                with open(fp, "rb") as f:
                    self._send(200, "application/javascript", f.read())
            else:
                self._send(404, "text/plain", "not found")
        elif self.path == "/sample.pdf":
            ensure_sample_pdf()
            with open(SAMPLE_PDF, "rb") as f:
                self._send(200, "application/pdf", f.read())
        else:
            self._send(404, "text/plain", "not found")

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_POST(self):
        if self.path == "/simplify":
            req = self._body()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.end_headers()
            try:
                for rec in simplify_sections(req.get("text", "")):
                    self.wfile.write((json.dumps(rec) + "\n").encode("utf-8"))
                    self.wfile.flush()
            except Exception as e:  # Ollama down / model missing — surface it to the page
                self.wfile.write((json.dumps({"error": str(e)}) + "\n").encode("utf-8"))
        elif self.path == "/ask":
            req = self._body()
            try:
                ans = answer_question(req.get("question", ""), req.get("doc_text", ""))
            except Exception as e:
                ans = {"answer": f"Error: {e}", "source": "", "verified": False}
            self._send(200, "application/json", json.dumps(ans))
        else:
            self._send(404, "text/plain", "not found")

    def log_message(self, *args):
        pass  # quiet console during the demo


if __name__ == "__main__":
    ensure_sample_pdf()
    print(f"Serving on http://localhost:{PORT}  (model={MODEL}, domain={NOUN})")
    print("Open it in a browser, then upload a benefits notice (PDF).")
    ThreadingHTTPServer(("localhost", PORT), Handler).serve_forever()
