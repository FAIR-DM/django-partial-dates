# Feature Specification: Filtering, ordering and grouping partial dates in the database

**Feature Branch**: `003-database-queries`

**Created**: 2026-10-30

**Status**: Draft

**Serves**: G3, G6 · **Roadmap**: R3 · **Issue**: #14 · **Builds on**: FS-001, FS-002

**Input**: A developer querying partial dates needs to filter, order and group them in the
database, without pulling rows into Python: by year, month or day, by a range whose bounds are
themselves partial dates, and by the first day of the period for a chart axis. Uncertain dates are
what make this hard, so the developer also needs to know, before relying on a query, exactly which
uncertain dates it includes. Whether a year-only date matches a filter on June is the kind of
question the documentation has to answer for every lookup, along with worked recipes for June of
any year, a date axis and a year, month and day drilldown.

## Summary

The queries a developer runs on a partial date field. `year`, `month` and `day` lookups read the
recorded parts in `filter`, `exclude`, `values`, `annotate` and `order_by`. A `start` transform
gives the first day of the period as a real date, for a chart axis. Range filters take partial
dates as their bounds, and ordering by the field gives the same order as sorting the values in
Python. All of it runs in the database, with the same results on PostgreSQL and SQLite.

Uncertainty is stated, not resolved. A filter asks about recorded parts and about the order of
the ISO form, as ADR 0001 records, so a date that might or might not be what the filter asks for
has one defined result. A developer guide says what that result is for every lookup, and shows how
to write the other rule where a query needs it.

Out of scope, each owned elsewhere:

- the form field, the widget and the admin (R4)
- converting a column written by django-partial-date (R5)
- showing a partial date to a reader, and template filters (R6)
- round trips through django-reversion and other model-history tools (R7)
- ready-made django-filter filters and Django REST framework serializer fields (R8)

The words used here are defined in `CONTEXT.md`. `1990`, `1990-06` and `1990-06-14` stand for
partial dates at year, month and day precision.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A developer filters partial dates, knowing which uncertain dates each filter includes (Priority: P1)

A developer narrows a queryset by year, by month, by day, or by a range whose bounds are partial
dates, in the database. Before relying on a filter, they read in the guide exactly which uncertain
dates it includes, and where a query needs the other rule, they write it from a recipe.

**Why this priority**: Filtering is what a stored date is for, and it is where an uncertain date
can silently change an answer. A query is only useful once the developer knows what it left out.

**Independent Test**: On each database, load a grid of values at each precision around one bound,
plus rows holding no date, and compare what each filter returns with the expected results below.

**Acceptance Scenarios**:

1. **Given** rows holding `1990`, `1990-06`, `1990-06-14` and `1991`, **When** the developer filters
   by `year=1990`, **Then** the first three are found, because every partial date has a recorded
   year.
2. **Given** the same rows, **When** the developer filters by `month=6`, **Then** `1990-06` and
   `1990-06-14` are found, and `1990` is not, because its month is unknown.
3. **Given** the same rows, **When** the developer filters by `day=14`, **Then** only `1990-06-14`
   is found, and `1990` and `1990-06` are not, because their day is unknown.
4. **Given** a filter on a part combined with a comparison, such as `month__gte=6`, `month__in` with
   6, 7 and 8, or `year__range` with 1990 and 2000, **When** the developer runs it, **Then** it
   compares the recorded part as a number, and a date with that part unknown is never found.
5. **Given** a field that allows no date, **When** the developer filters by `month__isnull=True`,
   **Then** rows at year precision and rows holding no date are found, and with
   `month__isnull=False`, rows at month and day precision are found. `day__isnull` does the same
   for the day, so a query can select by precision.
6. **Given** rows at each precision, **When** the developer calls `exclude(month=6)`, **Then**
   `1990` is not returned, so a date whose month is unknown is in neither `filter(month=6)` nor
   `exclude(month=6)`. The same holds for `day`.
7. **Given** a part that no date can hold, such as `month=13`, `day=32`, `year=0` or `year=10000`,
   **When** the developer filters by it, **Then** no row is found and no error is raised.
8. **Given** rows holding `0001`, `0990` and `9999-12-31`, **When** the developer filters by
   `year=1`, `year=990` and `year=9999`, **Then** each finds its own row.
9. **Given** a bound as a partial date value or its ISO form, **When** the developer filters with
   `gt`, `gte`, `lt`, `lte` or `range`, **Then** each row is compared by the order of the ISO form,
   the same order as sorting the values in Python, as the expected results below set out.
