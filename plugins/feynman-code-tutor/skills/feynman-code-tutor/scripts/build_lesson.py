#!/usr/bin/env python3
"""Build a self-contained Feynman dossier (single HTML file) from lesson.json.

Usage:
    python3 build_lesson.py lesson.json -o feynman-<system>.html

The script owns every piece of interactive machinery -- gating, jargon detection,
progress tracking, language switching, the final report -- so authors only ever
write content. See references/lesson-schema.md for the contract.
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

ERRORS = []


def err(path, msg):
    ERRORS.append(f"  {path}: {msg}")


def need(obj, key, path, kind="object"):
    if not isinstance(obj, dict) or key not in obj:
        err(f"{path}.{key}", f"missing required {kind}")
        return None
    return obj[key]


def check_bi(val, path, langs):
    """A bilingual object must have a non-empty string for every language."""
    if not isinstance(val, dict):
        err(path, f"expected a bilingual object like {{'en': '...', 'es': '...'}}, got {type(val).__name__}")
        return
    for lg in langs:
        if lg not in val:
            err(path, f"missing language '{lg}'")
        elif not isinstance(val[lg], str) or not val[lg].strip():
            err(f"{path}.{lg}", "must be a non-empty string")


ANCHOR_RE = re.compile(r"^[\w./\\-]+:\d+(-\d+)?$")


def check_anchor(val, path):
    if not isinstance(val, str) or not ANCHOR_RE.match(val.strip()):
        err(path, f"anchor must look like 'src/file.py:42' or 'src/file.py:12-40', got {val!r}")


def validate(data):
    langs = data.get("meta", {}).get("languages") or ["en", "es"]

    meta = need(data, "meta", "$")
    if isinstance(meta, dict):
        for k in ("title", "subtitle"):
            if k in meta:
                check_bi(meta[k], f"$.meta.{k}", langs)
            else:
                err(f"$.meta.{k}", "missing required bilingual object")
        if not meta.get("system_name"):
            err("$.meta.system_name", "missing required string")

    ori = need(data, "orientation", "$")
    if isinstance(ori, dict):
        for k in ("problem", "what_was_built"):
            check_bi(ori.get(k), f"$.orientation.{k}", langs)
        for i, f in enumerate(ori.get("files") or []):
            if not f.get("path"):
                err(f"$.orientation.files[{i}].path", "missing")
            check_bi(f.get("role"), f"$.orientation.files[{i}].role", langs)
        if not (ori.get("dataflow") or []):
            err("$.orientation.dataflow", "trace at least one input through the system")
        for i, s in enumerate(ori.get("dataflow") or []):
            check_bi(s.get("step"), f"$.orientation.dataflow[{i}].step", langs)
            check_anchor(s.get("anchor"), f"$.orientation.dataflow[{i}].anchor")
        for i, d in enumerate(ori.get("decisions") or []):
            for k in ("choice", "why", "instead_of"):
                check_bi(d.get(k), f"$.orientation.decisions[{i}].{k}", langs)

    check_bi(data.get("prior_knowledge_prompt"), "$.prior_knowledge_prompt", langs)

    concepts = data.get("concepts") or []
    if not 1 <= len(concepts) <= 9:
        err("$.concepts", f"expected 3-7 load-bearing concepts, got {len(concepts)}")
    seen_ids = set()
    for i, c in enumerate(concepts):
        p = f"$.concepts[{i}]"
        cid = c.get("id")
        if not cid or not re.match(r"^[a-z0-9-]+$", str(cid)):
            err(f"{p}.id", "missing or not a lowercase-hyphen slug")
        elif cid in seen_ids:
            err(f"{p}.id", f"duplicate id {cid!r}")
        else:
            seen_ids.add(cid)
        for k in ("name", "one_liner", "simple_explanation"):
            check_bi(c.get(k), f"{p}.{k}", langs)
        bt = c.get("banned_terms")
        if not isinstance(bt, list) or not bt:
            err(f"{p}.banned_terms", "list the jargon this concept lets the learner hide behind")
        ana = c.get("analogy") or {}
        check_bi(ana.get("text"), f"{p}.analogy.text", langs)
        check_bi(ana.get("breaks_down"), f"{p}.analogy.breaks_down", langs)
        gqs = c.get("gap_questions") or []
        if len(gqs) < 2:
            err(f"{p}.gap_questions", f"expected 3-5 questions, got {len(gqs)}")
        for j, g in enumerate(gqs):
            check_bi(g.get("q"), f"{p}.gap_questions[{j}].q", langs)
            check_bi(g.get("a"), f"{p}.gap_questions[{j}].a", langs)
            check_anchor(g.get("anchor"), f"{p}.gap_questions[{j}].anchor")
        sen = c.get("senior") or {}
        for k in ("tradeoff", "cost_complexity", "at_scale"):
            check_bi(sen.get(k), f"{p}.senior.{k}", langs)
        for j, fm in enumerate(sen.get("failure_modes") or []):
            for k in ("mode", "symptom", "mitigation"):
                check_bi(fm.get(k), f"{p}.senior.failure_modes[{j}].{k}", langs)
        if not (sen.get("failure_modes") or []):
            err(f"{p}.senior.failure_modes", "name at least one way this fails in production")
        for j, alt in enumerate(sen.get("alternatives") or []):
            for k in ("option", "why_not"):
                check_bi(alt.get(k), f"{p}.senior.alternatives[{j}].{k}", langs)

    rb = need(data, "rebuild", "$")
    if isinstance(rb, dict):
        check_bi(rb.get("spec"), "$.rebuild.spec", langs)
        for i, c in enumerate(rb.get("constraints") or []):
            check_bi(c, f"$.rebuild.constraints[{i}]", langs)
        ms = rb.get("milestones") or []
        if len(ms) < 3:
            err("$.rebuild.milestones", f"expected 4-8 milestones, got {len(ms)}")
        for i, m in enumerate(ms):
            for k in ("title", "goal", "acceptance", "hint"):
                check_bi(m.get(k), f"$.rebuild.milestones[{i}].{k}", langs)
        at = rb.get("acceptance_tests") or {}
        if not at.get("code"):
            err("$.rebuild.acceptance_tests.code", "the learner needs a test they can actually run")
        if not (rb.get("reference_solution") or []):
            err("$.rebuild.reference_solution", "include the real source, locked behind the rebuild gate")
        for i, s in enumerate(rb.get("reference_solution") or []):
            if not s.get("path") or not s.get("code"):
                err(f"$.rebuild.reference_solution[{i}]", "needs both 'path' and 'code'")
        for i, d in enumerate(rb.get("diff_prompts") or []):
            check_bi(d, f"$.rebuild.diff_prompts[{i}]", langs)

    sb = need(data, "senior_brief", "$")
    if isinstance(sb, dict):
        check_bi(sb.get("architecture_summary"), "$.senior_brief.architecture_summary", langs)
        for i, q in enumerate(sb.get("review_questions") or []):
            check_bi(q.get("q"), f"$.senior_brief.review_questions[{i}].q", langs)
            check_bi(q.get("a"), f"$.senior_brief.review_questions[{i}].a", langs)

    for i, f in enumerate(data.get("flashcards") or []):
        check_bi(f.get("front"), f"$.flashcards[{i}].front", langs)
        check_bi(f.get("back"), f"$.flashcards[{i}].back", langs)
    for i, n in enumerate(data.get("next_steps") or []):
        check_bi(n, f"$.next_steps[{i}]", langs)

    return langs


# --------------------------------------------------------------------------
# tiny markdown
# --------------------------------------------------------------------------

BULLET = r"^\s*[-*]\s+"
NUMBERED = r"^\s*\d+[.)]\s+"


def _inline(text):
    out = html.escape(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


def md(text):
    """Paragraphs, bullets, numbered lists, fenced code. Nothing more."""
    if not text:
        return ""
    blocks, fence, buf, lang = [], False, [], ""
    for line in str(text).split("\n"):
        m = re.match(r"^```(\w*)\s*$", line)
        if m and not fence:
            if buf:
                blocks.append(("text", "\n".join(buf)))
                buf = []
            fence, lang = True, m.group(1)
            continue
        if line.strip() == "```" and fence:
            blocks.append(("code", "\n".join(buf), lang))
            buf, fence, lang = [], False, ""
            continue
        buf.append(line)
    if buf:
        blocks.append(("code", "\n".join(buf), lang) if fence else ("text", "\n".join(buf)))

    parts = []
    for b in blocks:
        if b[0] == "code":
            cls = f' class="lang-{b[2]}"' if len(b) > 2 and b[2] else ""
            parts.append(f'<pre><code{cls}>{html.escape(b[1])}</code></pre>')
            continue
        for para in re.split(r"\n\s*\n", b[1]):
            para = para.strip("\n")
            if not para.strip():
                continue
            lines = [l for l in para.split("\n") if l.strip()]
            if all(re.match(BULLET, l) for l in lines):
                items = "".join("<li>" + _inline(re.sub(BULLET, "", l)) + "</li>" for l in lines)
                parts.append(f"<ul>{items}</ul>")
            elif all(re.match(NUMBERED, l) for l in lines):
                items = "".join("<li>" + _inline(re.sub(NUMBERED, "", l)) + "</li>" for l in lines)
                parts.append(f"<ol>{items}</ol>")
            else:
                parts.append("<p>" + "<br>".join(_inline(l) for l in lines) + "</p>")
    return "".join(parts)


# --------------------------------------------------------------------------
# bilingual rendering
# --------------------------------------------------------------------------

LANGS = ["en", "es"]


def bi(obj, tag="div", cls="", inline=False):
    """Render one block per language; CSS shows only the active one."""
    if obj is None:
        return ""
    if isinstance(obj, str):
        obj = {lg: obj for lg in LANGS}
    out = []
    for lg in LANGS:
        body = html.escape(obj.get(lg, "")) if inline else md(obj.get(lg, ""))
        out.append(f'<{tag} class="lb {cls}" data-lang="{lg}">{body}</{tag}>')
    return "".join(out)


def bis(obj, cls=""):
    return bi(obj, tag="span", cls=cls, inline=True)


def anchor(a):
    return f'<span class="anchor" title="source">{html.escape(str(a))}</span>' if a else ""


UI = {
    "orientation": {"en": "What the AI built", "es": "Qué construyó la IA"},
    "blank": {"en": "The blank page", "es": "La hoja en blanco"},
    "concepts": {"en": "The load-bearing ideas", "es": "Las ideas que sostienen todo"},
    "rebuild": {"en": "Rebuild it yourself", "es": "Reconstruilo vos"},
    "senior": {"en": "Senior register", "es": "Registro senior"},
    "report": {"en": "Report", "es": "Informe"},
    "locked": {"en": "Locked", "es": "Bloqueado"},
    "problem": {"en": "The problem", "es": "El problema"},
    "built": {"en": "What was built", "es": "Qué se construyó"},
    "files": {"en": "The map", "es": "El mapa"},
    "dataflow": {"en": "One input, all the way through", "es": "Un input, de punta a punta"},
    "decisions": {"en": "Decisions you would not guess from the code",
                  "es": "Decisiones que no adivinarías leyendo el código"},
    "instead_of": {"en": "instead of", "es": "en vez de"},
    "yourturn": {"en": "Your turn", "es": "Te toca"},
    "explain_prompt": {"en": "Explain this to a smart 12-year-old. Plain words only.",
                       "es": "Explicá esto a un chico de 12 años. Solo palabras comunes."},
    "banned_hit": {"en": "You are hiding behind jargon:", "es": "Te estás escondiendo detrás de jerga:"},
    "banned_help": {
        "en": "These words are not banned to annoy you. Each one is a box you have not opened. Say what physically happens instead.",
        "es": "Estas palabras no están prohibidas para molestarte. Cada una es una caja que no abriste. Decí qué pasa realmente en su lugar."},
    "words": {"en": "words", "es": "palabras"},
    "need_words": {"en": "need", "es": "faltan"},
    "submit": {"en": "Submit and compare", "es": "Enviar y comparar"},
    "reference": {"en": "The reference explanation", "es": "La explicación de referencia"},
    "your_analogy": {"en": "Now forge your own analogy", "es": "Ahora forjá tu propia analogía"},
    "analogy_prompt": {
        "en": "Finish the sentence: \"It is like...\" — and then say where your analogy breaks down.",
        "es": "Completá la frase: \"Es como...\" — y después decí dónde se rompe tu analogía."},
    "ref_analogy": {"en": "Reference analogy", "es": "Analogía de referencia"},
    "breaks": {"en": "Where it breaks down", "es": "Dónde se rompe"},
    "gaps": {"en": "Gap hunt", "es": "Caza de lagunas"},
    "gaps_help": {"en": "Answer from your head first. The source anchor is there so you can verify, not so you can copy.",
                  "es": "Contestá de memoria primero. El ancla al código está para que verifiques, no para que copies."},
    "reveal": {"en": "Check my answer", "es": "Ver la respuesta"},
    "spec": {"en": "The specification", "es": "La especificación"},
    "constraints": {"en": "Constraints", "es": "Restricciones"},
    "milestones": {"en": "Milestones", "es": "Hitos"},
    "acceptance": {"en": "Done when", "es": "Listo cuando"},
    "hint": {"en": "Nudge", "es": "Empujoncito"},
    "tests": {"en": "Run these against your own build", "es": "Corré esto contra tu propia versión"},
    "rebuild_notes": {"en": "What did you build, and what fought you?",
                      "es": "¿Qué construiste y qué se te resistió?"},
    "rebuild_notes_help": {
        "en": "Write it before you unlock the source. What you struggled with is the map of what you actually learned.",
        "es": "Escribilo antes de desbloquear el código. Lo que te costó es el mapa de lo que de verdad aprendiste."},
    "unlock_source": {"en": "Unlock the original source", "es": "Desbloquear el código original"},
    "original": {"en": "The original source", "es": "El código original"},
    "diff": {"en": "Diff your thinking", "es": "Compará tu razonamiento"},
    "diff_help": {
        "en": "Not every difference is a mistake. Sometimes yours is better — say so when it is.",
        "es": "No toda diferencia es un error. A veces la tuya es mejor — decilo cuando lo sea."},
    "tradeoff": {"en": "Tradeoff taken", "es": "Trade-off asumido"},
    "failure": {"en": "Failure modes", "es": "Modos de falla"},
    "symptom": {"en": "Looks like", "es": "Se ve así"},
    "mitigation": {"en": "Mitigation", "es": "Mitigación"},
    "cost": {"en": "Cost and complexity", "es": "Costo y complejidad"},
    "scale": {"en": "At 100x", "es": "A 100x"},
    "alts": {"en": "Alternatives not taken", "es": "Alternativas descartadas"},
    "whynot": {"en": "Why not", "es": "Por qué no"},
    "arch": {"en": "The system at staff level", "es": "El sistema a nivel staff"},
    "reviewq": {"en": "Design review questions", "es": "Preguntas de design review"},
    "flash": {"en": "Worth memorising", "es": "Vale la pena memorizar"},
    "flip": {"en": "Flip", "es": "Dar vuelta"},
    "next": {"en": "Where to go next", "es": "Qué sigue"},
    "breakglass": {"en": "Break glass (marks this UNVERIFIED)",
                   "es": "Romper el vidrio (queda marcado SIN VERIFICAR)"},
    "locked_msg": {"en": "This section unlocks when the work above is done.",
                   "es": "Esta sección se abre cuando termines lo de arriba."},
    "verified": {"en": "VERIFIED", "es": "VERIFICADO"},
    "unverified": {"en": "UNVERIFIED", "es": "SIN VERIFICAR"},
    "incomplete": {"en": "NOT STARTED", "es": "SIN EMPEZAR"},
    "report_intro": {
        "en": "An honest record of what you have actually reconstructed. Anything marked UNVERIFIED is next week's agenda.",
        "es": "Un registro honesto de lo que realmente reconstruiste. Todo lo marcado SIN VERIFICAR es la agenda de la semana que viene."},
    "copy_report": {"en": "Copy report", "es": "Copiar informe"},
    "teach": {
        "en": "Final act: close this file and explain the whole system out loud in five sentences, with no jargon. If you stall, you have found your next gap.",
        "es": "Acto final: cerrá este archivo y explicá el sistema entero en voz alta en cinco oraciones, sin jerga. Si te trabás, encontraste tu próxima laguna."},
}


PLACEHOLDERS = {
    "blank": {
        "en": "Start with \"I think it works like this...\" and keep going. Mark anything you are unsure of with a ? — those marks are the point.",
        "es": "Arrancá con \"creo que funciona así...\" y seguí. Marcá con ? todo lo que no tengas seguro — esas marcas son justamente el punto.",
    },
    "exp": {
        "en": "When someone asks a question, the program first...",
        "es": "Cuando alguien hace una pregunta, el programa primero...",
    },
    "gap": {
        "en": "From memory. No scrolling up.",
        "es": "De memoria. Sin subir a mirar.",
    },
    "ana": {
        "en": "It is like... and it breaks down when...",
        "es": "Es como... y se rompe cuando...",
    },
    "notes": {
        "en": "What you built, in what order, and the exact point where you got stuck.",
        "es": "Qué construiste, en qué orden y el punto exacto donde te trabaste.",
    },
}


def ph(key):
    """Bilingual placeholder as data attributes; the runtime swaps them on toggle."""
    d = PLACEHOLDERS[key]
    return " ".join(f'data-ph-{lg}="{html.escape(d.get(lg, d["en"]), quote=True)}"' for lg in LANGS)


def u(key):
    return bis(UI[key])


# --------------------------------------------------------------------------
# section renderers
# --------------------------------------------------------------------------

def render_orientation(o):
    files = "".join(
        f'<li><span class="path">{html.escape(f["path"])}</span>{bi(f["role"], "div", "role")}</li>'
        for f in (o.get("files") or [])
    )
    flow = "".join(
        f'<li><span class="num">{i+1}</span><div class="flowbody">{bi(s["step"])}{anchor(s.get("anchor"))}</div></li>'
        for i, s in enumerate(o.get("dataflow") or [])
    )
    decs = "".join(
        f'<div class="decision"><div class="dhead">{bi(d["choice"], "div", "choice")}'
        f'<div class="dinstead">{u("instead_of")} {bi(d["instead_of"], "span", "", True)}</div></div>'
        f'{bi(d["why"])}{anchor(d.get("anchor"))}</div>'
        for d in (o.get("decisions") or [])
    )
    return f"""
