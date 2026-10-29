# Research — FS-001: A partial date value for Python code

The investigation behind `plan.md`, against `main` at `c71fec8`. There is no `planning-notes.md`
and no sketch for this feature.

## R1 — Where the value lives and what it is called

The package holds only `partial_dates/__init__.py`. The value goes in a new module,
`partial_dates/partial_date.py`, and is re-exported from the package, so a developer writes
`from partial_dates import PartialDate`.

- **`PartialDate`** is the name `CONTEXT.md` gives the concept and the name the replaced package's
  class has (`partial_date.PartialDate`). The import paths differ (`partial_dates` against
  `partial_date`), so both can be installed side by side while a project moves (R5).
- **`Precision`** names the three precisions, `CONTEXT.md`'s word for them.
- **`Relation`** names the three answers of the comparison: before, after and overlapping.

## R2 — A frozen dataclass

A `dataclasses.dataclass(frozen=True, slots=True)` with fields `year`, `month` and `day` gives,
from the standard library:

- immutability: assigning a field raises `dataclasses.FrozenInstanceError` (FR-007),
- equality on the three fields, returning `NotImplemented` for another class, so a partial date
  is never equal to a `date`, a text or a number (FR-009, FR-010),
- a hash over the same three fields, consistent with equality (FR-009),
- a readable `repr`, pickling and copying.

Ordering is not taken from the dataclass. `order=True` compares the field tuples, and a `None`
month against an integer month raises `TypeError`. The four ordering methods compare the ISO
forms of both values as text instead. Every part is zero-padded and fixed-width, so text order is
date order, and a year sorts before its months and a month before its days: `1990` < `1990-01` <
`1990-01-01` < `1990-02`. Each method returns `NotImplemented` for another type, which makes Python raise
`TypeError` (FR-008, FR-010). `functools.total_ordering` is not used: four one-line methods read
more plainly than a decorator that derives three of them.

## R3 — Validation, and the error it raises

Validation runs in `__post_init__`:

1. each given part is an `int` and not a `bool` (`True` is an `int` in Python and would otherwise
   build year 1),
2. a day needs a month,
3. the parts make a real date: `datetime.date(year, month or 1, day or 1)` raises `ValueError`
   for a year outside `datetime.MINYEAR`–`datetime.MAXYEAR` (1–9999, the range ADR 0001 sets), a
   month outside 1–12 and a day the month does not have, leap years included.

Every refusal raises `ValueError` (FR-006, decision D2 in `decisions.md`). A wrong type raises
`ValueError` too rather than `TypeError`, because the spec names one error for refused input and a
caller catching it should not need two.

## R4 — Reading the ISO form

`PartialDate.fromisoformat(text)` mirrors `datetime.date.fromisoformat`. It matches the text in
full against `[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?`, then builds the value from the groups, so the same
validation applies. The character class is `[0-9]` and not `\d`, because `\d` matches every
Unicode digit (`١٩٩٠` would otherwise read as 1990). `re.fullmatch` is used, never `$`, which
matches before a trailing newline. Anything that is not a `str` is refused with `ValueError`.

## R5 — Writing the ISO form

`isoformat()` writes `f"{year:04d}"`, adding `-{month:02d}` and `-{day:02d}` for the parts that
are known. `__str__` returns the same text, so `str(value)` and f-strings give the ISO form.

## R6 — Start and end

`start` is `date(year, month or 1, day or 1)`. `end` is `date(year, month or 12, day or
last_day)`, where `last_day` comes from `calendar.monthrange(year, month)[1]`, which follows the
proleptic Gregorian calendar (`1900` is not a leap year, `2000` is). Both are properties: they are
cheap and take no arguments.

## R7 — The comparison

`relation_to(other)` returns `Relation.BEFORE` when `self.end < other.start`, `Relation.AFTER`
when `self.start > other.end`, and `Relation.OVERLAPPING` otherwise. Because every period is a
whole year, a whole month or a single day, two periods are always nested or apart, so
"overlapping" means one holds the other or they are the same.

This is the same answer as FairDM's `precedes()` for "before" (`fairdm/core/dates.py`, lines 12–31,
on FairDM's main branch of 2026-10-29): that helper takes the coarser of the two precisions,
compares the years, the year and month tuples, or the full dates at that precision with a strict
`<`, and a truncated value is earlier exactly when its whole period
ends before the other's starts. SC-003 is shown by a test that implements the coarser-precision
rule independently and compares the two over every pair in a sample.

Asking about anything that is not a `PartialDate` raises `TypeError`. The spec says the question
is refused. Here the input is a valid value of the wrong type, and `TypeError` is what Python's
own comparisons raise for the same mistake.

## R8 — Precision and Relation as enums

`Precision` and `Relation` are `enum.StrEnum`s (Python 3.11 and later, and the package needs
3.12). Their values are `"year"`, `"month"`, `"day"` and `"before"`, `"after"`, `"overlapping"`.
A string value prints readably and can be stored or compared to a string by a caller. Members
compare as text, so `sorted(Precision)` is alphabetical. That order carries no meaning, and the
`Precision` docstring says so: nothing in this feature compares precisions.

## R9 — Dependencies

None. Everything is in the standard library (`dataclasses`, `datetime`, `calendar`, `re`, `enum`).
Django stays out of `dependencies` until R2 (FR-006, SC-005). `deptry` stays green because nothing
new is imported from outside the standard library.

## R10 — Documentation

The documentation standard (§2) says a small package needs no `docs/` site: when setting it up
takes no more than two short examples, the README is its documentation. The value type is that
size, and the package has no docs build. So the README gains a *Usage* section, written by US1 and
extended by US2 and US3, each in the story that adds the names it quotes. The CHANGELOG records the
value under *Added* in `[Unreleased]`. The README's *Status* line changes, because the package now
holds the value. A `docs/` site arrives with the field and its lookups (R2, R3), which need a
guide.

## R11 — Test layout

One source module, one test module: `tests/test_partial_date.py`, split into classes by subject
(`TestBuilding`, `TestReadingTheIsoForm`, `TestWritingTheIsoForm`, `TestOrdering`, `TestEquality`,
`TestPeriod`, `TestRelation`). No Django, no database, no factories: the value has no model.
Tests that reach across many values (SC-002, SC-003, SC-004) enumerate a fixed sample rather than
drawing random ones, so a failure always reproduces. No new test dependency.

## What already exists

| Planned piece | Where the search stopped |
|---|---|
| Immutability, equality, hashing, `repr` | The standard library: `dataclasses.dataclass(frozen=True, slots=True)` |
| Year, month and day range checks, leap years | The standard library: `datetime.date` raises for every invalid combination |
| Last day of a month | The standard library: `calendar.monthrange` |
| Matching the ISO form | The standard library: `re.fullmatch` |
| The value type itself | New code. The replaced `partial_date.PartialDate` carries the defects in `docs/reference/prior-art.md`. `python-edtf` covers the forms but is a dependency far beyond three forms, rejected in the same document |
| Ordering by ISO order | New code: four methods comparing `isoformat()`. `dataclass(order=True)` cannot compare `None` with an integer |
| The before / after / overlapping comparison | New code. FairDM's `precedes()` answers only "before", lives in FairDM, and is the rule this replaces |
| `Precision` and `Relation` | New code: two small `StrEnum`s |
