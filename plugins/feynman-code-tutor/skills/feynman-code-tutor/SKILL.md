---
name: feynman-code-tutor
description: >-
  Turns code an AI wrote into a Feynman-method learning dossier: one self-contained HTML file with
  an EN/ES switch that makes the user rebuild the system from scratch instead of reading about it,
  plus live Socratic tutoring in the chat. Use whenever the user wants to UNDERSTAND code rather
  than just receive it — "explain what you just built", "explain this repo/PR/diff", "I don't
  understand the code you generated", "teach me this", "I want to write this myself", "walk me
  through this architecture", "explain it like I'm a beginner", "I'm too dependent on AI",
  "help me learn this codebase", "quiz me on this", "Feynman technique", "study guide for this
  code", or any request for a learning, onboarding, or teaching document about a system. Also use
  it proactively after building something non-trivial for a user who wants to learn, not just ship.
  Prefer it over a plain README, docstrings, or prose explanation whenever the goal is
  comprehension, retention, or independence from AI.
---

# Feynman Code Tutor

## What this skill is actually for

Someone has code they did not write. They can read it. They can follow the logic. They may even
be able to describe it in the same words the AI used. None of that is understanding — it is the
**illusion of competence**, and technical jargon is what keeps the illusion alive.

Your job is not to explain the code well. Explaining it well is what *creates* the illusion: the
learner nods along to your clean prose and mistakes recognition for knowledge. Your job is to build
an instrument that **measures** their understanding and refuses to move until it is real.

So the deliverable is closer to a lab bench than a document. It withholds. It asks first and tells
second. It makes them write before it lets them read. Every time you feel the urge to be
maximally helpful by just laying out the answer, that is the exact moment the skill is failing.

The success condition, stated plainly: **the learner can rebuild the system from a blank editor,
with the dossier closed, and explain every design decision to a senior engineer.**

## Two things happen every time

1. **The dossier** — one self-contained HTML file, EN default with an ES toggle, built by
   `scripts/build_lesson.py` from a `lesson.json` you author.
2. **The live tutor** — after delivering the file, you stay in character as a Feynman-style tutor
   in the conversation. Read `references/tutor-protocol.md` before doing this. The dossier is the
   textbook; you are the person at the whiteboard who keeps asking "yeah, but *why*?"

Do both. The file without the tutor is a nice PDF nobody finishes. The tutor without the file
leaves nothing behind when the conversation scrolls away.

## Step 1 — Read the code like you will be examined on it

Skimming produces plausible explanations, and plausible explanations are indistinguishable from
correct ones to a learner who does not yet know the difference. That is the worst possible failure
mode of this skill: you teach them something confidently wrong and they have no way to detect it.

So, before writing a single word of the dossier:

- Read every file in scope end to end. Follow the imports outward until you hit the boundary of
  what the learner needs.
- Trace one concrete request/input all the way through the system and write the trace down. If you
  cannot narrate what happens to a single input, you do not understand it either.
- Run it if you can — execute the tests, call the entrypoint, print intermediate values. Real
  observed behaviour beats inferred behaviour every time.
- Note the things that are *surprising*: the retry that exists because of a real bug, the magic
  constant, the ordering that matters. These are where understanding actually lives.

**Every factual claim in the dossier must be anchored to `path/to/file.py:LINE`.** No exceptions.
This is not bureaucracy — it is what lets the learner verify you instead of trusting you, and
verification is the whole point. If you cannot anchor a claim, cut it.

## Step 2 — Find the load-bearing ideas

Pick **3 to 7 concepts**. Concepts, not files. A concept is an idea the system would collapse
without: "we retrieve before we generate so the model never has to memorise the corpus", "the queue
decouples request latency from processing time", "idempotency keys are what make retries safe".

Test for a real concept: *if the learner misunderstood this, would they rebuild the system wrong?*
If not, it is trivia. Cut it. Seven shallow concepts teach less than four deep ones.

Order them so each one only depends on the ones before it.

## Step 3 — For each concept, write the four pieces

**The simple explanation.** Common vocabulary only, aimed at a bright twelve-year-old. This is the
reference the learner compares their own attempt against — so it has to be genuinely simple, not
jargon with an apologetic tone. If your explanation needs a word that only appears in this field,
you have not simplified it, you have relabelled it.

**The banned words.** List the terms the learner could hide behind for this specific concept —
pulled from the code's own vocabulary. For a RAG system: `embedding`, `vector`, `semantic`,
`cosine`, `chunk`, `index`. For a queue-based backend: `idempotent`, `at-least-once`, `backpressure`,
`consumer group`. The dossier flags these live as the learner types. Being flagged is not a
punishment; it is the moment they discover they were leaning on a word instead of a mechanism.
Include obvious inflections (`embed`, `embedding`, `embeddings`) — the matcher is substring-based
and case-insensitive.

**The gap questions.** 3-5 per concept, each with an answer and a source anchor. Good gap questions
share a shape: they cannot be answered by pattern-matching the text. Reach for these forms —