10. **Given** a `range` whose two bounds differ in precision, or mix a partial date value and an
    ISO form, **When** the developer filters by it, **Then** it finds the same rows as `gte` of the
    first and `lte` of the second. A `range` whose first bound sorts after its second finds no row.
11. **Given** a list of partial date values or ISO forms, **When** the developer filters by `in`,
    **Then** exactly the rows equal to one of them are found, so `1990` does not find `1990-06`.
12. **Given** a bound that is not a partial date, such as `1990-6`, a real date or a number, **When**
    the developer filters with `gt`, `gte`, `lt`, `lte`, `range` or `in`, **Then** it is refused
    with the partial date value's own error before any query runs.
13. **Given** a row holding no date, **When** the developer filters by a part or by a bound, **Then**
    the row is not found.
14. **Given** a field that allows no date, **When** the developer calls `exclude` with a part or a
    bound, **Then** a row holding no date is returned, as Django does for any field that allows
    null.
15. **Given** a column with an index, **When** the developer filters by a range or by `year`,
    **Then** the database uses the index.
16. **Given** any filter in this story, **When** the developer reads the guide, **Then** the guide
    states which uncertain dates it includes, for a value at each precision on both sides of a
    bound, and each stated result is what the filter returns.
17. **Given** the guide, **When** the developer follows the recipe for June of any year, **Then** it
    finds rows at month and day precision in June of every year, and states that year-only dates
    are left out.
18. **Given** a range, **When** the developer follows the guide's recipes for the other rule, **Then**
    they can add every uncertain date to the range, leave every uncertain date out of it, and take
    in the whole of the month or year named by an upper bound, each with the package's own filters.
19. **Given** any of the scenarios above, **When** the suite runs against PostgreSQL and against
    SQLite, **Then** each gives the same result on both.

**Expected results for a bound of `1990-06`.** The rows are in sort order. `1990` is the uncertain
match: its period is partly inside and partly outside what each filter asks for.

| Row | `gt` | `gte` | `lt` | `lte` |
|---|---|---|---|---|
| `1990` | no | no | yes | yes |
| `1990-05` | no | no | yes | yes |
| `1990-05-31` | no | no | yes | yes |
| `1990-06` | no | yes | no | yes |
| `1990-06-01` | yes | yes | no | no |
| `1990-06-14` | yes | yes | no | no |
| `1990-07` | yes | yes | no | no |
| `1991` | yes | yes | no | no |

**The same rule at the other two precisions of bound.**

| Bound | Row | `gte` | `lte` |
|---|---|---|---|
| `1990` | `1990` | yes | yes |
| `1990` | `1990-06` | yes | no |
| `1990` | `1990-06-14` | yes | no |
| `1990-06-14` | `1990` | no | yes |
| `1990-06-14` | `1990-06` | no | yes |
| `1990-06-14` | `1990-06-14` | yes | yes |

---

### User Story 2 - A developer orders and groups partial dates, for lists, drilldowns and chart axes (Priority: P2)

A developer orders a queryset by the field, counts rows by year, month and day to build a
drilldown, and uses the first day of each date's period to put rows on a date axis, all in the
database. The guide shows where a year-only date lands in each of these.

**Why this priority**: It builds on the parts from US-1. Lists, summaries and charts are the next
thing a site does with stored dates, and they need the same honesty about dates at each precision.

**Independent Test**: On each database, load rows at each precision, order them and compare with
`sorted()`, group them and compare the counts, and compare each `start` with the value's own.

**Acceptance Scenarios**:

1. **Given** rows at each precision, **When** the developer orders by the field, **Then** the rows
   come back in the order `sorted()` gives the values, so `1990`, `1990-06`, `1990-06-14`, `1991`.
   Ordering by `-field` gives the reverse.
2. **Given** rows holding no date, **When** the developer orders with `nulls_first` or `nulls_last`,
   **Then** those rows come first or last on both databases.
3. **Given** rows at each precision, **When** the developer selects `year`, `month` or `day` with
   `values`, `values_list` or `annotate`, **Then** each is a whole number equal to that part of the
   partial date value, and `None` where the part is unknown or the row holds no date.
4. **Given** rows at each precision, **When** the developer groups by `year` and counts, **Then**
   every row with a date is counted under its year.
5. **Given** rows at each precision, **When** the developer groups by `year` and `month` and counts,
   **Then** rows at year precision form their own group with no month for that year, and are never
   counted under a month. Grouping by `year`, `month` and `day` does the same for rows at month
   precision.
6. **Given** rows at each precision, **When** the developer orders by `year`, `month` or `day`,
   **Then** the rows come back in the numeric order of that part.
