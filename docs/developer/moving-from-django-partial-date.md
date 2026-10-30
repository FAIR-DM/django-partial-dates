# Moving from django-partial-date

This page moves a column written by django-partial-date to a `PartialDateField`, keeping every
value. django-partial-date stores a timestamp and hides the precision in its seconds: `1990-01-01
00:00:00` is the year 1990, `1990-06-01 00:00:01` is June 1990 and `1990-06-14 00:00:02` is 14 June
1990. The package gives you one migration operation that rewrites those timestamps as `1990`,
`1990-06` and `1990-06-14`, and one field that lets your existing migrations stop importing
django-partial-date.

The operation converts a value only when it is exactly what django-partial-date writes. Any other
value stops the migration before anything changes. You do the move in the order of the sections
below: point your old migrations at the stand-in, change your models, convert, correct whatever the
conversion refuses, and uninstall django-partial-date.

The examples come from the package's own test app, `moving`, which is at `tests/moving`. Read
`tests.moving` as the Python path of your own app. A code block that names a file under
`tests/moving` is that file, word for word.

## Install this package

Install `django-partial-dates` into the environment your project runs in, before you change
anything.

```console
$ pip install django-partial-dates
```

The [installation page](installation.md) says what the package sets up. Keep it installed after
the move: your migrations refer to it.

## Point existing migrations at the stand-in

Use `OldPartialDateField` in the migrations that created or altered the column, in place of the
field from django-partial-date. It describes the same column, so those migrations still create,
alter and rebuild the table as they did, and the project can uninstall django-partial-date.

1. In each migration that names the old field, change the import and the reference. This is the
   whole edit.

   ```python before-state
   import partial_date.fields

   field = partial_date.fields.PartialDateField(blank=True, null=True)
   ```

   ```python
   import partial_dates.conversion

   field = partial_dates.conversion.OldPartialDateField(blank=True, null=True)
   ```

2. Keep every option the migration passed. `OldPartialDateField` takes any option of Django's
   `Field`, and no `max_length`.

The first migration of the test app creates two models, one with a nullable, indexed field that
has its own `db_column`, and one with a required field:

```python title="tests/moving/migrations/0001_initial.py"
from django.db import migrations, models

import partial_dates.conversion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Sighting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "seen",
                    partial_dates.conversion.OldPartialDateField(
                        blank=True,
                        db_column="seen_on",
                        db_index=True,
                        help_text="When it was seen.",
                        null=True,
                        verbose_name="seen",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Survey",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "taken",
                    partial_dates.conversion.OldPartialDateField(
                        help_text="When the survey was taken.", verbose_name="taken"
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
```

A migration that renames the field or alters one of its options changes in the same way, and
keeps its other operations:

```python title="tests/moving/migrations/0002_rename_and_alter.py"
from django.db import migrations

import partial_dates.conversion


class Migration(migrations.Migration):
    dependencies = [("moving", "0001_initial")]

    operations = [
        migrations.RenameField(
            model_name="sighting", old_name="seen", new_name="observed"
        ),
        migrations.AlterField(
            model_name="sighting",
            name="observed",
            field=partial_dates.conversion.OldPartialDateField(
                blank=True,
                db_column="seen_on",
                db_index=True,
                help_text="When the animal was observed.",
                null=True,
                verbose_name="observed",
            ),
        ),
    ]
```

Use the stand-in in migrations only. A model always declares `PartialDateField`.

## Rebase your own subclass

If your project subclasses django-partial-date's field, change both places that name it.

1. In your migrations, replace the subclass with `OldPartialDateField`, as in the section above.
   The second model in `0001_initial.py` above shows it.
2. In your code, base the subclass on `PartialDateField`.

   ```python before-state
   from partial_date.fields import PartialDateField


   class ProjectDateField(PartialDateField):
       """A project's own subclass of the date field."""
   ```

```python title="tests/moving/fields.py"
from partial_dates import PartialDateField


class ProjectDateField(PartialDateField):
    """A project's own subclass of the date field, as it reads after the move."""
```

