# Django Partial Dates

A Django model field for dates that are known only to the year, to the month or to the day:
`1990`, `1990-06` or `1990-06-14`. It stores a date at the precision it was recorded at and never
holds a part nobody gave.

## Features

- [Store a partial date](developer/index.md) in one text column, as its ISO form.
- [Filter partial dates](developer/querying.md) by year, month, day or a range, in the database,
  knowing which uncertain dates each filter includes.
- [Order, select and group partial dates](developer/querying.md#order-by-the-date) by the date
  or by one of its parts, and put them on a date axis with `start`.
- [Enter a partial date](developer/forms.md) in a model form, the admin or a plain form, with a
  year, a month and a day select, giving as much of the date as the user knows.

## Requirements

- Python 3.12 or later
- Django 5.2 or later
- PostgreSQL or SQLite

## Installation

1. Install the package.

   ```console
   $ pip install django-partial-dates
   ```

2. Declare the field on a model.

   ```python
   from django.db import models

   from partial_dates import PartialDateField


   class Sample(models.Model):
       collected = PartialDateField(null=True, blank=True, db_index=True)
   ```

3. Make and apply the migration.

   ```console
   $ python manage.py makemigrations
   $ python manage.py migrate
   ```

The [installation page](developer/installation.md) says what each step sets up.

## Example

```python
from partial_dates import PartialDate

Sample.objects.create(collected=PartialDate(1990, 6))
Sample.objects.filter(collected__month=6)
```

The first line stores `1990-06`. The second finds every sample collected in a June, and leaves
out samples whose month nobody recorded.

## Next steps

- [Developer guide](developer/index.md): store and query partial dates from Python.
- [Reference](reference/prior-art.md): the packages this one replaces, and why.

## About the project

- [Goals](https://github.com/FAIR-DM/django-partial-dates/blob/main/GOALS.md): what the package
  works toward.
- [Domain model](https://github.com/FAIR-DM/django-partial-dates/blob/main/CONTEXT.md): the
  words the project uses.
- [Constitution](https://github.com/FAIR-DM/django-partial-dates/blob/main/CONSTITUTION.md): the
  rules every change follows.
- [Changelog](https://github.com/FAIR-DM/django-partial-dates/blob/main/CHANGELOG.md): what
  changed in each release.

## Support

Report a problem or ask a question in the
[issue tracker](https://github.com/FAIR-DM/django-partial-dates/issues).

## Licence

MIT. See the
[licence](https://github.com/FAIR-DM/django-partial-dates/blob/main/LICENSE).
