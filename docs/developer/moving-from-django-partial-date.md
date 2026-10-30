# Moving from django-partial-date

This page moves a column written by django-partial-date to a `PartialDateField`, keeping every
value. django-partial-date stores a timestamp and hides the precision in its seconds: `1990-01-01
00:00:00` is the year 1990, `1990-06-01 00:00:01` is June 1990 and `1990-06-14 00:00:02` is 14 June
1990. The package gives you one migration operation that rewrites those timestamps as `1990`,
`1990-06` and `1990-06-14`, and one field that lets your existing migrations stop importing
django-partial-date.

The operation converts a value only when it is exactly what django-partial-date writes. Any other
value stops the migration before anything changes. You use the page in this order: convert, point
your old migrations at the stand-in, and correct whatever the conversion refuses.

## Convert a column

Use `ConvertPartialDateField` to change a django-partial-date column into a `PartialDateField`
in place. It takes the arguments of Django's own `AlterField`.

1. Change the field on the model to `PartialDateField`, with the options it already has.

   ```python
   from django.db import models

   from partial_dates import PartialDateField


   class Sighting(models.Model):
       seen = PartialDateField(null=True, blank=True)
   ```

2. Make the migration. Django writes an `AlterField` for the change of field.

   ```console
   $ python manage.py makemigrations sightings
   ```

3. In the migration Django wrote, change the name of the operation to
   `ConvertPartialDateField`, and import it. Nothing else changes.

   ```python
   from django.db import migrations

   from partial_dates import PartialDateField
   from partial_dates.conversion import ConvertPartialDateField


   class Migration(migrations.Migration):
       dependencies = [("sightings", "0003_sighting_note")]

       operations = [
           ConvertPartialDateField(
               model_name="sighting",
               name="seen",
               field=PartialDateField(blank=True, null=True),
           ),
       ]
   ```

4. Apply the migration to a copy of your data first.

   ```console
   $ python manage.py migrate sightings
   ```

Every value becomes the ISO form of the partial date it recorded, and every empty value stays
empty. The column then has the type, the check, the indexes and the constraints that a new
`PartialDateField` column has, and `makemigrations` finds nothing more to do. Migrating backwards
restores the timestamp column and the value each row held before.

Do not leave Django's `AlterField` in place of the conversion. On a table that holds rows it fails
with a database error and changes nothing, on PostgreSQL and on SQLite.

The operation runs on PostgreSQL and SQLite and refuses any other database before it changes
anything. A database router that excludes the model from a database excludes the conversion
there too.

## Point existing migrations at the stand-in

Use `OldPartialDateField` in the migrations that created or altered the column, in place of the
field from django-partial-date. It describes the same column, so those migrations still create,
alter and rebuild the table as they did, and the project can uninstall django-partial-date.

1. In each migration that names the old field, change the import and the reference.

   ```python
   # Before
   import partial_date.fields

   field = partial_date.fields.PartialDateField(blank=True, null=True)
   ```

   ```python
   # After
   import partial_dates.conversion

   field = partial_dates.conversion.OldPartialDateField(blank=True, null=True)
   ```

2. Keep every option the migration passed. `OldPartialDateField` takes any option of Django's
   `Field`, and no `max_length`.

Use the stand-in in migrations only. A model always declares `PartialDateField`.

## Correct a refused value

When a value in the column is not one that django-partial-date writes, the conversion raises
`RefusedValuesError` before it changes anything. Every row and the column are as they were, so you
can correct the data and run the migration again.

The error has four attributes:

- `model` is the label of the model, such as `sightings.Sighting`.
- `field` is the name of the field.
- `count` is the number of refused values in the column.
- `rows` holds the primary key and stored value of the first 20, lowest key first.

1. Read `count` and `rows` in the error the migration printed.

   ```text
   partial_dates.conversion.RefusedValuesError: ('sightings.Sighting', 'seen', 2,
   [(2, '1990-06-14 13:45:37'), (7, '1990-06-14 00:00:00')])
   ```

2. Decide what each row should hold. The table below says what each kind of value means.
3. Correct each row, in a shell or in a data migration that runs before the conversion. Write the
   date at one of the three precisions: `YYYY-01-01 00:00:00` for a year, `YYYY-MM-01 00:00:01`
   for a month, `YYYY-MM-DD 00:00:02` for a day. Set the column to `NULL` if the row should hold
   no date.

   ```sql
   UPDATE sightings_sighting SET seen = '1990-06-14 00:00:02' WHERE id = 2;
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

## Why a refused value stops everything

Dropping or rounding a value that holds more than a partial date would lose something only you can
judge. A row such as `1990-06-14 00:00:00` shows as 1990 in django-partial-date, but it also
records a month and a day, and you may need them. So the conversion keeps nothing it has to guess:
it checks every value first, and a single refused value leaves the whole table as it was.