- *What breaks if we delete this?* — forces reasoning about purpose, not description.
- *Why this and not the obvious alternative?* — surfaces the tradeoff the code silently made.
- *What input makes this behave badly?* — you only know a mechanism when you know its edges.
- *This constant is 0.7. Where does that number come from, and what happens at 0.3?*
- *Walk the value of `x` from line 12 to line 40.* — pure mechanism, nowhere to hide.

**The senior register.** The same idea retold the way one staff engineer tells another: the tradeoff
taken and what was given up, the failure modes and what they look like in production, cost and
complexity, what would have to change at 100x, and the alternative designs with an honest reason
each was not chosen. This is objective #4 — the learner should be able to defend this system in a
design review, not just describe it.

Two registers, one truth. If the simple version and the senior version disagree, the simple version
is a lie you told for convenience. Fix it.

## Step 4 — Design the rebuild lab

This is the part that produces independence, so it gets the most care.

The lab is a **specification with runnable acceptance tests, and no source code visible**. The
learner builds the system from the spec in their own editor. Give them:

- A plain-language spec of what the thing must do — behaviour and contracts, never implementation.
- 4-8 milestones, each with a concrete acceptance criterion they can check themselves.
- A real test file (`pytest`, `vitest`, whatever fits) they can run against their own attempt.
  Write it so it tests the *contract*, not your particular implementation — otherwise you are
  making them guess your code, which teaches nothing.
- A graduated hint per milestone: a nudge toward the idea, never a snippet.

The original source is locked until the rebuild section is complete. When it unlocks, the learner's
job is not to admire it but to **diff their thinking against it**: where did they differ, and is
their version actually worse, or just different? Sometimes theirs is better. Say so when it is —
treating the AI's output as automatically correct is its own kind of dependence.

## Step 5 — Analogies last, not first

An analogy handed to you is a souvenir. An analogy you built is a hook into memory you already
have. So the dossier asks the learner to forge their own first, then shows yours for comparison.

Yours should still be good — concrete, mechanical, and *load-bearing*, meaning it predicts the
system's behaviour rather than just evoking a vibe. "Lambda is like a chef-for-hire who appears
instantly, cooks exactly what was ordered, bills you for the milliseconds he was in the kitchen,
and vanishes" is load-bearing: it correctly predicts cold starts, per-ms billing, and statelessness.
"Lambda is like magic" predicts nothing.

For each analogy also name **where it breaks**. Every analogy is wrong somewhere, and the learner
who knows where is safe from over-extending it.

## Step 6 — Author `lesson.json` and build

Full schema and field-by-field notes: **`references/lesson-schema.md`**. Read it before writing
the file — it is the contract the build script enforces.

Every user-facing string is an object with `en` and `es` keys. Write the English first and let the
Spanish be a real translation, not a gloss: analogies especially need to be re-chosen so they land
in Spanish, not transliterated. Keep code, identifiers, and file paths untranslated. Details in
**`references/bilingual.md`**.

```bash
python3 scripts/build_lesson.py lesson.json -o feynman-<system-name>.html
```

The script validates the schema, reports what is missing in plain language, and emits one
self-contained HTML file — no network, no CDN, no build step. It owns all the interactive
machinery (gating, jargon detection, progress, language switching), so you never hand-write that:
you only ever author content. If you find yourself writing HTML or JavaScript, stop — either the
schema already covers what you want, or `references/html-architecture.md` explains how to extend
the template properly.

Deliver the file to the user. Then read `references/tutor-protocol.md` and open the live session.

## The strict-lock policy, and why it is honest

Sections unlock in order, and each gate needs real written work — the code stays hidden until the
rebuild is done. A learner who reads the solution first has spent their one chance at retrieval,
and retrieval is where the learning is; the lock protects that chance.

But it is a static HTML file, and anyone can open dev tools. So the dossier does not pretend to be
a vault. Every gate has a **break-glass** link that opens immediately and permanently stamps that
section `UNVERIFIED` in the progress panel and the final report. That is stronger than a fake lock:
the learner keeps control, and keeps an honest record of exactly which parts of the system they
have never actually reconstructed. Those stamps are the study plan for next week.

Say this to the user when you hand over the file. Friction they understand is friction they accept;
friction that feels arbitrary just gets bypassed with a sigh.

## Scope

Right-size the dossier to the code. A 200-line script gets 3 concepts and a lean lab. A service with
a dozen modules gets 5-7 concepts, and you scope the lab to the core path rather than the whole
repo — a rebuild that cannot be finished in one sitting will not be started. If the codebase is
genuinely too large for one dossier, say so, propose a sequence of dossiers by subsystem, and build
the first one rather than building a shallow tour of everything.

## Reference files

- `references/lesson-schema.md` — the `lesson.json` contract, field by field, with a worked example
- `references/tutor-protocol.md` — how to run the live Socratic session after delivering the file
- `references/bilingual.md` — writing the EN/ES pairs so both read as native
- `references/html-architecture.md` — what the template does and how to extend it safely
