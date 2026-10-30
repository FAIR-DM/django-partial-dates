# Roadmap — django-partial-dates

**Date:** 2026-10-29

This document was designed against [GOALS.md](../GOALS.md). See also [CONTEXT.md](../CONTEXT.md)
for domain terminology, [CONSTITUTION.md](../CONSTITUTION.md) for project standards and
[ADR 0001](adr/0001-store-partial-dates-as-iso-8601-strings.md) for how a partial date is stored.

## Versioning

Releases are gated on goal importance, not on a count of features.

| Version | Gate |
|---|---|
| `0.0.x` | Building toward the Essential goals. Pre-viable, expect churn, nothing published |
| `0.1.0` | All Essential goals delivered. The minimum usable release, and the first publish |
| `0.1.x` → `0.x` | Advancing the Expected goals, at whatever granularity the work takes |
| `1.0.0` | All Expected goals delivered. The complete, dependable release |
| `1.x` | Stable line: fixes and additive features only |
| `2.0` | The next major, where breaking changes go |

A goal is not one minor: some take several releases, and one release can move two. Once `1.0`
ships, a breaking change never goes out as `1.x`. It waits for the next major.

## Essential goals: v0.1.0

Everything needed for FAIR-DM and django-literature to drop django-partial-date.

### R1 — A partial date value that tells the truth

*delivered in [#3](https://github.com/FAIR-DM/django-partial-dates/issues/3) · advances G2*

Everything else is built on the value type, so it comes first. django-partial-date's value class
compares wrongly across precisions, cannot be hashed, invents a day for a year-only date, and
carries a precision setter that silently does nothing. FairDM had to write its own `precedes()`
to work around the comparisons. This item replaces all of that with one immutable type.

**Deliverables:**

- A type holding year, month and day, with `None` for an unknown part, built from parts or parsed
  from the ISO form, with invalid input rejected
- Sorting in ISO order, equality and hashing
- The start and end of the period, as real dates
- A comparison answering before, after or overlapping
- The ISO form back out, for storage and export

### R2 — A model field storing the ISO form

*delivered in [#8](https://github.com/FAIR-DM/django-partial-dates/issues/8), [#9](https://github.com/FAIR-DM/django-partial-dates/issues/9) · advances G1, G9*

`PartialDateField` stores a partial date as ADR 0001 sets out: one `varchar(10)` column with `C`
collation on PostgreSQL and a check constraint that blocks a malformed value written by any route,
with the value type going in and coming out and the column, collation and check carried by the
migration. It is the first module to import Django, so Django is now a runtime dependency. Fixtures
round-trip through `dumpdata` and `loaddata`, empty values included. The whole test suite runs on
SQLite and on PostgreSQL on every pull request, the second through a job in this repository's own
tests workflow, because the shared workflow runs SQLite only.

### R3 — Filtering, ordering and grouping in the database

*delivered in [#14](https://github.com/FAIR-DM/django-partial-dates/issues/14) · advances G3, G6*

String comparison already gives range filters and ordering. This item adds the lookups that
reading the ISO form makes possible, and the part that matters as much as the code: a guide that
tells a developer exactly which uncertain matches each one includes. Constitution Article XII
makes the boundary tests part of the definition of done.

**Deliverables:**

- `year`, `month` and `day` lookups and transforms, usable in `filter`, `values` and `annotate`
- A `start` transform giving the first day of the period as a date, for chart axes
- Range filters that accept partial dates as their bounds
- A developer guide covering every lookup, with the uncertain matches each includes and the
  recipes for "June of any year", a date axis and a year, month and day drilldown

### R4 — Entering and editing a partial date

*delivered in [#19](https://github.com/FAIR-DM/django-partial-dates/issues/19) · advances G4*

A person recording a date has to be able to say how much of it they know. FairDM already owns a
form field and a three-select widget built over django-partial-date. They move here, rebuilt on
the value type, and the model field returns them as its form field so the admin uses them without
configuration.

**Deliverables:**

- A form field validating year, year and month, or full date, and rejecting a day without a month
- A widget of year, month and day selects with month and day optional
- The admin using both for the model field

### R5 — Moving from django-partial-date

*delivered in [#20](https://github.com/FAIR-DM/django-partial-dates/issues/20) · advances G5*

django-partial-date stores a timestamp with the precision in its seconds. Every project moving
over needs to turn that into the ISO form without losing a value, and FAIR-DM has two packages
waiting to do it. The conversion ships here once, so each project's own migration is a few lines.

**Deliverables:**

- An operation a project's migration calls to convert an existing column in place, on PostgreSQL
  and SQLite
- A how-to guide for the move, including swapping the field in existing migrations so they no
  longer import django-partial-date

## Expected goals: v1.0.0

The breadth that makes the package dependable rather than merely usable.

### R6 — Showing a partial date to a reader

*delivered in [#28](https://github.com/FAIR-DM/django-partial-dates/issues/28) · advances G7*

A reader sees a partial date in their own language at the precision it was recorded, so a year
reads as a year and never as "1 January 1990". FairDM's `format_partial_date()` was the shape
generalised here.

**Deliverables:**

- Locale-aware formatting at year, month and day precision
- A template filter for it
- A mixin that shows the field in the admin's lists and read-only views

### R7 — Model history and other serialisers

*delivered in [#29](https://github.com/FAIR-DM/django-partial-dates/issues/29) · advances G8*

Values come back unchanged, empty ones included, through the JSON written by
`django.core.serializers` and through django-reversion: its stored versions, `field_dict`,
reverting a row or a revision and recovering a deleted row. The tests run on SQLite and PostgreSQL
and found no fault, so the field needed no change. django-reversion is a development dependency
only.

## Aspirational goals

### R8 — django-filter and Django REST framework extras

*feature · advances G10*

FairDM filters measurements by date with django-filter and exposes an API. Ready-made filters and
a serializer field would save each project from writing its own, but they belong in optional
extras so the core keeps Django as its only dependency.

**Deliverables:**

- A django-filter filter class validating a partial date, with range and precision lookups
- A Django REST framework serializer field reading and writing the ISO form
- Both installable as extras, with the core importing neither