7. **Given** rows at each precision, **When** the developer selects `start` with `values`,
   `values_list` or `annotate`, **Then** each is a real date equal to the partial date value's own
   `start`, and `None` where the row holds no date.
8. **Given** rows at each precision, **When** the developer groups by `start` and counts, **Then**
   `1990`, `1990-01` and `1990-01-01` are all counted on 1 January 1990.
9. **Given** a real date, **When** the developer filters by `start` with `exact`, `gt`, `gte`, `lt`,
   `lte` or `range`, **Then** each row is compared by the first day of its period, so `1990` counts
   as 1 January 1990.
10. **Given** rows at each precision, **When** the developer orders by `start`, **Then** the rows
    come back by the first day of their period. Rows sharing a first day have no guaranteed order
    between them until the field is added as a second key.
11. **Given** the earliest and latest values and a leap day, `0001`, `9999-12-31` and `2000-02-29`,
    **When** the developer selects `start`, **Then** each gives the real date the value gives.
12. **Given** a column with an index, **When** the developer orders by the field, **Then** the
    database uses the index.
13. **Given** the guide, **When** the developer follows the recipe for a date axis, **Then** it gives
    counts by the first day of the period, and states where year-only and month-only dates land and
    how to leave them out.
14. **Given** the guide, **When** the developer follows the recipe for a year, month and day
    drilldown, **Then** each level gives its counts, and it states that a date stays at the level of
    its own precision.
15. **Given** any of the scenarios above, **When** the suite runs against PostgreSQL and against
    SQLite, **Then** each gives the same result on both, with one exception: an ordering that names
    neither `nulls_first` nor `nulls_last` leaves rows holding no date where each database puts
    them, and the guide states where that is.

---

### Edge Cases

- A date's day is compared as a number, so `day=1` finds `1990-06-01` and not `1990-06`.
- A year-only date on a chart axis sits on 1 January. That is the first day of its period, not a
  claim about when it happened, and the date axis recipe says so.
- Comparing the two forms of one date is not equality: `1990-06` and `1990-06-01` are different
  values, and `gt` of `1990-06` finds `1990-06-01`. `start` is the query that treats them alike.
- An upper bound names a position in the sort order, not a period, so `lte=1990-06` finds `1990-06`
  and not `1990-06-14`. The guide gives `lt=1990-07` and `lte=1990-06-30` as the way to take in the
  whole month.
- A model with several partial date fields can filter, order and group on each of them.

## Clarifications

### Session 2026-10-30

- Q: What does a bound at month or year precision mean? → A: A position in the sort order, the
  comparison ADR 0001 records and the order `PartialDate` already sorts in. Every filter and every
  sort then agree. `lte=1990-06` therefore finds `1990` and leaves out `1990-06-14`. The guide says
  so, and gives the recipe for taking in the whole month.
- Q: What do uncertain matches do at a bound? → A: A date whose period contains the bound sorts
  before the bound, so it is left out of `gt` and `gte` and included in `lt` and `lte`.
- Q: What does `exclude` do with an unknown part? → A: SQL's rule stands: the part is unknown, so
  the row is in neither `filter(month=6)` nor `exclude(month=6)`. Saying that a year-only date is
  not in June would claim something nobody recorded. A developer who wants those rows asks for them
  with `month__isnull=True`.
- Q: Where do rows holding no date sort? → A: Where each database puts nulls, as for every Django
  field, because the package cannot change it for a plain `order_by`. PostgreSQL and SQLite differ.
  `nulls_first` and `nulls_last` give one answer on both, and the guide says to use them.
- Q: Does a filter accept a real date as a bound? → A: No. A real date is refused by the field, as
  FS-002 set out, because it carries a day that may never have been recorded. A real date is
  compared through `start`, where the rule is stated: the first day of the period.
- Q: Is there an `end` transform or a `precision` lookup? → A: No. The roadmap names `start` alone,
  and `month__isnull` and `day__isnull` already select by precision. Nothing in this feature needs
  either.
- Q: What about the text lookups Django gives every field, such as `contains`, `startswith` and
  `regex`? → A: They stay as Django gives them, and they read the stored text. The guide lists them
  as outside what it covers, and points to the filters above.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (US1): The field MUST provide `year`, `month` and `day` lookups taking a whole number,
  which match rows whose recorded part equals it. A date with that part unknown MUST NOT match.
- **FR-002** (US1): The `year`, `month` and `day` lookups MUST combine with Django's numeric
  comparisons (`gt`, `gte`, `lt`, `lte`, `in`, `range`) and with `isnull`, which is true where the
  part is unknown.
