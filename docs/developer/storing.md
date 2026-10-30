# Storing a partial date

`PartialDateField` stores a [`PartialDate`](values.md) in one text column. The column holds the ISO
form, so a row read by any other tool shows `1990`, `1990-06` or `1990-06-14`. This page shows how
to save and read a value, how the field treats text that is not a date and empty values, and how to
move dates in and out with fixtures. [Installation](installation.md) covers adding the field to a
model.

The examples use this model.

```python
from django.db import models

from partial_dates import PartialDate, PartialDateField


class Sample(models.Model):
    collected = PartialDateField(null=True, blank=True)
```

## Save and read a value

The field takes a `PartialDate` or its ISO text, and gives back a `PartialDate`.

```python
>>> from partial_dates import PartialDate
>>> sample = Sample.objects.create(collected=PartialDate(1990, 6))
>>> sample.refresh_from_db()
>>> sample.collected
PartialDate(year=1990, month=6, day=None)
```

## Find a row by its exact value

Filtering by a value, or by its ISO text, finds the rows that hold exactly that value. A row
holding `1990-06` is not found by `1990`. [Querying](querying.md) covers filters on a year, a month,
a day or a range.

```python
>>> Sample.objects.filter(collected=PartialDate(1990, 6)).count()
1
>>> Sample.objects.filter(collected="1990-06").count()
1
```

## Handle text that is not a date

Text that is not a partial date is refused when it is saved. `save()`, `create()`, `update()`,
`bulk_create()` and `bulk_update()` raise `ValueError`, and a `datetime.date` or an integer is
refused the same way. `full_clean()` reports it as a `ValidationError` with the code `invalid` on
the field.

```python
>>> Sample.objects.create(collected="1990-6")
Traceback (most recent call last):
    ...
ValueError: Not a partial date in ISO form: '1990-6'
```

## Leave a date empty

An empty value is no date. `None` and `""` are both stored as `NULL` and read back as `None`, so a
field that may be empty is declared with `null=True`, and `blank=True` lets a form leave it out.
Without `null=True` the database refuses a missing date.

## Rely on the check in the database

The database checks the column itself. It refuses any text that is not `YYYY`, `YYYY-MM` or
`YYYY-MM-DD` naming a real date, whichever route writes it: raw SQL, a data migration or another
program. The check is created by the migration of the model that declares the field, and the
package asks for no extra constraint. On PostgreSQL the column is also byte-order collated, so a
database sort of the column is the same sort as `sorted()` on the values.

## Dump and load fixtures

`dumpdata` writes each value as its ISO form and an empty value as empty, and `loaddata` reads them
back unchanged, in JSON, JSON Lines and XML. A fixture can be loaded into the same database or into
the other supported one.

```console
$ python manage.py dumpdata app.Sample --format jsonl > samples.jsonl
$ python manage.py loaddata samples.jsonl
```

```json
{"model": "app.sample", "pk": 1, "fields": {"collected": "1990-06"}}
{"model": "app.sample", "pk": 2, "fields": {"collected": null}}
```

A fixture holding text that is not a partial date, such as `1990-6`, is refused when it is loaded.

## Why a partial date is one text column

[ADR 0001](../adr/0001-store-partial-dates-as-iso-8601-strings.md) records how the package stores a
partial date and why.