<section id="orientation" class="sec open" data-sec="orientation">
  <h2><span class="secnum">00</span>{u('orientation')}</h2>
  <div class="card"><h3>{u('problem')}</h3>{bi(o['problem'])}</div>
  <div class="card"><h3>{u('built')}</h3>{bi(o['what_was_built'])}</div>
  {f'<div class="card"><h3>{UI_files()}</h3><ul class="filelist">{files}</ul></div>' if files else ''}
  {f'<div class="card"><h3>{bis(UI["dataflow"])}</h3><ol class="flow">{flow}</ol></div>' if flow else ''}
  {f'<div class="card"><h3>{bis(UI["decisions"])}</h3>{decs}</div>' if decs else ''}
</section>"""


def UI_files():
    return bis(UI["files"])


def render_blank(prompt):
    return f"""
<section id="blank" class="sec open" data-sec="blank">
  <h2><span class="secnum">01</span>{u('blank')}</h2>
  <div class="card">
    {bi(prompt)}
    <textarea class="ta" data-key="blank" data-min="60" {ph("blank")}></textarea>
    <div class="meter"><span class="wc" data-for="blank">0</span> {u('words')}
      <span class="short" data-for="blank"></span></div>
  </div>
</section>"""


def render_concepts(concepts):
    cards = []
    for i, c in enumerate(concepts):
        cid = c["id"]
        banned = json.dumps(c["banned_terms"])
        gaps = "".join(f"""
      <div class="gap">
        <div class="q">{bi(g['q'])}</div>
        <textarea class="ta small" data-key="{cid}.gap{j}" data-min="8" {ph("gap")}></textarea>
        <button class="btn ghost" data-reveal="{cid}.gap{j}">{u('reveal')}</button>
        <div class="revealbox" id="rev-{cid}-gap{j}">{bi(g['a'])}{anchor(g.get('anchor'))}</div>
      </div>""" for j, g in enumerate(c["gap_questions"]))

        sen = c["senior"]
        fails = "".join(
            f'<div class="fm"><div class="fmhead">{bi(f["mode"], "div", "mode")}</div>'
            f'<div class="fmrow"><b>{bis(UI["symptom"])}</b>{bi(f["symptom"])}</div>'
            f'<div class="fmrow"><b>{bis(UI["mitigation"])}</b>{bi(f["mitigation"])}</div></div>'
            for f in sen.get("failure_modes") or [])
        alts = "".join(
            f'<div class="alt">{bi(a["option"], "div", "optname")}'
            f'<div class="fmrow"><b>{bis(UI["whynot"])}</b>{bi(a["why_not"])}</div></div>'
            for a in sen.get("alternatives") or [])

        cards.append(f"""
  <article class="concept" data-cid="{cid}" data-banned='{banned}'>
    <header class="chead">
      <span class="cnum">{i+1:02d}</span>
      <div><h3>{bis(c['name'])}</h3>{bi(c['one_liner'], 'div', 'oneliner')}</div>
      <span class="badge" data-badge="{cid}"></span>
    </header>

    <div class="stage">
      <h4>{u('yourturn')}</h4>
      {bi(UI['explain_prompt'])}
      <textarea class="ta" data-key="{cid}.exp" data-min="40" data-banned-check="1" {ph("exp")}></textarea>
      <div class="meter"><span class="wc" data-for="{cid}.exp">0</span> {u('words')}
        <span class="short" data-for="{cid}.exp"></span></div>
      <div class="jargon" data-for="{cid}.exp"></div>
      <button class="btn" data-submit="{cid}.exp">{u('submit')}</button>
      <button class="btn glass" data-glass="{cid}">{u('breakglass')}</button>
      <div class="revealbox" id="rev-{cid}-exp">
        <h4>{u('reference')}</h4>
        {bi(c['simple_explanation'])}
        <div class="analogyzone">
          <h4>{u('your_analogy')}</h4>
          {bi(UI['analogy_prompt'])}
          <textarea class="ta small" data-key="{cid}.ana" data-min="15" {ph("ana")}></textarea>
          <button class="btn ghost" data-reveal="{cid}.ana">{u('ref_analogy')}</button>
          <div class="revealbox" id="rev-{cid}-ana">
            {bi(c['analogy']['text'])}
            <div class="breaks"><b>{bis(UI['breaks'])}</b>{bi(c['analogy']['breaks_down'])}</div>
          </div>
        </div>
        <div class="gapzone">
          <h4>{u('gaps')}</h4>
          <div class="hint">{bi(UI['gaps_help'])}</div>
          {gaps}
        </div>
      </div>
    </div>

    <div class="seniorzone" data-senior="{cid}">
      <div class="srow"><b>{bis(UI['tradeoff'])}</b>{bi(sen['tradeoff'])}</div>
      <div class="srow"><b>{bis(UI['failure'])}</b>{fails}</div>
      <div class="srow"><b>{bis(UI['cost'])}</b>{bi(sen['cost_complexity'])}</div>
      <div class="srow"><b>{bis(UI['scale'])}</b>{bi(sen['at_scale'])}</div>
      {f'<div class="srow"><b>{bis(UI["alts"])}</b>{alts}</div>' if alts else ''}
    </div>
  </article>""")

    return f"""
