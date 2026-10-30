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
`1990`, `1990-06` or `1990-06-14`. It stores a date at the precision it was recorded at, and never
more.

**Documentation: <https://django-partial-dates.fairdm.org>**

## Why

Research records are full of dates nobody knows exactly. A sample was collected "in 1990", a
project started "in June 2014", an affiliation ended "some time in 2019". Django's `DateField`
cannot hold any of these without inventing a day and a month, and once it has, nothing can tell
the invented date from a recorded one.

## Quickstart

The package is pre-alpha. It needs Python 3.12 or later, Django 5.2 or later, and PostgreSQL or
SQLite.

```console
$ pip install django-partial-dates
```

Declare the field on a model, then make and apply the migration.

```python
from django.db import models

from partial_dates import PartialDateField


class Sample(models.Model):
    collected = PartialDateField(null=True, blank=True, db_index=True)
```

```python
from partial_dates import PartialDate

Sample.objects.create(collected=PartialDate(1990, 6))
Sample.objects.filter(collected__month=6)
```

The first line stores `1990-06`. The second finds every sample collected in a June, and leaves out
samples whose month nobody recorded.

## Features

- [A value for Python code](https://django-partial-dates.fairdm.org/developer/values.html) that sorts, compares, hashes and says
  which period it covers.
- [A model field](https://django-partial-dates.fairdm.org/developer/storing.html) that stores the ISO form in one text column,
  with the database refusing anything else.
- [Filtering, ordering and grouping](https://django-partial-dates.fairdm.org/developer/querying.html) by year, month, day or
  range, in the database, knowing which uncertain dates each filter includes.
- [A form field](https://django-partial-dates.fairdm.org/developer/forms.html) with year, month and day selects, in model forms
  and the admin with nothing to configure.
- [Display text](https://django-partial-dates.fairdm.org/developer/showing.html) at the recorded precision, in the reader's
  language.
- [Ready-made django-filter filters](https://django-partial-dates.fairdm.org/developer/filtering.html), with the `django-filter`
  extra.
- [A Django REST framework field](https://django-partial-dates.fairdm.org/developer/rest-framework.html), with the
  `djangorestframework` extra.
- [A migration from django-partial-date](https://django-partial-dates.fairdm.org/developer/moving-from-django-partial-date.html)
  that converts a column in place and keeps every value.

## Scope and philosophy

**What it is:**

- A model field that stores a year, a year and month, or a full date in one database column.
- A value type for those dates, which sorts, compares and hashes.
- Lookups for filtering on them, and a form field and widget for editing them, in model forms
  and the admin as well as plain forms.

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
has had no release since January 2022. The [prior art page](https://django-partial-dates.fairdm.org/reference/prior-art.html)
compares the alternatives.

## Licence

MIT. See [LICENSE](https://github.com/FAIR-DM/django-partial-dates/blob/main/LICENSE).