3. Check what the subclass overrides. Anything that depended on the old field storing a timestamp
   no longer applies, because the field now stores the ISO form.

## Change the models

Change each model to `PartialDateField`, or to your rebased subclass, with the options the field
already has. Models that inherit the field from an abstract base change in the base, and each
concrete model gets its own conversion in the next section.

```python title="tests/moving/models.py"
from django.db import models

from partial_dates import PartialDateField
from tests.moving.fields import ProjectDateField


class Sighting(models.Model):
    observed = PartialDateField(
        null=True,
        blank=True,
        db_index=True,
        db_column="seen_on",
        verbose_name="observed",
        help_text="When the animal was observed.",
    )
    note = models.CharField(max_length=20, blank=True, db_default="")


class Dated(models.Model):
    taken = ProjectDateField(
        verbose_name="taken", help_text="When the survey was taken."
    )

    class Meta:
        abstract = True


class Survey(Dated):
    note = models.CharField(max_length=20, blank=True, db_default="")
```

## Convert the columns

Use `ConvertPartialDateField` to change a django-partial-date column into a `PartialDateField`
in place. It takes the arguments of Django's own `AlterField`.

1. Make the migration. Django writes an `AlterField` for each change of field.

   ```console
   $ python manage.py makemigrations moving
   ```

2. In the migration Django wrote, change the name of each `AlterField` to
   `ConvertPartialDateField`, and import it. Nothing else changes. The test app's conversion
   does it for one field of each kind:

```python title="tests/moving/migrations/0004_convert_dates.py"
from django.db import migrations

import partial_dates.fields
import tests.moving.fields
from partial_dates.conversion import ConvertPartialDateField


class Migration(migrations.Migration):
    dependencies = [("moving", "0003_add_note")]

    operations = [
        ConvertPartialDateField(
            model_name="sighting",
            name="observed",
            field=partial_dates.fields.PartialDateField(
                blank=True,
                db_column="seen_on",
                db_index=True,
                help_text="When the animal was observed.",
                null=True,
                verbose_name="observed",
            ),
        ),
        ConvertPartialDateField(
            model_name="survey",
            name="taken",
            field=tests.moving.fields.ProjectDateField(
                help_text="When the survey was taken.", verbose_name="taken"
            ),
        ),
    ]
```

3. Apply the migration to a copy of your data first.

   ```console
   $ python manage.py migrate moving
   ```

Every value becomes the ISO form of the partial date it recorded, and every empty value stays
empty. The column then has the type, the check, the indexes and the constraints that a new
`PartialDateField` column has, and `makemigrations` finds nothing more to do. Migrating backwards
restores the timestamp column and the value each row held before.

Do not leave Django's `AlterField` in place of the conversion. On a table that holds rows it fails
with a database error and changes nothing, on PostgreSQL and on SQLite.

Three more things about the migration:

- Leave it atomic, which is Django's default. A refused value stops the migration before anything
  changes either way, but a failure after the conversion's first step, such as a PostgreSQL view
  that depends on the column, leaves everything as it was only in an atomic migration.
- Keep `null` as the old field had it. The conversion changes `null` in its last step, after the
  values are rewritten, so a change that the data refuses comes late. Make a change of `null` in
  its own alteration after the conversion.
- The operation runs on PostgreSQL and SQLite and refuses any other database before it changes
  anything. A database router that excludes the model from a database excludes the conversion
  there too.

## Correct a refused value

When a value in the column is not one that django-partial-date writes, the conversion raises
`RefusedValuesError` before it changes anything. Every row and the column are as they were, so you
can correct the data and run the migration again.

The error has four attributes:

- `model` is the label of the model, such as `moving.Sighting`.
- `field` is the name of the field.
- `count` is the number of refused values in the column.
- `rows` holds the primary key and stored value of the first 20, lowest key first.

1. Read `count` and `rows` in the error the migration printed.

   ```text
   partial_dates.conversion.RefusedValuesError: ('moving.Sighting', 'observed', 2,
   [(2, '1990-06-14 13:45:37'), (7, '1990-06-14 00:00:00')])
   ```

