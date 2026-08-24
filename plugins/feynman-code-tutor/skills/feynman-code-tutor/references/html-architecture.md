# What the template does

Read this only if you are tempted to hand-write HTML or JavaScript. Almost always the schema
already covers what you want, and hand-rolled markup means the next dossier has to reinvent it.

## Files

| file | role |
|---|---|
| `scripts/build_lesson.py` | validates `lesson.json`, renders every section, inlines the assets |
| `assets/dossier.css` | all styling; light/dark via tokens, no external fonts |
| `assets/dossier.js` | gates, jargon detection, progress, language switch, report |
| `assets/example-lesson.json` | a complete worked dossier — read it when authoring your first one |

Output is one HTML file with the CSS and JS inlined. No network, no build step, no dependencies.
It opens from a `file://` path, from a shared drive, or from an email attachment.

## How the language switch works

Every bilingual string renders as one element per language, all present in the DOM:

```html
<div class="lb" data-lang="en">…</div>
<div class="lb" data-lang="es">…</div>
```

CSS shows only the blocks matching `body[data-lang]`. Nothing is translated at runtime, so a
missing translation is a build-time error rather than a silent English fallback. Textarea
placeholders cannot work that way, so they carry `data-ph-en` / `data-ph-es` and the runtime swaps
the `placeholder` attribute on toggle.

Adding a language means adding its key to every bilingual object plus `meta.languages`. The
validator lists every field that is missing it.

## The gates

All gating lives in `dossier.js` as small predicate functions, and `refresh()` re-evaluates
everything on any change. The chain:

| gate | requirement |
|---|---|
| concepts unlock | 60+ words on the blank page |
| concept reference reveals | 40+ words in the explanation **and** zero banned terms |
| gap answer reveals | 8+ words in that gap's textarea |
| analogy reference reveals | 15+ words of the learner's own analogy |
| rebuild unlocks | every concept has a submitted explanation and all gaps answered |
| source code reveals | all milestones ticked **and** 80+ words of rebuild notes |
| senior register unlocks | source revealed |

Word thresholds are deliberately low. They exist to stop one-word bypasses, not to police length —
a gate tuned to force essays gets defeated by padding, which teaches padding.

## Break-glass

Every gate carries a break-glass button. It confirms, opens the section, and sets a permanent flag
that renders that section `UNVERIFIED` in the report and in the sidebar dot. Nothing is ever
re-locked and no work is lost — the file records what happened rather than preventing it, which is
the only honest posture for a static page anyone can view-source.

## State and storage

State is a single object: text by key, submitted flags, revealed flags, milestone booleans,
break-glass flags, language, theme. It persists to `localStorage` under `feynman:<system_name>` when
available and falls back to in-memory silently when it is not — a private window, a preview pane, or
a browser blocking site data all degrade to a working file that simply forgets on reload. Never make
a feature depend on storage succeeding.

## Extending it

Adding a section means: a `render_*` function in `build_lesson.py`, a nav entry in `build()`, its
gate predicate in `dossier.js`, and a row in `renderReport()`. Keep new content in `lesson.json` and
new mechanics in the template — the split is what keeps authoring cheap.

Two things to preserve if you change anything: the report must keep distinguishing verified work
from break-glass work, and reference material must never render before the learner's own attempt.
Those two properties are the entire product.
