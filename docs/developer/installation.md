# Installation

This page installs the package and adds a partial date field to a model. You need Python 3.12 or
later, Django 5.2 or later, and a PostgreSQL or SQLite database.

## Install the package

Install `django-partial-dates` into the environment your project runs in.

```console
$ pip install django-partial-dates
```

The package has no app to add to `INSTALLED_APPS`. It brings in Django and nothing else.

## Add the field to a model

Declare `PartialDateField` as you would a `DateField`. It stores one ten-character text column,
holding the date as `YYYY`, `YYYY-MM` or `YYYY-MM-DD`.

```python
from django.db import models

from partial_dates import PartialDateField


class Sample(models.Model):
    collected = PartialDateField(null=True, blank=True, db_index=True)
```

- `null=True` lets a row hold no date. An empty value is stored as `NULL`.
- `db_index=True` adds an index. Whether a column has one stays your decision, and the
  [querying guide](querying.md) says which filters use it.

## Make and apply the migration

```console
$ python manage.py makemigrations
$ python manage.py migrate
```

The migration creates the column and a check on it. The database then refuses any text that is
not a date in one of the three forms, whichever program writes it. On PostgreSQL the column is
also created with byte-order collation, so a database sort of the column is the same sort as
`sorted()` on the values.

You now have a model whose `collected` field takes a `PartialDate` or its ISO text, and gives back
a `PartialDate`. Next, [filter the dates in the database](querying.md).