<section id="concepts" class="sec" data-sec="concepts">
  <h2><span class="secnum">02</span>{u('concepts')}</h2>
  <div class="lockmsg">{bi(UI['locked_msg'])}<button class="btn glass" data-glass="sec:concepts">{u('breakglass')}</button></div>
  <div class="secbody">{''.join(cards)}</div>
</section>"""


def render_rebuild(rb):
    cons = "".join(f"<li>{bi(c, 'div')}</li>" for c in (rb.get("constraints") or []))
    ms = "".join(f"""
    <li class="ms">
      <label><input type="checkbox" data-ms="{i}"><span>{bis(m['title'])}</span></label>
      <div class="msbody">
        {bi(m['goal'])}
        <div class="acc"><b>{bis(UI['acceptance'])}</b>{bi(m['acceptance'], 'span', '', True)}</div>
        <details><summary>{bis(UI['hint'])}</summary>{bi(m['hint'])}</details>
      </div>
    </li>""" for i, m in enumerate(rb.get("milestones") or []))

    at = rb.get("acceptance_tests") or {}
    tests = ""
    if at.get("code"):
        tests = (f'<div class="card"><h3>{bis(UI["tests"])}</h3>'
                 f'<div class="filename">{html.escape(at.get("filename", "tests"))}</div>'
                 f'<pre><code>{html.escape(at["code"])}</code></pre></div>')

    sol = "".join(
        f'<div class="srcfile"><div class="filename">{html.escape(s["path"])}</div>'
        f'<pre><code>{html.escape(s["code"])}</code></pre></div>'
        for s in (rb.get("reference_solution") or []))
    diffs = "".join(f"<li>{bi(d, 'div')}</li>" for d in (rb.get("diff_prompts") or []))

    return f"""
