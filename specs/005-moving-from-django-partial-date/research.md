# Research — FS-005: Moving from django-partial-date

Django 6.1.2 and 5.2 are the versions the package supports. Line references are to 6.1.2 in the
project's virtual environment. Every claim marked *measured* was run on SQLite and PostgreSQL 17
with a prototype of the operation.

## The conversion cannot be Django's own `AlterField`

*Measured.* An `AlterField` from a field reporting `DateTimeField` to `PartialDateField` issues
`ALTER COLUMN ... TYPE varchar(10) USING col::varchar(10)` on PostgreSQL. An explicit cast to
`varchar(10)` truncates silently, so `1990-01-01 00:00:00` becomes `1990-01-01`, and the check
accepts that. `1990` has become a full date. `postgresql/schema.py`, `_using_sql`, adds the `USING`
when `_field_data_type` of the two fields differ.

On SQLite the same alteration rebuilds the table and the check refuses the first row.

## The stand-in field makes that mistake loud

*Measured.* `_field_data_type` reads `connection.data_types[field.get_internal_type()]`. A stand-in
that reports `CharField` from `get_internal_type()` and returns the timestamp type from `db_type()`
keeps the column it describes, and PostgreSQL then alters with no `USING`. The assignment cast does
not truncate, so the database raises `value too long for type character varying(10)`. The cost is
one method, whose comment says why.

## PostgreSQL steps

`alter_field` cannot take a custom `USING`, so the type change is one raw statement. `alter_field`
does the rest, on fields cloned with `db_index` and `unique` off.

| Step | How |
|---|---|
| Drop the field's own index and unique | `alter_field(old, old without indexes)` |
| Change the type and add the check | One `ALTER TABLE` with `ALTER COLUMN ... TYPE varchar(10) COLLATE "C" USING <expression>` and `ADD CONSTRAINT` |
| Add the field's own index, its `_like` index and unique | `alter_field(new without indexes, new)` |

Three things the steps rest on:

- **A `db_check` is never added by `alter_field`.** *Measured*: the converted column had no check.
  `_alter_field` compares `_field_db_check`, which reads `data_type_check_constraints` for the
  internal type and never calls `Field.db_check` (`base/schema.py:973`, `:1333`). The check is added
  by the raw statement, and dropped by name on the way back.
- **`alter_field` from the old type to the new adds no `_like` index.** A new column with `db_index`
  has one (`_create_like_index_sql`), and `_alter_field` adds it only when the index is added
  (`postgresql/schema.py`). Dropping the index first and adding it last gives the same indexes as
  a new column. *Measured*: column, collation, indexes and check then match a new column, except
  that a unique index is named `..._uniq` rather than `..._key`.
- **Reading the value.** `col::timestamp::text` gives the wall clock in the session's time zone
  with no offset. The session's zone is the one the old field used.

## SQLite steps

SQLite has no `ALTER COLUMN TYPE`. `alter_field` rebuilds the table, and `create_model`'s column
definition carries the check, so a rebuild gives the right column.

Reads need care. Django's SQLite connection parses a column declared `datetime` through a converter
(`sqlite3/base.py:52`, `:163`), so a bare select returns `None` for `''` or junk text. `CAST(col AS
TEXT)` returns what is stored. *Measured by the design review.*

The order matters. *Reasoned from SQLite's affinity rules*: a column declared `datetime` has
NUMERIC affinity, so writing `0990` to it stores the integer 990. The rows are rewritten after the
rebuild into text affinity, and a rebuild with the check would refuse the old rows, so the middle
step is a plain `CharField`.

| Step | How |
|---|---|
| Rebuild to a text column with no check | `alter_field(old without indexes, plain text field)` |
| Rewrite the rows | One `UPDATE` |
| Rebuild with the check and indexes | `alter_field(plain text field, new)` |

*Measured*: the table then matches a new one exactly, and migrating backwards restores every stored
value on both databases.

## Finding refused values

Fetching `pk, stored text` and testing in Python is one implementation for both databases, and it
can use `PartialDate` for "is this a real date in years 0001 to 9999". Doing it in SQL needs a
second predicate per database, and SQLite would need its date function's normalising behaviour
worked around. The conversion rewrites every row anyway, so reading every row does not change its
order of cost. The rows are read with `fetchmany`.

## Squashing

`AlterField.reduce` turns `AlterField(x) + AlterField(y)` into the second, and would let
`squashmigrations` remove a conversion followed by an alteration of the field, losing the
conversion. The operation's `reduce` returns `False`.

## Module name

`partial_dates/migrations.py` is what Django looks for in an installed app, and FS-004 may make the
package an installed app. The module is `partial_dates/conversion.py`.

## What already exists

| Piece | Stopped at | Found |
|---|---|---|
| State change and arguments of the operation | Django | `migrations.AlterField`, subclassed |
| Index, unique and null changes | Django | `schema_editor.alter_field` |
| Rebuilding a SQLite table | Django | `schema_editor.alter_field` |
| Router handling | Django | `allow_migrate_model` |
| Real-date and year-range test | This repo | `PartialDate` |
| The check's SQL | This repo | `PartialDateField.db_check` |
| Constraint name | Django | `django.db.backends.utils.truncate_name` |
| Reading what a stored timestamp means | New code | A regular expression and a method on the operation |
| The type change with a custom `USING` | New code | One `ALTER TABLE` statement, because `alter_field` has no hook for it |
| A field describing the old column | New code | Kept deliberately (ADR); django-partial-date cannot be a dependency (FR-014) |

## Keeping the old package out of the tests

The old column comes from the stand-in field and raw SQL. `decisions.md` records the rows written
through the real field, so no test depends on the old package.
