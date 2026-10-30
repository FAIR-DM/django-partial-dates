# Decisions — FS-003: Filtering, ordering and grouping partial dates in the database

Decisions made while specifying, where the issue and the roadmap were silent. Each was resolved
from the goals, the constitution, ADR 0001, the prior-art notes, FS-001 and FS-002. Behaviour stated
about `exclude`, ordering and refused bounds was checked by running the field on SQLite with a
trial `month` lookup, or follows from what each database documents about nulls.

## The reading of the issue that the spec is written from

A developer gets `year`, `month` and `day` lookups and transforms, a `start` transform giving the
first day of the period, range filters taking partial dates as bounds, ordering that matches
`sorted()`, and a guide stating which uncertain matches each filter includes, with recipes for June
of any year, a date axis and a year, month and day drilldown. All of it runs in the database and
behaves the same on PostgreSQL and SQLite. Forms and the admin (R4), the move from
django-partial-date (R5), display (R6), model history (R7) and django-filter (R8) are out of scope.
It serves G3 and G6, and depends only on FS-002, which is delivered.

## D1 — A bound is a position in the sort order, not a period

`lte=1990-06` finds `1990` and `1990-06`, and leaves out `1990-06-14`, because `'1990-06-14'` sorts
after `'1990-06'`. To a reader this looks odd: 14 June is plainly "up to June". The alternative was
to read an upper bound as the end of its period, so that `lte=1990-06` took in the whole of June.

Sort order was kept, because:

- ADR 0001 accepts it, with its own worked range, and rejects hiding the question.
- Constitution Article XII tests exactly this grid, against a bound of `1990-06`.
- Every filter then agrees with `order_by` and with `PartialDate`'s own `<=`. A period reading
  would make `lte` disagree with sorting the values in Python, which is the defect the package
  replaced.
- It keeps the one-column index range scan with the bound passed through unchanged.

The cost is one trap, which the guide states and the edge cases list, with `lt=1990-07`,
`lte=1990-06-30` and `year__lte=2020` as the ways round it.

**ADR:** none — ADR 0001 already records this. If review prefers the period reading, ADR 0001
changes first.

## D2 — Two stories

Filtering and ordering or grouping are the two things a developer sets out to do. The guide is not
a third story: documentation lands in the same story as the name it documents, so each story's
scenarios and requirements carry its part of the guide. The `start` transform sits under US-2,
including filtering by it, because a chart axis is what it is for.

**ADR:** none — how the specification is divided.

## D3 — An unknown part stays unknown under `exclude`

`exclude(month=6)` does not return `1990`, so the row is in neither that nor `filter(month=6)`.
SQL's three-valued logic gives this with no extra code, and it is the honest result: saying `1990`
is not in June claims something nobody recorded. A row holding no date, on a nullable field, is
returned by `exclude`, because Django adds a null guard on the column itself, and that is how every
nullable Django field behaves. Both were observed on SQLite and are specified so the two databases
are held to them.

**ADR:** none — stated in the specification and the guide.

## D4 — Rows with no date sort where the database puts them

SQLite sorts nulls first and PostgreSQL last. Nothing a field can do changes a plain `order_by`. G9
asks for the same behaviour on both, so this is the single stated exception, and `nulls_first` or
`nulls_last` closes it. The guide says to use them.

**ADR:** none — a stated limit of Django's ordering.

## D5 — Real dates are refused as bounds, and go through `start`

FS-002 refuses a real date, and the field's filters already raise before the query. A real date
carries a day that may never have been recorded, so it has no place in a comparison of recorded
text. `start` takes a real date, with a stated rule.

**ADR:** none — follows FS-002.

## D6 — No `end` transform and no `precision` lookup

The roadmap names `start` alone, and Article II asks for the least that satisfies the spec.
`month__isnull` and `day__isnull` select by precision. The uncertain dates for a bound are exactly
the bound's enclosing periods (`1990` for `1990-06`, and `1990` and `1990-06` for `1990-06-14`), so
adding them to a range or taking them out of it needs only `in` on those values.

**ADR:** none — scope.

## D7 — Recipes beyond the three the issue names

Adding every uncertain date to a range, leaving them all out, and taking in the whole of the month
or year in an upper bound were added. ADR 0001 says a developer who needs a different rule writes
it with the lookups, and G6 needs that to be shown, not assumed. They need no code of their own.

**ADR:** none — documentation.

## D8 — The index promise covers what ADR 0001 measured

Range filters, a filter on one year and ordering by the field use the index. These are the queries
ADR 0001's measurements show using it. Filters on month and day read the whole table, as Django's
`__month` does on a real date, and the guide should say so. Comparisons on `year` other than
equality carry no index promise.

**ADR:** none — ADR 0001 records the measurements.

## D9 — Django's text lookups stay as they are

`contains`, `startswith`, `regex` and the like come with every field and read the stored text. They
are not this package's filters, so Article XII does not reach them, and removing them would be
machinery with no benefit. The guide says it does not cover them.

**ADR:** none — scope.

## D10 — Traps for planning

Recorded so the plan picks them up. None of them is a statement about how to build this.

- SQLite turns an empty text into 0 under an integer cast and PostgreSQL refuses it, so a part that
  is unknown must reach the cast as null on both.
- A filter on `year=9999` must still work however a one-year filter is written, because `10000`
  sorts before `9999` as text.
- `year=990` has to find `0990`, so a year compared as text needs its padding.
- `start` for `0001` must survive each database's own date handling and Django's converters.

**ADR:** none — planning notes.

## D11 — No design preview

The feature changes no screen.

**ADR:** none — a judgement for this feature only.

## D12 — No new terms in `CONTEXT.md`

*Uncertain match*, *period* and *start* already exist. One gap is handled in the guide rather than
the glossary: `1990-06-14` against `lte=1990-06` is not an uncertain match by the glossary's
definition, because its period sits wholly inside the bound's. It is a date inside a coarser bound,
and the expected-results table and the guide state its result directly.

**ADR:** none — vocabulary unchanged.