<section id="rebuild" class="sec" data-sec="rebuild">
  <h2><span class="secnum">03</span>{u('rebuild')}</h2>
  <div class="lockmsg">{bi(UI['locked_msg'])}<button class="btn glass" data-glass="sec:rebuild">{u('breakglass')}</button></div>
  <div class="secbody">
    <div class="card"><h3>{u('spec')}</h3>{bi(rb['spec'])}</div>
    {f'<div class="card"><h3>{bis(UI["constraints"])}</h3><ul class="cons">{cons}</ul></div>' if cons else ''}
    <div class="card"><h3>{u('milestones')}</h3><ol class="mslist">{ms}</ol></div>
    {tests}
    <div class="card">
      <h3>{u('rebuild_notes')}</h3>
      <div class="hint">{bi(UI['rebuild_notes_help'])}</div>
      <textarea class="ta" data-key="rebuild.notes" data-min="80" {ph("notes")}></textarea>
      <div class="meter"><span class="wc" data-for="rebuild.notes">0</span> {u('words')}
        <span class="short" data-for="rebuild.notes"></span></div>
      <button class="btn" data-submit="rebuild.notes">{u('unlock_source')}</button>
      <button class="btn glass" data-glass="rebuild">{u('breakglass')}</button>
    </div>
    <div class="revealbox" id="rev-rebuild-notes">
      <div class="card"><h3>{u('original')}</h3>{sol}</div>
      {f'<div class="card"><h3>{bis(UI["diff"])}</h3><div class="hint">{bi(UI["diff_help"])}</div><ul class="cons">{diffs}</ul></div>' if diffs else ''}
    </div>
  </div>
