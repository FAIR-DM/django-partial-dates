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

Pre-alpha. The package holds a partial date value and a model field that stores it, and the
field filters, orders, selects and groups by year, month, day and range in the database. A form
field and widget enter a partial date as a year, a month and a day select. The model field gives
them to model forms and the admin, so there is nothing to configure. A migration operation converts
a column written by django-partial-date.

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

Values sort in the order of their ISO forms, so a year comes before its months and a month before
its days. Two values are equal when all their parts are equal: `1990` is not `1990-01-01`.

```python
>>> values = [
...     PartialDate(1991),
...     PartialDate(1990, 6, 14),
...     PartialDate(1990),
...     PartialDate(1990, 6),
... ]
>>> [value.isoformat() for value in sorted(values)]
['1990', '1990-06', '1990-06-14', '1991']
>>> PartialDate(1990) == PartialDate(1990, 1, 1)
False
```

Values are hashable, so they work as set members and dictionary keys. A value is never equal to a
`datetime.date`, a string or an integer, and ordering against one raises `TypeError`.

```python
>>> len({PartialDate(1990, 6), PartialDate.fromisoformat("1990-06")})
1
>>> counts = {PartialDate(1990, 6): 3}
>>> counts[PartialDate.fromisoformat("1990-06")]
3
```

A value covers a period. `start` and `end` give its first and last day as `datetime.date`
objects, with the last day of February worked out for the year.

```python
>>> PartialDate(1990).start, PartialDate(1990).end
(datetime.date(1990, 1, 1), datetime.date(1990, 12, 31))
>>> PartialDate(2000, 2).end
datetime.date(2000, 2, 29)
>>> PartialDate(1990, 6, 14).start == PartialDate(1990, 6, 14).end
True
```

`relation_to` says whether the period of one value is `Relation.BEFORE`, `Relation.AFTER` or
`Relation.OVERLAPPING` the period of another. Sorting and "is this one earlier?" are different
questions: `1990` sorts before `1990-06`, but the two overlap, so neither is earlier. Passing
anything but a `PartialDate` raises `TypeError`.

```python
>>> from partial_dates import Relation
>>> PartialDate(1990, 6).relation_to(PartialDate(1991)) is Relation.BEFORE
True
>>> PartialDate(1991).relation_to(PartialDate(1990, 6)) is Relation.AFTER
True
>>> PartialDate(1990).relation_to(PartialDate(1990, 6)) is Relation.OVERLAPPING
True
>>> PartialDate(1990) < PartialDate(1990, 6)
True
```

## Model field

`PartialDateField` stores a `PartialDate` in one text column. Declare it as you would a
`DateField`.

```python
from django.db import models

from partial_dates import PartialDate, PartialDateField


class Sample(models.Model):
    collected = PartialDateField(null=True, blank=True)
```

The field takes a `PartialDate` or its ISO text, and gives back a `PartialDate`. The column
holds the ISO form, so a row read by any other tool shows `1990`, `1990-06` or `1990-06-14`.

```python
>>> sample = Sample.objects.create(collected=PartialDate(1990, 6))
>>> sample.refresh_from_db()
>>> sample.collected
PartialDate(year=1990, month=6, day=None)
```

Filtering by a value, or by its ISO text, finds the rows that hold exactly that value. A row
holding `1990-06` is not found by `1990`.

```python
>>> Sample.objects.filter(collected=PartialDate(1990, 6)).count()
1
>>> Sample.objects.filter(collected="1990-06").count()
1
```

Text that is not a partial date is refused when it is saved. `save()`, `create()`, `update()`,
`bulk_create()` and `bulk_update()` raise `ValueError`, and a `datetime.date` or an integer is
refused the same way. `full_clean()` reports it as a `ValidationError` with the code `invalid`
on the field.

```python
>>> Sample.objects.create(collected="1990-6")
Traceback (most recent call last):
    ...
ValueError: Not a partial date in ISO form: '1990-6'
```

An empty value is no date. `None` and `""` are both stored as `NULL` and read back as `None`,
so a field that may be empty is declared with `null=True`, and `blank=True` lets a form leave
it out. Without `null=True` the database refuses a missing date.

The database checks the column itself. It refuses any text that is not `YYYY`, `YYYY-MM` or
`YYYY-MM-DD` naming a real date, whichever route writes it: raw SQL, a data migration or
another program. The check is created by the migration of the model that declares the field,
and the package asks for no extra constraint. On PostgreSQL the column is also byte-order
collated, so a database sort of the column is the same sort as `sorted()` on the values.

### Fixtures

`dumpdata` writes each value as its ISO form and an empty value as empty, and `loaddata` reads
them back unchanged, in JSON, JSON Lines and XML. A fixture can be loaded into the same database
or into the other supported one.

```console
$ python manage.py dumpdata app.Sample --format jsonl > samples.jsonl
$ python manage.py loaddata samples.jsonl
```