2. Decide what each row should hold. The table below says what each kind of value means.
3. Correct each row, in a shell or in a data migration that runs before the conversion. Write the
   date at one of the three precisions: `YYYY-01-01 00:00:00` for a year, `YYYY-MM-01 00:00:01`
   for a month, `YYYY-MM-DD 00:00:02` for a day. Set the column to `NULL` if the row should hold
   no date.

   ```sql
   UPDATE moving_sighting SET seen_on = '1990-06-14 00:00:02' WHERE id = 2;
   ```

4. Apply the migration again. The count falls with each correction, and the migration completes
   when no value is refused.

| Stored value | What it means | How to correct it |
|---|---|---|
| A time of day, seconds 3 to 59, or a fraction of a second, such as `1990-06-14 13:45:37` | The column holds more than a date, because your project wrote its own timestamps into it. | Write the day it stands for at day precision, or `NULL`. |
| Year precision on a date other than 1 January, such as `1990-06-14 00:00:00` | django-partial-date shows it as `1990`, but the row also holds a month and a day. | Write `1990-01-01 00:00:00` to keep the year, or `1990-06-14 00:00:02` to keep the day. |
| Month precision on a day other than the first, such as `1990-06-14 00:00:01` | django-partial-date shows it as `1990-06`, but the row also holds a day. | Write `1990-06-01 00:00:01` to keep the month, or `1990-06-14 00:00:02` to keep the day. |
| A year outside 0001 to 9999, `infinity`, or a date before the common era (PostgreSQL) | The ISO form cannot hold it. | Write a date inside the range, or `NULL`. |
| Text that is not a timestamp, an impossible date, a number, empty text, or text with an offset (SQLite) | The column holds something other than a date. | Write one of the three precisions, or `NULL`. |

The operation reads each value in the time zone of the database connection, which is the one
django-partial-date used when it wrote it. If your project's time zone settings changed after the
rows were written, a value that no longer falls on 00:00:00, 00:00:01 or 00:00:02 there is refused
instead of converted to a date one day out.

## Uninstall django-partial-date

Once every database you run has applied the conversion, and nothing in your project imports
django-partial-date, remove it.

1. Search your project for what still names it. The search finds `partial_date` and leaves out
   `partial_dates`, this package.

   ```console
   $ grep -rnw partial_date .
   ```

2. Remove django-partial-date from your requirements, then uninstall it.

   ```console
   $ pip uninstall django-partial-date
   ```

3. Check that your migrations load and that Django finds no change to make.

   ```console
   $ python manage.py makemigrations --check --dry-run
   ```

Keep `django-partial-dates` in your requirements. Your migrations import `partial_dates`, and
every new database is built from them.

## Change the code that uses the old value class

django-partial-date's `PartialDate` and this package's `PartialDate` are different classes. The
table says what replaces each name of the old one.

| Old class | What replaces it |
|---|---|
| `PartialDate("1990-06")` | `PartialDate.fromisoformat("1990-06")`. It reads `YYYY`, `YYYY-MM` and `YYYY-MM-DD` and nothing else, so `"1990-6"` raises `ValueError`, which the old class accepted. It raises `ValueError`, not `ValidationError`. |
| `PartialDate(date, precision)` | `PartialDate(date.year)`, `PartialDate(date.year, date.month)` or `PartialDate(date.year, date.month, date.day)`, according to the precision. A part you do not pass is `None`. |
| `.date` | `.start`, the first day of the period, or `.end`, the last. `.year`, `.month` and `.day` hold the recorded parts, and `None` for a part nobody recorded. A value cannot be assigned to. Build a new one. |
| `.precision` | `.precision`, which is a `Precision` member such as `Precision.MONTH`, not the integer 0, 1 or 2. It cannot be assigned to. |
| `PartialDate.YEAR`, `PartialDate.MONTH`, `PartialDate.DAY` | `Precision.YEAR`, `Precision.MONTH` and `Precision.DAY`, from `partial_dates`. They are not integers, so code that stored or computed with 0, 1 and 2 changes. |
| `.precisionYear()`, `.precisionMonth()`, `.precisionDay()` | `.precision is Precision.YEAR`, and likewise for month and day. |
| `.format(year, month, day)` | Nothing yet. Choose the format by `.precision` and apply it to `.start`, as in the example below. |
| `str(value)` | The same ISO form. A year below 1000 is padded, so `str(PartialDate(990))` is `"0990"`. `repr(value)` is no longer the ISO form, so code that showed `repr` uses `str`. |
| `==` | Equal when every part is equal, as before. `1990` is not `1990-01-01`. Values are now hashable, so they work in sets and as dictionary keys. |
| `<`, `<=`, `>`, `>=` | Values sort in the order of their ISO forms, a year before its months and a month before its days. The old class compared date and precision separately, so two values could be neither greater nor smaller. Every pair is ordered now. Comparing with a `date`, a string or an integer raises `TypeError`. |

