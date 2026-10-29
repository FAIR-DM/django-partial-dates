# django-partial-dates

[![Tests](https://github.com/FAIR-DM/django-partial-dates/actions/workflows/tests.yml/badge.svg)](https://github.com/FAIR-DM/django-partial-dates/actions/workflows/tests.yml)
[![Build](https://github.com/FAIR-DM/django-partial-dates/actions/workflows/build.yml/badge.svg)](https://github.com/FAIR-DM/django-partial-dates/actions/workflows/build.yml)
[![Publish](https://github.com/FAIR-DM/django-partial-dates/actions/workflows/publish.yml/badge.svg)](https://github.com/FAIR-DM/django-partial-dates/actions/workflows/publish.yml)
[![Coverage](https://codecov.io/gh/FAIR-DM/django-partial-dates/branch/main/graph/badge.svg)](https://codecov.io/gh/FAIR-DM/django-partial-dates)
[![PyPI](https://img.shields.io/pypi/v/django-partial-dates)](https://pypi.org/project/django-partial-dates/)
[![Development status](https://img.shields.io/pypi/status/django-partial-dates)](https://pypi.org/project/django-partial-dates/)
[![Python](https://img.shields.io/pypi/pyversions/django-partial-dates)](https://pypi.org/project/django-partial-dates/)
[![Django](https://img.shields.io/pypi/djversions/django-partial-dates)](https://pypi.org/project/django-partial-dates/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Licence](https://img.shields.io/github/license/FAIR-DM/django-partial-dates)](https://github.com/FAIR-DM/django-partial-dates/blob/main/LICENSE)

A Django model field for dates that are known only to the year, to the month or to the day:
`1990`, `1990-06` or `1990-06-14`.

## Why

Research records are full of dates nobody knows exactly. A sample was collected "in 1990", a
project started "in June 2014", an affiliation ended "some time in 2019". Django's `DateField`
cannot hold any of these without inventing a day and a month, and once it has, nothing can tell
the invented date from a recorded one.

`django-partial-dates` stores a date at the precision it was recorded at, and never more.

## Status

Pre-alpha. The package holds a partial date value so far. The model field is not written yet.

## Usage

A `PartialDate` holds a year and, when they were recorded, a month and a day. A part that was
not recorded is `None`.

```python
>>> from partial_dates import PartialDate, Precision
>>> PartialDate(1990)
PartialDate(year=1990, month=None, day=None)
>>> PartialDate(1990, 6, 14)
PartialDate(year=1990, month=6, day=14)
```

`PartialDate.fromisoformat` reads the three ISO forms, `YYYY`, `YYYY-MM` and `YYYY-MM-DD`, and
nothing else. `isoformat()` writes the form back, and reading it gives an equal value.

```python
>>> value = PartialDate.fromisoformat("1990-06")
>>> value == PartialDate(1990, 6)
True
>>> value.isoformat()
'1990-06'
>>> str(PartialDate(990))
'0990'
```

The `precision` of a value says how much of it was recorded.

```python
>>> value.year, value.month, value.day
(1990, 6, None)
>>> value.precision is Precision.MONTH
True
```

A value is immutable. Building or reading one that is not a date, such as a day without a month,
`1990-02-30` or a year outside 0001 to 9999, raises `ValueError`.

```python
>>> PartialDate.fromisoformat("1990-6")
Traceback (most recent call last):
    ...
ValueError: Not a partial date in ISO form: '1990-6'
```

## Scope and philosophy

**What it is:**

- A model field that stores a year, a year and month, or a full date in one database column.
- A value type for those dates, which sorts, compares and hashes.
- Lookups for filtering on them, and form handling for editing them.

**What it is not:**

- Not a date range. A partial date is one date whose day or month is unknown, not an interval
  with known ends.
- Not a parser for free-text dates such as "spring 1990" or "c. 1850".
- Not a full implementation of EDTF, the Extended Date/Time Format. Its three forms are EDTF
  level 0. Uncertain and approximate dates (`1990?`, `1990~`) are outside its scope.

**When two ways are possible:**

- **Never store what was not recorded.** A partial date is uncertain, and the database holds it as
  uncertain. A stored value never claims a day or a month nobody gave.
- **Uncertain in, uncertain out.** Filters and lookups on partial dates inherit the uncertainty of
  the values. The package documents exactly what each one matches rather than hiding the question.
- **Standard forms over clever encodings.** Values are stored in their ISO 8601 form, so any tool
  reading the database reads them correctly.

## Prior art

This package replaces [django-partial-date](https://github.com/ktowen/django_partial_date), which
has had no release since January 2022. That package stores a partial date as a timestamp with
the precision held in its seconds. [python-edtf](https://github.com/ixc/python-edtf) implements
the whole of EDTF and ships a Django field that needs four extra columns on every model for
filtering and sorting. [ADR 0001](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/adr/0001-store-partial-dates-as-iso-8601-strings.md) records how this package stores a
partial date and why. [Prior art](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/reference/prior-art.md) compares them.

## Licence

MIT. See [LICENSE](https://github.com/FAIR-DM/django-partial-dates/blob/main/LICENSE).