```json
{"model": "app.sample", "pk": 1, "fields": {"collected": "1990-06"}}
{"model": "app.sample", "pk": 2, "fields": {"collected": null}}
```

A fixture holding text that is not a partial date, such as `1990-6`, is refused when it is loaded.

## Forms

`partial_dates.forms.PartialDateField` enters a partial date in a form, with a year, a month and
a day select. The user gives the parts they know and leaves the rest empty. It needs no entry in
`INSTALLED_APPS` and no JavaScript.

```python
>>> from django import forms
>>> from partial_dates.forms import PartialDateField
>>> class EventForm(forms.Form):
...     happened = PartialDateField()
>>> form = EventForm({"happened_year": "1990", "happened_month": "6", "happened_day": ""})
>>> form.is_valid()
True
>>> form.cleaned_data["happened"]
PartialDate(year=1990, month=6, day=None)
```

A model form and the admin show the same selects for a `PartialDateField`, with no form or widget
to declare. The field's `blank`, `verbose_name`, `help_text`, default and `unique` carry over. With
nothing said, the year select lists the years from the current year down to 1900, and
`PartialDateWidget(years=...)` names others.

A day without a month is refused with the error code `incomplete`, never dropped, and a date that
does not exist is refused with `invalid`. A form opened on a stored date selects exactly the parts
it records. The
[forms guide](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/developer/forms.md)
says what each error means, how to limit the dates with a validator, and how to try the field in
the example project on localhost.

## Querying

The field filters in the database by the year, month and day of a date, and by a range whose
bounds are partial dates. It orders by the date, selects and counts by each part, and gives each
date as a real date for a chart axis. A date that might or might not match a filter has one
defined result.

```python
Sample.objects.filter(collected__month=6)  # 1990-06 and 1990-06-14, but not 1990
Sample.objects.filter(collected__gte="1990-06", collected__lt="1991")
Sample.objects.order_by(F("collected").asc(nulls_last=True))
Sample.objects.values_list("collected__year").annotate(total=Count("pk"))
Sample.objects.values_list("collected__start")  # 1990 is date(1990, 1, 1)
```

The [querying guide](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/developer/querying.md)
says which uncertain dates each filter includes, and gives recipes for June of any year, a date
axis, a drilldown from year to day, and the other rules a range can follow. It also says where
each database sorts a row holding no date, and how to choose.

## Filtering with django-filter

Install the `django-filter` extra to filter a list of records by a partial date. The extra adds
django-filter and nothing else, and the core package never imports it.

```console
$ pip install "django-partial-dates[django-filter]"
```

```python
import django_filters

from partial_dates.filters import PartialDateFilter, PartialDateRangeFilter


class SampleFilter(django_filters.FilterSet):
    collected = PartialDateFilter()
    when = PartialDateRangeFilter(field_name="collected")
```

A person sees the year, month and day selects and gives as much of the date as they know, and an
API client sends the ISO form, as in `?when_after=1990-06&when_before=1991-03`. An entry that is
not a partial date is reported as an error on the filter. The range includes the whole of the
period its second bound names, so `1991-03` takes in `1991-03-15`. The
[filtering guide](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/developer/filtering.md)
says which uncertain dates each filter includes, how to filter on a year, month or day and across
a relation, and how to ask for another rule.

## Django REST framework

Install the `djangorestframework` extra to read and write a partial date in an API. The extra
adds Django REST framework and nothing else, and the core package never imports it.

```console
$ pip install "django-partial-dates[djangorestframework]"
```

```python
from rest_framework import serializers

from partial_dates.rest_framework import PartialDateField


class SampleSerializer(serializers.Serializer):
    collected = PartialDateField()
```

A client reads `1990`, `1990-06` or `1990-06-14`, or `null` when a record has no date, and writes
the same text. Anything else, including an empty string, is reported as a validation error with
the code `invalid`. The
[Django REST framework guide](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/developer/rest-framework.md)
shows how to save the value with a `ModelSerializer`, how to require a date, and how to use the
field across a project.

## Moving from django-partial-date

`ConvertPartialDateField` converts a column written by django-partial-date to a
`PartialDateField` in place, on PostgreSQL and SQLite, and keeps every value. It stops before
changing anything when a value is not exactly what django-partial-date writes. The
[guide to the move](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/developer/moving-from-django-partial-date.md)
takes you through changing your existing migrations, converting the columns and uninstalling
django-partial-date.

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
has had no release since January 2022. That package stores a partial date as a timestamp with
the precision held in its seconds. [python-edtf](https://github.com/ixc/python-edtf) implements
the whole of EDTF and ships a Django field that needs four extra columns on every model for
filtering and sorting. [ADR 0001](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/adr/0001-store-partial-dates-as-iso-8601-strings.md) records how this package stores a
partial date and why. [Prior art](https://github.com/FAIR-DM/django-partial-dates/blob/main/docs/reference/prior-art.md) compares them.

## Licence

MIT. See [LICENSE](https://github.com/FAIR-DM/django-partial-dates/blob/main/LICENSE).