- **FR-003** (US1): A date with the part unknown MUST be returned by neither a filter on that part
  nor its `exclude`. A row holding no date MUST behave as Django's `exclude` does for a nullable
  field.
- **FR-004** (US1): A whole number outside the values a part can hold MUST match nothing, and MUST
  raise no error.
- **FR-005** (US1): The field's `gt`, `gte`, `lt`, `lte` and `range` filters MUST accept a partial
  date value or its ISO form as a bound, in any mix of precisions, and MUST compare by the order of
  the ISO form, which MUST be the order `PartialDate` sorts in.
- **FR-006** (US1): The `in` filter MUST accept partial date values and ISO forms, and MUST match
  only rows equal to one of them.
- **FR-007** (US1): A bound or list member that is not a partial date MUST be refused with the
  partial date value's own error before any query runs.
- **FR-008** (US1): A filter on one year, and a range filter, on an indexed column MUST use the
  index on both databases.
- **FR-009** (US2): Ordering by the field MUST give the order `sorted()` gives the values.
- **FR-010** (US2): `year`, `month` and `day` MUST be usable in `values`, `values_list`, `annotate`,
  and `order_by`, MUST give a whole number, and MUST give `None` where the part is unknown or the
  row holds no date. Grouping by them MUST keep a date at the level of its own precision.
- **FR-011** (US2): The field MUST provide a `start` transform giving the first day of the period
  as a real date, equal to the partial date value's own `start`, or `None` for a row holding no
  date. It MUST be usable in `values`, `values_list`, `annotate`, `order_by` and `filter`, where it
  takes a real date with `exact`, `gt`, `gte`, `lt`, `lte` and `range`.
- **FR-012** (US2): Ordering by the field on an indexed column MUST use the index on both databases.
- **FR-013** (US1, US2): Every lookup, filter and transform in this specification MUST run in the
  database, and MUST give the same result on PostgreSQL and on SQLite, apart from where rows
  holding no date sort when an ordering does not say.
- **FR-014** (US1): A developer guide MUST state, for every filter in this specification, which
  uncertain matches it includes, for a value at each precision on both sides of a bound. It MUST
  say what `exclude` does with an unknown part and with a row holding no date, and which of
  Django's text lookups it does not cover.
- **FR-015** (US1): The guide MUST include recipes for June of any year, adding every uncertain date
  to a range, leaving every uncertain date out of a range, and taking in the whole of the month or
  year named by an upper bound.
- **FR-016** (US2): The guide MUST state what ordering, grouping and `start` do with dates at each
  precision, where each database sorts a row holding no date, and how to say which, and MUST
  include recipes for a date axis and for a year, month and day drilldown.
- **FR-017** (US1, US2): Every example in the guide MUST run against the package and give the result
  the guide states.

### Key Entities

- **Lookup on a recorded part**: `year`, `month` or `day`, read from the stored ISO form in the
  database. Unknown where the partial date does not hold that part.
- **`start` transform**: the first day of a partial date's period as a real date, derived when the
  query runs and never stored.
- **Bound**: the partial date a range filter compares each row with, by the order of the ISO form.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every filter, a value at each precision on both sides of each boundary gives the
  result the expected-results tables state, on both databases.
- **SC-002**: From the guide alone, a developer can say whether any filter includes any value at
  any precision, and every such statement matches what the filter returns.
- **SC-003**: For every value stored, `year`, `month`, `day` and `start` from the database equal the
  attributes of the partial date value read in Python.
- **SC-004**: Ordering by the field gives the same order as `sorted()` on every set of values
  tested, on both databases.
- **SC-005**: Each filter, ordering and grouping in this specification runs as one query and
  returns only the rows or groups it asks for, so no developer has to load rows to work out a
  result.
- **SC-006**: The three recipes the issue names, June of any year, a date axis and a year, month and
  day drilldown, run from the guide as written and give the results it states.

## Assumptions

- The developer uses Django 5.2 LTS or the current stable release, on PostgreSQL or SQLite, as the
  constitution's stack article sets out.
- Partial date columns hold what FS-002 lets them hold: the ISO form or no value. The filters are
  not written to cope with other text.
- Whether a column is indexed stays the developer's decision, as FS-002 set out. The index
  requirements apply when one exists.
- The package replaces Django's `Trunc` and `Extract` with these lookups, as ADR 0001 records. The
  admin's `date_hierarchy` stays unavailable, because it accepts only Django's own date fields.
