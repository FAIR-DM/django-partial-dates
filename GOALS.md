# Goals

These are the standing directions `django-partial-dates` works toward. Each one is a capability or
quality to steer by, not a task that gets ticked off. Whether a goal is served well enough is
decided in the roadmap, the feature specifications and review, never by the goal itself.

This file carries no version numbers or release plan. For what the package is, what it stays out
of, and the principles that settle a close call, read the *Scope and philosophy* section of the
[README](README.md). The words are defined in [CONTEXT.md](CONTEXT.md).

Importance is a tag on each goal, not a ranking:

- **Essential**: not worth adopting without it.
- **Expected**: a complete, dependable version is expected to have it.
- **Aspirational**: a genuine want whose absence never makes the package incomplete.

| ID | Goal | Importance | Status | Notes |
|----|------|------------|--------|-------|
| G1 | A model field stores a partial date at the precision it was recorded at, and never stores a part nobody recorded | Essential | | Storage is fixed by [ADR 0001](docs/adr/0001-store-partial-dates-as-iso-8601-strings.md) |
| G2 | In Python, a partial date can be built, parsed, compared, sorted and used as a set member or dictionary key, and gives the start and end of its period | Essential | | Sorting and "is this one earlier?" are different questions: the second can answer that two dates overlap |
| G3 | A query can filter, order and group partial dates in the database, by range and by year, month or day | Essential | | Every lookup states which uncertain matches it includes |
| G4 | A person can enter and edit a partial date in a form and in the admin, choosing how much of the date they know | Essential | | |
| G5 | A project storing dates with django-partial-date can move to this package with a migration and lose no data | Essential | | FAIR-DM's own packages are the first to move |
| G6 | A developer can find out exactly what each filter and lookup matches before relying on it | Essential | | Uncertainty is documented, never designed away |
| G7 | A partial date is shown to a reader in their locale at its own precision, never with an invented day or month | Expected | | |
| G8 | Values pass unchanged through Django's serialisers, fixtures and anything that records model history | Expected | | |
| G9 | The field behaves the same on PostgreSQL and SQLite, and both are tested | Expected | | |
| G10 | Projects using django-filter or Django REST framework get ready-made filters and serializer fields | Aspirational | | Optional extras, never runtime dependencies of the core |

## Direction

The intended design, recorded so the first features start from it. None of it is built yet.

- **One column, the ISO form.** `YYYY`, `YYYY-MM` or `YYYY-MM-DD` in a `varchar(10)` with `C`
  collation, guarded by a check constraint (ADR 0001).
- **The value type holds year, month and day,** with `None` for a part that is unknown. It is
  immutable. It sorts in ISO order, so `1990` comes before `1990-06`, which comes before
  `1990-06-14`.
- **Comparing two dates is a separate question from sorting them.** A method answers before,
  after or overlapping. FairDM's `precedes()` helper is the case it replaces.
- **Lookups run in the database:** `year`, `month` and `day` read characters of the stored form,
  and `start` gives the first day of the period as a real date. A year-only value has no month,
  so it never matches a month lookup.
- **The form widget is year, month and day selects,** with month and day optional. FairDM's
  `PartialDateWidget` is the starting point.
- **Moving from django-partial-date is a data migration** that reads its timestamp and the
  precision in its seconds and writes the ISO form.

_Written 2026-10-29. Revise as the goals change._
