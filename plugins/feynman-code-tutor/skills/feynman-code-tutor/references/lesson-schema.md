# `lesson.json` — the contract

Every user-facing string is a **bilingual object**: `{"en": "...", "es": "..."}`. The build script
rejects a bare string wherever it expects one of these, and tells you the path that is wrong.

Strings support a small subset of Markdown: `**bold**`, `` `code` ``, `- ` bullets, `1. ` numbered
lists, blank-line paragraphs, and fenced code blocks with ```` ```lang ````. Nothing else — no
tables, no links. If you need more, you are putting reference material where an exercise belongs.

**Anchors** are `path/to/file.py:LINE` or `path/to/file.py:12-40`. They render as a small monospace
tag next to the claim. Any field named `anchor` is required to be real — invented anchors destroy
the learner's ability to verify you, which is the one thing the dossier is for.

---

## Top level

```json
{
  "meta": { ... },
  "orientation": { ... },
  "prior_knowledge_prompt": { "en": "...", "es": "..." },
  "concepts": [ ... ],
  "rebuild": { ... },
  "senior_brief": { ... },
  "flashcards": [ ... ],
  "next_steps": [ { "en": "...", "es": "..." } ]
}
```

`flashcards` and `next_steps` are optional; everything else is required.

---

## `meta`

| field | type | notes |
|---|---|---|
| `title` | bilingual | Names the system, not the document. "The RAG service you just built" beats "Learning Guide". |
| `subtitle` | bilingual | One line on what the learner will be able to do at the end. |
| `system_name` | string | Slug used in the filename and report. |
| `source_root` | string | Repo path or description of what was analysed. |
| `default_lang` | `"en"` \| `"es"` | Default `"en"`. |
| `estimated_minutes` | int | Be honest. A dossier that claims 30 minutes and takes 3 hours gets abandoned at minute 40. |

---

## `orientation`

The only section that is unlocked from the start. It answers "what did the AI actually do here?"
in plain language, with no teaching agenda — the learner needs a map before they can be examined
on the terrain.

```json
"orientation": {
  "problem":      {"en": "...", "es": "..."},
  "what_was_built": {"en": "...", "es": "..."},
  "files": [
    {"path": "src/retriever.py", "role": {"en": "...", "es": "..."}}
  ],
  "dataflow": [
    {"step": {"en": "...", "es": "..."}, "anchor": "src/api.py:31"}
  ],
  "decisions": [
    {"choice": {...}, "why": {...}, "instead_of": {...}, "anchor": "src/store.py:12"}
  ]
}
```

`dataflow` is the single traced input from Step 1 of the skill, one entry per hop. Write it as
things happening to a specific value, not as an abstract pipeline: "the question text arrives as
JSON and is trimmed" is useful; "the input layer processes the request" is noise.

`decisions` are the choices a reader would not guess from the code alone. Three to six is plenty.

---

## `concepts` — 3 to 7 entries

```json
{
  "id": "retrieval-before-generation",
  "name": {"en": "...", "es": "..."},
  "one_liner": {"en": "...", "es": "..."},
  "banned_terms": ["embedding", "embeddings", "vector", "semantic", "cosine"],
  "simple_explanation": {"en": "...", "es": "..."},
  "analogy": {
    "text": {"en": "...", "es": "..."},
    "breaks_down": {"en": "...", "es": "..."}
  },
  "gap_questions": [
    {"q": {...}, "a": {...}, "anchor": "src/retriever.py:44"}
  ],
  "senior": {
    "tradeoff": {...},
    "failure_modes": [{"mode": {...}, "symptom": {...}, "mitigation": {...}}],
    "cost_complexity": {...},
    "at_scale": {...},
    "alternatives": [{"option": {...}, "why_not": {...}}]
  }
}
```

`id` — lowercase slug, stable, used for progress keys.

`one_liner` — shown *before* the gate, so it must orient without teaching. Name the question the
concept answers rather than the answer: "How does the system answer questions about documents it
was never trained on?" not "It embeds chunks and retrieves by cosine similarity."

`banned_terms` — matched case-insensitively as substrings against the learner's typed explanation,
so `embed` also catches `embedding` and `embeddings`. Prefer 4-10 terms. Include the English term
even in Spanish mode: Spanish-speaking engineers say "el embedding".

Do **not** ban ordinary words the learner needs to explain anything (`data`, `search`, `model`,
`function`) — a gate that cannot be passed honestly teaches only resentment.

`gap_questions` — 3-5. See the question shapes in SKILL.md Step 3. Every one needs a real `anchor`.

`senior` — all fields required. Two registers of one truth; if the simple explanation and the
senior brief could not both be true, the simple one is wrong.

---

## `rebuild`

```json
"rebuild": {
  "spec": {"en": "...", "es": "..."},
  "constraints": [{"en": "...", "es": "..."}],
  "milestones": [
    {"title": {...}, "goal": {...}, "acceptance": {...}, "hint": {...}}
  ],
  "acceptance_tests": {
    "filename": "test_retriever.py",
    "language": "python",
    "code": "import pytest\n..."
  },
  "reference_solution": [
    {"path": "src/retriever.py", "language": "python", "code": "..."}
  ],
  "diff_prompts": [{"en": "...", "es": "..."}]
}
```

`spec` describes **behaviour and contracts only**. The moment it says "use a dict keyed by doc id"
it has stopped being a spec and become dictation.

`acceptance_tests` is visible from the start — the learner needs to run it while building. Write it
against the contract, not your implementation: no asserting on private helpers, no importing
internal names the spec never mentioned. A test the learner can only pass by guessing your variable
names teaches guessing.

`reference_solution` stays locked until the rebuild gate is cleared. Include the real code from the
repo, not a cleaned-up retelling — the learner is going to open the actual file afterwards and any
discrepancy costs you all your credibility.

`diff_prompts` are the questions asked at the reveal: "where did yours differ?", "is the difference
a bug, a style choice, or an improvement?", "what did the original handle that you forgot?"

---

## `senior_brief`

```json
"senior_brief": {
  "architecture_summary": {"en": "...", "es": "..."},
  "review_questions": [{"q": {...}, "a": {...}}]
}
```

`architecture_summary` is the whole system at staff level — how the concepts compose, where the
real risk sits, what you would flag in review. `review_questions` are the ones a sharp interviewer
or reviewer would ask; 4-8 of them, with answers that admit uncertainty where it exists.

---

## `flashcards` and `next_steps`

```json
"flashcards": [{"front": {...}, "back": {...}}],
"next_steps": [{"en": "...", "es": "..."}]
```

Flashcards are for the details that are genuinely worth memorising — a signature, a default, an
ordering constraint. Not for concepts; concepts are learned by rebuilding, not by drilling.

`next_steps` point outward: the doc to read, the variation to try, the related system to attack next.

---

## A complete worked example

`assets/example-lesson.json` is a full, valid dossier for a small document-Q&A service — three
concepts, six rebuild milestones, runnable tests, both languages. Read it before authoring your
first one; it is faster than reading this file twice, and it shows the *register* the prose should
be in, which no schema can specify.

## Validating

```bash
python3 scripts/build_lesson.py lesson.json -o out.html
```

Errors name the JSON path and what was expected. Fix and rerun — the script is fast and idempotent.
