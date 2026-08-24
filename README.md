# feynman-code-tutor

A Claude skill that turns code an AI wrote into a **learning dossier** — a single self-contained
HTML file that makes you rebuild the system from scratch instead of reading about it.

The premise, borrowed from Richard Feynman: if you cannot explain something in plain words, you do
not understand it. Reading generated code and following its logic feels like understanding. It
isn't — it's recognition, and the jargon is what keeps the illusion alive.

So this skill doesn't explain code well. Explaining it well is what *creates* the illusion. It
builds an instrument that **measures** your understanding and refuses to move until it's real.

**Success condition:** you can rebuild the system from a blank editor, with the dossier closed, and
defend every design decision in a review.

---

## What it produces

Two things, every time.

**1. The dossier** — one HTML file, no network, no dependencies, opens from anywhere. Six sections
that unlock in order:

| | section | what happens |
|---|---|---|
| 00 | **What the AI built** | File map, one input traced end to end, and the decisions you'd never guess from the code. Every claim anchored to `file.py:line` so you can verify instead of trusting. |
| 01 | **The blank page** | You dump what you think you know before reading anything. 60 words to continue. |
| 02 | **The load-bearing ideas** | 3–7 concepts. You write the twelve-year-old explanation first. A **jargon detector blocks submit** if you lean on the shield words (`embedding`, `vector`, `semantic`…). Then: your own analogy, then gap questions. |
| 03 | **Rebuild it yourself** | A spec, milestones, and **a real test file you run against your own code**. The original source stays locked until you've written your rebuild notes. |
| 04 | **Senior register** | Tradeoffs, failure modes, cost, behaviour at 100×, alternatives rejected and why. For the design review. |
| 05 | **Honest report** | Every section marked `VERIFIED` or `UNVERIFIED`. |

**2. A live Socratic tutor** — after handing over the file, Claude stays in character in the chat:
asks before it tells, breaks your wrong models with counterexamples instead of corrections, and
refuses to just write the code for you.

Bilingual throughout: **EN default, ES toggle**. Both languages are authored, not machine
translated, and analogies are re-chosen so they land in Spanish rather than being transliterated.

[`examples/doc-qa-dossier.html`](examples/doc-qa-dossier.html) is a complete generated dossier for a
small document-Q&A service. Download and open it — try typing "embedding" into the first box of
section 02.

## The lock policy

Sections unlock in order and the code stays hidden until you've rebuilt it. Reading the solution
first spends your one chance at retrieval, and retrieval is where the learning happens.

But it's a static HTML file — anyone can open dev tools. So it doesn't pretend to be a vault. Every
gate has a **break-glass** link that opens immediately and permanently stamps that section
`UNVERIFIED` in the report. You keep control, and you keep an honest record of which parts of the
system you never actually reconstructed. Those stamps are next week's study plan.

---

## Install

### Claude Code — personal skill

```bash
git clone https://github.com/jrobador/feynman-code-tutor.git
cd feynman-code-tutor
./install.sh
```

That copies the skill into `~/.claude/skills/feynman-code-tutor/`. Restart Claude Code. Use
`./install.sh --project` from inside another repo to install it there instead
(`.claude/skills/`), which is the right choice if you want it committed alongside a team codebase.

### Claude Code — as a plugin

```
/plugin marketplace add jrobador/feynman-code-tutor
/plugin install feynman-code-tutor@feynman-code-tutor
```

Updates then arrive through `/plugin`, which is easier to keep current than a copied folder.

### Claude.ai and Cowork

Zip the skill folder as `feynman-code-tutor.skill` and upload it, or use the release asset:

```bash
cd plugins/feynman-code-tutor/skills && zip -r ../../../feynman-code-tutor.skill feynman-code-tutor
```

---

## Using it

Just ask, in either language:

> explain what you just built — I want to be able to write it myself next time

> no entiendo el código que generaste, ayudame a estudiarlo en serio

> teach me this repo, I'm too dependent on AI

The skill reads the code, traces a real input through it, picks the load-bearing ideas, authors a
`lesson.json`, and builds the HTML:

```bash
python3 scripts/build_lesson.py lesson.json -o feynman-<system>.html
```

Only Python 3 — no packages to install.

## Authoring your own dossier by hand

`lesson.json` is the whole content contract; the build script owns every piece of interactive
machinery, so you never write HTML or JavaScript. Start from
[`assets/example-lesson.json`](plugins/feynman-code-tutor/skills/feynman-code-tutor/assets/example-lesson.json)
— it's a complete working dossier and shows the register the prose should be in, which no schema can
specify.

Reference docs live in
[`skills/feynman-code-tutor/references/`](plugins/feynman-code-tutor/skills/feynman-code-tutor/references):

- `lesson-schema.md` — the JSON contract, field by field
- `tutor-protocol.md` — how the live Socratic session runs
- `bilingual.md` — writing EN/ES pairs so both read as native
- `html-architecture.md` — what the template does and how to extend it

The validator reports missing fields by JSON path in plain language, so iterating is fast.

---

## Design notes

**No unanchored claims.** Every factual statement in the dossier points at `file.py:line`. This
isn't bureaucracy — a confident, plausible, wrong explanation is the worst thing this skill could
produce, and anchors are what let you catch one.

**Two registers, one truth.** The twelve-year-old version and the staff-engineer version describe
the same system. If they could not both be true, the simple one is a lie told for convenience.

**Analogies last.** An analogy you're handed is a souvenir. One you built is a hook into memory you
already have. So you forge yours first, then compare — and every reference analogy names where it
breaks down, because the learner who knows the seam is safe from over-extending it.

**Low word gates.** Thresholds exist to stop one-word bypasses, not to police length. A gate tuned
to force essays gets defeated by padding, which teaches padding.

## License

MIT