This example runs each replacement:

```python
from datetime import date

from partial_dates import PartialDate, Precision

year = PartialDate(1990)
month = PartialDate.fromisoformat("1990-06")
day = PartialDate(1990, 6, 14)

assert str(day) == "1990-06-14"
assert (day.year, day.month, day.day) == (1990, 6, 14)
assert day.start == date(1990, 6, 14) == day.end
assert month.precision is Precision.MONTH
assert year.month is None

if month.precision is Precision.MONTH:
    shown = month.start.strftime("%B %Y")
assert shown == "June 1990"

assert year < month < day
assert len({month, PartialDate(1990, 6)}) == 1
```

Queries change in two ways.

- **Ordering stays the same.** Ordering by the field gives the order the old column gave, a year
  before the months of that year and a month before its days. The [querying guide](querying.md)
  says where each database sorts a row holding no date.
- **Filters match what was recorded.** On the old column the `month` and `day` lookups read the
  stored timestamp, so a date known only to the year matched `month=1` and `day=1`. The lookups
  now match a part only on dates that recorded it. The querying guide says what each filter
  includes. A range takes a `PartialDate` or its ISO text as a bound. A `date` or a `datetime`
  raises `ValueError`, and lookups that only a timestamp has, such as `hour`, are gone. The
  `start` transform gives each date as a real date to build them on.

## Check what the move does not cover

Four things need your attention beyond the steps above.

- **A fixture with an unpadded year.** django-partial-date dumps a year below 1000 without its
  leading zero, as `990-03`. That is not an ISO form, and `loaddata` refuses it. Pad the year to
  four digits in the fixture, `0990-03`. Fixtures from years 1000 onwards load unchanged, and so
  do empty values.
- **An earlier data migration that imports the old value class.** Its import fails once
  django-partial-date is gone. Through the stand-in field a historical model gives the stored
  `datetime`, not a value class, and the seconds hold the precision: 0 for the year, 1 for the
  month and 2 for the day. Rewrite the migration to read and write that `datetime`.
- **The lock.** The conversion takes an exclusive lock on the table until the migration ends, so
  nothing else reads or writes it meanwhile. On SQLite it rebuilds the table and locks the
  database for writing. The lock lasts as long as it takes to rewrite every row, so time the
  migration on your copy of the data.
- **Writes during the move.** The check for refused values runs in Python before the conversion,
  and the conversion itself does not repeat it. Stop everything that writes the table from the
  start of the migration until it finishes, so that no row is written after the check. For the
  same reason, never run the output of `sqlmigrate` by itself. It holds the conversion's SQL and
  no check, and run on a value the conversion would refuse it can write a date nobody recorded. Apply
  the migration with `migrate`.

A PostgreSQL view that depends on the column makes the database refuse the change, and the column
stays as it was. Drop the view before the migration and create it again after.

## Why a refused value stops everything

Dropping or rounding a value that holds more than a partial date would lose something only you can
judge. A row such as `1990-06-14 00:00:00` shows as 1990 in django-partial-date, but it also
records a month and a day, and you may need them. So the conversion keeps nothing it has to guess:
it checks every value first, and a single refused value leaves the whole table as it was.
