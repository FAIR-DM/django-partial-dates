# Decisions — FS-001: A partial date value for Python code

Decisions made while specifying and planning, where the issue and the roadmap were silent. Each was
resolved from the goals, the constitution, the ADR and the prior-art notes.

## The reading of the issue that the spec is written from

A developer gets one immutable value for a partial date: built from parts or read from the ISO
form, written back in the ISO form, sorted in ISO order, hashable, with the start and end of its
period as real dates and a separate answer of before, after or overlapping. It is the value alone:
the model field, lookups, forms, the migration from django-partial-date and display to a reader
are R2 to R6. It serves G2.

## D1 — Three stories

Recording a value, sorting and collecting values, and asking when a value could have been are
three things a developer sets out to do. Validation, immutability and the ISO form are scenarios
under the first, hashing under the second, start and end under the third.

**ADR:** none — how the specification is divided, not a design decision.

## D2 — Refused input raises `ValueError`, not Django's `ValidationError`

The value is plain Python and the roadmap makes Django a dependency only at R2, with the first
module that imports it. A `ValidationError` here would make Django a runtime dependency for a
value that never touches it. The field (R2) and the form field (R4) turn the error into a
`ValidationError` with a code, which is where the testing standard expects codes. A part of the
wrong type raises `ValueError` too, so a caller catches one error for all refused input.

**ADR:** none — the standard Python convention for a value type, and the field and form that will
convert it are specified separately.

## D3 — Reading text is strict

Only the three ISO forms, exactly. No trimming, no unpadded parts, no compact form, no times, no
EDTF level 1, and ASCII digits only. ADR 0001 accepts nothing else, and a lenient reader would
accept values the database's check constraint (R2) will refuse. Cleaning what a person typed
belongs to form handling (R4).

**ADR:** none — follows from ADR 0001, which already fixes the accepted forms.

## D4 — A partial date never equals another type, and ordering against one is refused

Equality across types would either break hashing (`a == b` with different hashes) or make a
day-precision value interchangeable with a real date, which is the false certainty the package
exists to avoid.

**ADR:** none — local to the value's comparison methods, and stated in the specification.

## D5 — The comparison has three answers: before, after and overlapping

Two periods are always either nested or apart, so overlapping covers "one holds the other" and
"the same". Equality is already `==`. "Before" is exactly FairDM's current coarser-precision
`precedes()` rule, which SC-003 holds it to.

**ADR:** none — stated in the specification, and nothing downstream depends on more than the three
values.

## D6 — The year is always required, and a day needs a month

A value with no year is not a partial date, and `YYYY--DD` is not an ISO form.

**ADR:** none — follows from the definition in `CONTEXT.md` and ADR 0001.

## D7 — Years 0001 to 9999, proleptic Gregorian

This is ADR 0001's range and Python's own date range, so the start and end are always
representable.

**ADR:** none — already recorded in ADR 0001.

## D8 — Building from a real date is left out

It is not in R1's deliverables, a real date's parts are one call away, and it is added when a
consumer needs it.

**ADR:** none — a scope call for this feature.

## D9 — The precision is exposed

R6's formatting and FairDM's own code branch on it, and the value cannot be read correctly without
it.

**ADR:** none — a property of the value, stated in the specification.

## D10 — No planning notes

The settled design direction (parts with `None`, immutable, hashable, ISO order, start and end, a
separate comparison, ISO in and out, years 0001–9999) is all behaviour and is in the specification
itself.

**ADR:** none — a record of what this feature was given, not a decision.

## D11 — The README is the documentation for now

The documentation standard (§2) lets a small package document itself in its README, and the value
type is that small. The package has no docs build. A `docs/` site comes with the field and its
lookups (R2, R3), which need a guide.

**ADR:** none — the standard already provides for it, and R2 and R3 revisit it.

## D12 — Asking `relation_to` about another type raises `TypeError`

The input is a valid object of the wrong type, and `TypeError` is what Python's own comparisons
raise for that mistake, and what the ordering operators raise here. Refused values stay
`ValueError` (D2).

**ADR:** none — local to one method.

## D13 — Ordering is four methods over a sort key, not `dataclass(order=True)`

`order=True` compares the raw fields, and a `None` month against an integer month raises
`TypeError`. The sort key `(year, month or 0, day or 0)` gives ISO text order because months and
days start at 1. The key is computed in each method rather than stored, so equality and hashing
stay on the recorded parts.

**ADR:** none — an implementation detail of one class.

## D14 — Design review: four low findings, all applied as edits

The design review approved the plan with four low findings and no blocking one:

- A `None` year is named among the refused inputs in T002.
- `Precision` members order alphabetically, as text. The research and the class docstring say that
  order carries no meaning.
- The FairDM rule SC-003 is held to is cited by file and line in `research.md` R7.
- Ordering uses the same exact-class test as the dataclass's equality, so a subclass can never be
  ordered "equal" to a value it is not equal to.

**ADR:** none — corrections to this feature's plan.

## D15 — `relation_to` accepts any `PartialDate`, subclasses included

The ordering operators use the dataclass's exact-class test so that ordering and equality agree
(D14). `relation_to` answers from the two periods alone, through `start` and `end`, so a subclass
gives a correct answer and nothing has to agree with it. It refuses anything that is not a
`PartialDate` with `TypeError` (D12).

**ADR:** none — local to one method.

## D16 — Test classes carry no docstrings

The code documentation standard leaves docstrings off test classes. The ones written during the
build were removed at convergence (T012). The module docstring now names `Relation` as well.

**ADR:** none — a standards correction inside this feature.
