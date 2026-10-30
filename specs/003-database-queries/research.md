# Research: Filtering, ordering and grouping partial dates in the database

Everything below was run on SQLite and on PostgreSQL 17, on Django 6.1, with a trial version of
the lookups against a table holding `0001`, `0990`, `1990`, `1990-01`, `1990-01-01`, `1990-06`,
`1990-06-14`, `1991`, `2000-02-29`, `9999-12-31` and one empty row. Both databases gave the same
rows for every filter.

There are no planning notes for this feature.

## R1 — What already works, and needs only proof

The field inherits Django's `exact`, `gt`, `gte`, `lt`, `lte`, `in`, `range` and `isnull`, and each
one takes its value through `PartialDateField.get_prep_value` (`partial_dates/fields.py:172`).

- `gte`, `lte` and `range` compare by the order of the ISO form, and order and `sorted()` agree.
- A `PartialDate` and an ISO form both work as a bound, in any mix.
- A bound that is not a partial date raises `ValueError` before the query runs, in `gte`, `in` and
  `range`.
- `exclude(gte=...)` returns rows holding no date, through Django's null guard
  (`django/db/models/sql/query.py`, `Query.build_filter`).

So FR-005, FR-006, FR-007 and FR-009 need tests and documentation, and no code. FR-009 and FR-012
rest on the column's collation from FS-002.

## R2 — `year`, `month` and `day`

`Transform` subclasses registered on the field, each with a `template` and an `output_field` of
`IntegerField()`, which is how Django's own `Length` transform is written
(`django/db/models/functions/text.py`).

| Transform | SQL |
|---|---|
| `year` | `CAST(SUBSTR(col, 1, 4) AS INTEGER)` |
| `month` | `CAST(NULLIF(SUBSTR(col, 6, 2), '') AS INTEGER)` |
| `day` | `CAST(NULLIF(SUBSTR(col, 9, 2), '') AS INTEGER)` |

- `SUBSTR` past the end of the text gives empty text on both databases. `NULLIF` turns it into
  `NULL`. Without it, SQLite would cast it to 0 and PostgreSQL would raise (decisions D10).
- A `NULL` column gives `NULL`.
- The SQL carries literals and no parameters, so PostgreSQL treats the select and the `GROUP BY` as
  one expression.
- Django's numeric lookups come from `IntegerField`, `isnull` from `Field`.
- `exclude(month=6)` becomes `NOT (expr = 6 AND col IS NOT NULL)`. On a year-only row that is
  `NOT NULL`, which is not true, so the row stays out. On an empty row it is `NOT FALSE`, so the
  row is returned. Both match US-1 scenarios 6 and 14, on both databases.

## R3 — A one-year filter that uses the index

`CAST(SUBSTR(...))` reads every row. Django solves the same problem for dates with `YearLookup`
(`django/db/models/lookups.py:712`), which compares the column with a pair of bounds when the value
is a plain one.

An `exact` lookup registered on `Year` does the same: `col BETWEEN '1990' AND '1990-99'`, built with
`f"{year:04d}"`.

- Every form of a year sorts inside those bounds, including `1990-12-31`.
- Year 9999 works, because the upper bound is `9999-99` and not `10000` (decisions D10).
- `year=990` looks for `0990`.
- `year=0`, `year=10000` and `year=-1` find nothing and raise nothing.
- A value that is not plain, such as `F("other__year")`, falls back to `Exact`.

Plans read back from the trial:

| Query | SQLite | PostgreSQL, sequential scans off |
|---|---|---|
| `year=1990` | `SEARCH ... USING COVERING INDEX` | `Bitmap Heap Scan`, `Bitmap Index Scan` |
| `gte` and `lte` | `SEARCH ... USING COVERING INDEX` | `Bitmap Heap Scan`, `Bitmap Index Scan` |
| `month=6` | `SCAN` | `Seq Scan` |
| `order_by` | `SCAN ... USING COVERING INDEX` | `Index Scan` |

`YearLookup` itself is not subclassed. It reads date bounds from the database backend and is not a
documented extension point, while `Lookup.as_sql` is.

`year__gte` and the other comparisons stay on the transform. Only equality has an index promise
(decisions D8).

## R4 — `start`

`Transform` with `output_field = DateField()`.

- `SUBSTR(col || '-01-01', 1, 10)` gives `1990-01-01`, `1990-06-01` and `1990-06-14` for the three
  forms, and refers to the column once.
- PostgreSQL needs `CAST(... AS DATE)`. On SQLite a date is text, and `CAST AS DATE` would give a
  number, so `as_sqlite` leaves the cast out. Django's converter for `DateField` reads the text
  back as a `datetime.date`.
- `0001`, `9999-12-31` and `2000-02-29` come back as the same dates `PartialDate.start` gives, on
  both databases.
- `DateField`'s own lookups give `exact`, `gt`, `gte`, `lt`, `lte` and `range`.

## R5 — Where lookups live, and how they register

`partial_dates/lookups.py` holds the classes and imports nothing from `fields.py`. `fields.py`
registers them after the class. `partial_dates/__init__.py` already imports `fields`, so a project
that imports the field gets its lookups. A module of its own keeps `fields.py` about storage, and
`tests/test_lookups.py` mirrors it.

Importing `partial_dates` still needs no configured settings, because Django's lookup classes import
without them. `tests/test_init.py` covers this already.

## R6 — Running every guide example

FR-017 asks that every example runs, and README-style `>>>` blocks suit that. `doctest.DocTestParser`
reads examples out of the fenced blocks, because a closing fence would otherwise be taken for
expected output, and one `DocTestRunner` runs them with shared names against rows from a fixture.

The two tables of results in the guide are read by the same test and compared with the filters, so
a statement in the guide cannot drift from what a filter returns (SC-002).

Examples must print the same on both databases, so every example that can meet an empty value or an
unknown part orders with `nulls_first` or `nulls_last`, or filters the empty rows out.

## R7 — Documentation layout

This is the package's first guide, so `docs/` takes the shape `documentation.md` sets out: a
homepage, `developer/` with its index, the installation page, and one page for this feature titled
"Querying". The repository has no documentation build, so no reference pages are generated, and
the guide page holds the list of lookups.

## What already exists

```
gt, gte, lt, lte, range, in on the field · 4, Django · Field lookups, through get_prep_value
isnull on a part                         · 4, Django · Transform inherits Field's IsNull
numeric comparisons on a part            · 4, Django · IntegerField lookups, via output_field
ordering by the field                    · 2, repo   · C collation from FS-002 (fields.py:69)
nulls placement                          · 4, Django · F().asc(nulls_first=, nulls_last=)
query plans in tests                     · 4, Django · QuerySet.explain()
running guide examples                   · 4, stdlib · doctest.DocTestParser, DocTestRunner
year, month and day transforms           · 7, new    · searched fields.py, ExtractYear (needs a date)
one-year filter on the index             · 7, new    · searched YearLookup, undocumented, date bounds
start transform                          · 7, new    · searched Cast, Concat, TruncDate (need a date)
guide page and test                      · 7, new    · searched docs/, no guide exists
homepage, guide index, installation page · 7, new    · documentation.md 3, 4; searched docs/
query_plan test fixture                  · 7, new    · searched conftest.py, explain() needs seqscan off
Sample test model and factory            · 7, new    · searched tests/models.py, field names read badly
```
