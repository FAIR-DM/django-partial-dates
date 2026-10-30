# Installation

This page installs the package and adds a partial date field to a model. You need Python 3.12 or
later, Django 5.2 or later, and a PostgreSQL or SQLite database.

## Install the package

Install `django-partial-dates` into the environment your project runs in.

```console
$ pip install django-partial-dates
```

The field, the form field, the lookups and `PartialDate.display_form()` need no entry in
`INSTALLED_APPS`. Only the template filter does, because Django finds a tag library through an
installed app. [Showing a partial date](showing.md) says how to add it. The package brings in
Django and nothing else, and its app adds no model and needs no migration.

To filter a list of records with django-filter, install the extra instead:
`pip install "django-partial-dates[django-filter]"`. The [filtering guide](filtering.md) covers
the filters it adds. To expose a partial date through Django REST framework, install the
`djangorestframework` extra: `pip install "django-partial-dates[djangorestframework]"`. The
[Django REST framework guide](rest-framework.md) covers the serializer field it adds.

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

## Fixtures, serialisers and model history

There is nothing to configure for these, and [Storing a partial date](storing.md) shows the
commands. `dumpdata` and `django.core.serializers` write each value
as its ISO form and an empty value as empty, and `loaddata` and `serializers.deserialize` read them
back at the same precision. django-reversion stores its versions through the same serialisers, so
`Version.field_dict`, `Version.revert()` and `Revision.revert()` give back exactly what the version
recorded, empty values included.

You now have a model whose `collected` field takes a `PartialDate` or its ISO text, and gives back
a `PartialDate`. Next, [filter the dates in the database](querying.md).