</section>"""


def render_senior(sb, flashcards, next_steps):
    qs = "".join(f"""
    <div class="gap">
      <div class="q">{bi(q['q'])}</div>
      <button class="btn ghost" data-reveal="rq{i}">{u('reveal')}</button>
      <div class="revealbox" id="rev-rq{i}">{bi(q['a'])}</div>
    </div>""" for i, q in enumerate(sb.get("review_questions") or []))

    cards = "".join(
        f'<div class="flashcard" tabindex="0"><div class="front">{bi(f["front"])}</div>'
        f'<div class="back">{bi(f["back"])}</div></div>'
        for f in (flashcards or []))
    nxt = "".join(f"<li>{bi(n, 'div')}</li>" for n in (next_steps or []))

    return f"""
<section id="senior" class="sec" data-sec="senior">
  <h2><span class="secnum">04</span>{u('senior')}</h2>
  <div class="lockmsg">{bi(UI['locked_msg'])}<button class="btn glass" data-glass="sec:senior">{u('breakglass')}</button></div>
  <div class="secbody">
    <div class="card"><h3>{u('arch')}</h3>{bi(sb['architecture_summary'])}</div>
    {f'<div class="card"><h3>{bis(UI["reviewq"])}</h3>{qs}</div>' if qs else ''}
    {f'<div class="card"><h3>{bis(UI["flash"])}</h3><div class="flashgrid">{cards}</div></div>' if cards else ''}
    {f'<div class="card"><h3>{bis(UI["next"])}</h3><ul class="cons">{nxt}</ul></div>' if nxt else ''}
  </div>
