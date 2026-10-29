# Domain Docs

How an agent should read this repo's domain documentation before working on the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root: the vocabulary this repository uses, and the words it
  deliberately avoids.
- **`docs/adr/`**: the decisions that touch the area you are about to work in. ADR 0001, the
  storage decision, touches almost everything.
- **`GOALS.md`**, when it exists: what the package works toward.

If any of these files don't exist, proceed silently. Don't flag their absence, and don't suggest
creating them upfront.

## File structure

Single-context repo:

```
/
├── CONTEXT.md
├── CONSTITUTION.md
├── docs/adr/
└── partial_dates/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, say, or a test name), use the term as
defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids. Two are worth
repeating:

- A **partial date** is one date recorded to some precision. Don't call it a range, an interval,
  a fuzzy date or an approximate date.
- The parts nobody recorded are **unknown**. Don't call them missing, and never fill them in.

## Never store certainty the data doesn't have

A request to store a partial date as a start and end date, as a timestamp, or with companion
columns is answered by pointing at ADR 0001, never by adding the option. A request for uncertain
or approximate dates (`1990?`, `1990~`) is out of scope (README, *Scope and philosophy*).

## Flag conflicts with a recorded decision

If your output contradicts a decision in `docs/adr/`, surface it explicitly rather than silently
overriding it.
