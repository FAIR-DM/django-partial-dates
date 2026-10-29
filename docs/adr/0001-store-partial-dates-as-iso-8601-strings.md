# ADR 0001 — Store partial dates as ISO 8601 strings in one column

**Status:** accepted

## Decision

A partial date is stored as its ISO 8601 form, in one text column and nothing else:

| Precision | Stored as | Example |
|---|---|---|
| Year | `YYYY` | `1990` |
| Month | `YYYY-MM` | `1990-06` |
| Day | `YYYY-MM-DD` | `1990-06-14` |

- The column is a `varchar(10)`. Its collation compares text byte by byte, which is PostgreSQL's
  `C` collation. The field sets this itself.
- The field adds no companion columns, and asks the model to declare none.
- A part that was not recorded is not stored. Nothing fills it with a first day or a first month.
- The years are four digits, 0001 to 9999.
- These three forms are EDTF level 0 (ISO 8601-2). Nothing else is accepted.

## Why

### A partial date is uncertain, and the column must say so

A value recorded as "1990" means a single day somewhere in 1990. Nobody knows which day. Any
storage that writes a day or a month into the column claims a certainty the data does not have.
Someone reading the database, or another tool reading it, takes 1990-01-01 for a recorded
1 January.

Four ways of storing a partial date were weighed against that.

| Option | Why it was rejected |
|---|---|
| A timestamp with the precision held in its seconds | Stores a day and a month nobody recorded (`1990-01-01 00:00:00`). The precision can be read only through the field's own code. The column is time-zone aware, so Django's `__year`, `__month` and `__date` lookups convert to the current time zone first. On a site west of UTC, a value stored as 1990 then matches `__year=1989`. |
| A date column and a precision column | Honest about the precision, but Django has no field that spans two columns. It needs a hidden companion field added to every model, and two fields in every migration. |
| A start date and an end date, or a PostgreSQL `daterange` | Turns an uncertain date into an interval whose ends look certain. A reader of `1990-01-01 – 1990-12-31` cannot tell it from a recorded interval. It needs a hidden companion column, or works only on PostgreSQL. |
| **The ISO 8601 string** | Chosen. |

### What the string gives

- **It is the standard form.** DataCite, schema.org and CSL JSON all accept these three forms as
  they are, so exporting a value needs no conversion.
- **Text order is date order.** Every part is fixed-width and zero-padded, so comparing two
  values as text orders them chronologically. `order_by`, `gte` and `lte` in SQL give the same
  order as the value type in Python. A year sorts before the months in it, and a month before the
  days in it: `1990`, `1990-06`, `1990-06-14`, `1991`.
- **Range filters work on one indexed column.** "Collected between June 1990 and 23 September
  2020" is `value >= '1990-06' AND value <= '2020-09-23'`, an index range scan.
- **No time zone is involved.** The column holds no time, so no lookup converts it.
- **It reads correctly everywhere.** In the database, in `dumpdata`, in django-reversion's
  history and in any tool that reads the table.

### What a filter on a partial date means

A filter compares strings, and partial dates are uncertain, so some matches are uncertain too.
This package documents what each filter matches rather than hiding the question behind a stored
range. With the range above:

- `1990-06-14` and `2020-09` are inside it.
- `1990` is outside it, because `'1990' < '1990-06'`. The sample might have been collected in
  July 1990, or in March.
- `2020` is inside it, because `'2020' <= '2020-09-23'`. The sample might have been collected in
  December 2020.

A developer who needs a different rule writes it with the lookups the package provides.

### Queries beyond ranges

| Need | How |
|---|---|
| Records from June of any year | A `__month` lookup reading characters 6–7. A year-only value has no month, so it never matches. |
| A date axis on a chart | A `__start` lookup, giving the first day of the period as a real `date` in the database. In Python the value type gives the first and last day of its period. |
| A year → month → day drilldown | Grouping by the `__year` and `__month` lookups. A year-only value stays at the year level and never appears under a month. |

Two things Django provides for date columns are lost:

- The admin's `date_hierarchy`, which accepts only `DateField` and `DateTimeField`.
- Django's own `Trunc` and `Extract` functions, which this package replaces with its own lookups.

### Performance

Measured on PostgreSQL 17 with 5,000,000 rows, a third each at year, month and day precision,
1900–2025, one B-tree index on each column, no parallel workers. A timestamp column stored the
way the replaced package stored it is the baseline.

| Query | Timestamp | ISO string |
|---|---|---|
| June 1990 to 23 September 2020 (1.2 million matches) | 303 ms | 310 ms |
| One month (2,126 matches) | 10 ms | 10 ms |
| The year 2020 | 98 ms | 105 ms |
| June of any year | 1,297 ms | 933 ms |
| Counts per month across a decade | 309 ms | 325 ms |
| Counts per year across the whole table | 1,715 ms | 1,445 ms |
| The newest 50 | 0.4 ms | 0.3 ms |
| The first day of every row | 964 ms | 2,177 ms |
| Size on disk, with the index | 207 MB | 220 MB |

- Range, year and sorting queries use the index in both.
- "June of any year" reads the whole table in both, as Django's `__month` does on a real date.
- Converting every row to a real date is the one slower case. A chart that groups by month or
  year first does not pay it.
- The string column was measured with the `C` collation. A prefix match such as
  `LIKE '2020%'` uses the index only when the column compares text byte by byte. Under a
  language-aware collation such as `en_US.UTF-8`, PostgreSQL cannot use the index for it. Byte
  order is also the only order guaranteed to match date order. This is why the field sets the
  `C` collation itself. SQLite compares byte by byte by default.

## Revisit if

- Uncertain or approximate dates come into scope (`1990?`, `1990~`). The column holds them
  without a schema change, but text order would no longer match date order.
- Years before 0001 or after 9999 are needed. Text order breaks once a year is not four digits.
- A backend this package supports cannot use an index for a prefix range on a text column.