</section>"""


def render_report():
    return f"""
<section id="report" class="sec open" data-sec="report">
  <h2><span class="secnum">05</span>{u('report')}</h2>
  <div class="card">
    {bi(UI['report_intro'])}
    <div id="reportbody"></div>
    <button class="btn" id="copyreport">{u('copy_report')}</button>
  </div>
  <div class="card final">{bi(UI['teach'])}</div>
</section>"""


# --------------------------------------------------------------------------
# assets
# --------------------------------------------------------------------------

CSS = Path(__file__).parent.parent / "assets" / "dossier.css"
JS = Path(__file__).parent.parent / "assets" / "dossier.js"


def build(data, langs):
    global LANGS
    LANGS = langs
    meta = data["meta"]
    default_lang = meta.get("default_lang", langs[0])

    nav = "".join(
        f'<a href="#{sid}" data-nav="{sid}"><span class="dot"></span>{bis(UI[key])}</a>'
        for sid, key in [("orientation", "orientation"), ("blank", "blank"), ("concepts", "concepts"),
                         ("rebuild", "rebuild"), ("senior", "senior"), ("report", "report")])

    langbtns = "".join(
        f'<button class="langbtn" data-setlang="{lg}">{lg.upper()}</button>' for lg in langs)

    concept_ids = json.dumps([c["id"] for c in data["concepts"]])
    gap_counts = json.dumps({c["id"]: len(c["gap_questions"]) for c in data["concepts"]})
    ms_count = len(data["rebuild"].get("milestones") or [])
    names = json.dumps({c["id"]: c["name"] for c in data["concepts"]})

    body = "".join([
        render_orientation(data["orientation"]),
        render_blank(data["prior_knowledge_prompt"]),
        render_concepts(data["concepts"]),
        render_rebuild(data["rebuild"]),
        render_senior(data["senior_brief"], data.get("flashcards"), data.get("next_steps")),
        render_report(),
    ])

    css = CSS.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    cfg = json.dumps({
        "conceptIds": json.loads(concept_ids),
        "gapCounts": json.loads(gap_counts),
        "msCount": ms_count,
        "names": json.loads(names),
        "langs": langs,
        "defaultLang": default_lang,
        "systemName": meta.get("system_name", "system"),
        "ui": {k: UI[k] for k in ("verified", "unverified", "incomplete", "banned_hit", "need_words")},
    }, ensure_ascii=False)

    title_plain = meta["title"].get(default_lang, "")
    return f"""<!doctype html>
