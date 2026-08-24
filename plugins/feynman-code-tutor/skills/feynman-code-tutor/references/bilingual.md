# Writing the EN/ES pairs

The dossier ships both languages inside one file and swaps them with a toggle. Nothing is
translated at runtime, so whatever you write is what the learner reads — a rushed Spanish column
turns half the product into a machine-translation artifact.

## Write English first, then re-say it in Spanish

Translate the *meaning*, not the sentence. If the English reads "the queue decouples request
latency from processing time", the Spanish is not a word-by-word mapping — it is how a Spanish-
speaking engineer would say that thought out loud. Read the Spanish on its own and ask whether it
sounds like it was written in Spanish. If it sounds translated, rewrite it.

Register matters as much as vocabulary: use `vos`-neutral, professional-but-warm Spanish that reads
naturally across Latin America, and avoid the stiff peninsular constructions machine translation
reaches for.

## Analogies get re-chosen, not translated

This is the field where literal translation fails hardest, because analogies depend on shared
cultural furniture. An analogy built on an American diner, a drive-thru, or a college registrar
lands flat in Spanish. Pick a *different* concrete scene that predicts the same behaviour, and
check it still breaks down in the same place — the `breaks_down` field has to stay true for the
analogy that is actually in front of the reader.

The two versions do not have to be the same analogy. They have to be equally good.

## What stays in English, always

- Code, identifiers, function and variable names, file paths, CLI commands
- Library, protocol, and product names (`FastAPI`, `pgvector`, `HTTP`, `Postgres`)
- Everything inside `code` fields and `` `backticks` ``
- Anchors

Spanish-speaking engineers read code in English. Translating an identifier makes the anchor
unverifiable and the sentence harder to follow, not easier.

## Technical terms with no good Spanish

Many have no natural translation and are simply spoken in English: *embedding*, *deploy*,
*commit*, *cache*, *endpoint*, *thread*. Use the English word, in italics or as-is, the way people
actually speak — `el embedding`, `hacer deploy`. Do not invent Spanish coinages nobody says.

This has a direct consequence for `banned_terms`: keep the English terms in the list even for the
Spanish side of the gate, because that is the word the learner will actually type when hiding.
Where a Spanish equivalent is genuinely in use (`vector`, `índice`, `similitud`, `fragmento`), add
both.

## Length

Spanish runs roughly 15-25% longer than English. That is fine — the layout absorbs it. Do not
compress the Spanish to match the English visually, and do not pad the English to match the
Spanish. Each one should be as long as it needs to be.

## Adding a third language later

The template renders any set of language codes present in the bilingual objects and builds the
toggle from `meta.languages`. Adding `"pt"` takes two steps, not one:

1. Add that key to *every* bilingual object in `lesson.json` — the build script will list any it
   is missing.
2. Add it to the `UI` and `PLACEHOLDERS` dicts in `scripts/build_lesson.py`. Those hold the
   chrome — section headings, button labels, the report — and ship `en`/`es` only. Without
   step 2 the dossier renders your content in Portuguese and every label in English.

Only take this on when the user asks for it: it multiplies authoring cost with no benefit to a
bilingual reader.
