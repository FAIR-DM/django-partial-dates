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

*feature · advances G2*

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

*feature · advances G1, G9*

The field from ADR 0001: one `varchar(10)` column with `C` collation, a check constraint that
blocks a malformed value written by any route, and the value type in and out. It is the first
module to import Django, so Django becomes a runtime dependency here. The `C` collation is the
reason range filters and the year lookup use the index, so the field is tested against PostgreSQL
as well as SQLite from the start. The shared test workflow runs SQLite only, so this repository
adds its own PostgreSQL job.

**Deliverables:**

- The model field, accepting the value type, an ISO string or `None`
- The column type, collation and check constraint, emitted in migrations
- Serialisation through `value_to_string`, so `dumpdata` and `loaddata` round-trip, empty values
  included
- The test suite run against PostgreSQL and SQLite in continuous integration

### R3 — Filtering, ordering and grouping in the database

*feature · advances G3, G6*

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

*feature · advances G4*

A person recording a date has to be able to say how much of it they know. FairDM already owns a
form field and a three-select widget built over django-partial-date. They move here, rebuilt on
the value type, and the model field returns them as its form field so the admin uses them without
configuration.

**Deliverables:**

- A form field validating year, year and month, or full date, and rejecting a day without a month
- A widget of year, month and day selects with month and day optional
- The admin using both for the model field

### R5 — Moving from django-partial-date

*feature · advances G5*

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

*feature · advances G7*

A year-only date shown as "1 January 1990" is the false certainty this package exists to avoid,
and it is easy to do by accident in a template. FairDM's `format_partial_date()` is the shape to
generalise: a date shown in the reader's locale at its own precision.

**Deliverables:**

- Locale-aware formatting at year, month and day precision
- A template filter for it
- A display of the field in the admin's list and detail views

### R7 — Model history and other serialisers

*task · advances G8*

django-partial-date's empty values broke django-reversion. R2 covers Django's own serialisers.
This item proves the remaining paths: model history tools that store serialised versions, and
JSON produced by `django.core.serializers`.

**Deliverables:**

- Tests round-tripping values, empty ones included, through django-reversion and the JSON
  serialiser

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