<html lang="{default_lang}" data-lang="{default_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title_plain)}</title>
<style>{css}</style>
</head>
<body data-lang="{default_lang}">
<header class="topbar">
  <div class="brand">
    <div class="titles"><h1>{bis(meta['title'])}</h1>{bi(meta['subtitle'], 'div', 'sub')}</div>
  </div>
  <div class="controls">
    <div class="progresswrap"><div class="progressbar"><i id="pbar"></i></div><span id="ppct">0%</span></div>
    <div class="langswitch">{langbtns}</div>
    <button class="iconbtn" id="themebtn" title="theme" aria-label="theme"><svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M8 1.5a6.5 6.5 0 0 1 0 13z" fill="currentColor"/></svg></button>
  </div>
</header>
<div class="layout">
  <nav class="sidenav">{nav}</nav>
  <main>{body}</main>
</div>
<script>const CFG = {cfg};</script>
<script>{js}</script>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(description="Build a Feynman dossier from lesson.json")
    ap.add_argument("lesson")
    ap.add_argument("-o", "--output", default=None)
    args = ap.parse_args()

    try:
        data = json.loads(Path(args.lesson).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"lesson.json is not valid JSON: {e}")

    langs = validate(data)
    if ERRORS:
        sys.stderr.write(
            f"\nlesson.json has {len(ERRORS)} problem(s). Fix these and rerun:\n\n"
            + "\n".join(ERRORS) + "\n\nSee references/lesson-schema.md for the contract.\n")
        sys.exit(1)

    out = args.output or f"feynman-{data['meta'].get('system_name', 'system')}.html"
    Path(out).write_text(build(data, langs), encoding="utf-8")
    size = Path(out).stat().st_size / 1024
    print(f"Built {out} ({size:.0f} KB) — {len(data['concepts'])} concepts, "
          f"{len(data['rebuild'].get('milestones') or [])} milestones, langs: {', '.join(langs)}")


if __name__ == "__main__":
    main()
