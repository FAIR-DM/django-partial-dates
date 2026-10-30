# ADR 0002 — Convert only exact values, and keep a stand-in field for migration history

**Status:** accepted

## Decision

Moving a column from django-partial-date rests on two rules.

**A value converts only if it is exactly what django-partial-date writes.** That is a timestamp at
00:00:00 on 1 January (year), 00:00:01 on the first of a month (month) or 00:00:02 on any date (day),
in the years 0001 to 9999, read in the time zone of the database connection. An empty value stays
empty. `ConvertPartialDateField` checks every value before it changes anything. Any other value
stops the migration with `RefusedValuesError`, and the column and its rows stay as they were. The
same holds on PostgreSQL and SQLite.

**Existing migrations point at `OldPartialDateField`, never at `PartialDateField`.** It is a field
that describes the old column. It stays in the package for good, because a project's migration
history refers to it after the project has uninstalled django-partial-date.

## Why

### What to do with a value that does not fit

Goal G5 says a move loses no data. Three treatments of a value that does not fit were weighed.

| Option | Result |
|---|---|
| Convert to what django-partial-date displays | Rejected. `1990-06-14 00:00:00` displays as `1990`, because its precision setter never clears the month and the day. Converting destroys a day the column holds, and a developer may need it. |
| Skip the value and report it | Rejected. The column then cannot take the check ADR 0001 requires, and a report is easy to miss in a deployment. |
| **Stop the migration** | Chosen. Nothing is lost, and the developer is the only one who can say what the value meant. |

What django-partial-date displays is not evidence of what was recorded, so a value it reads without
complaint is still refused if it holds more than the ISO form can carry. A refused migration
changes nothing, so applying it to a copy of the data is also how a project checks its data.

The time zone follows from the same rule. django-partial-date writes a naive timestamp, so the
database reads it in the connection's zone, and it reads it back the same way. A project whose
settings changed after the rows were written has values that no longer fall on the three stored
times. They are refused, instead of converted a day out.

### What existing migrations point at

| Option | Result |
|---|---|
| Point them at `PartialDateField` | Rejected. The migrations would claim a text column while a deployed database holds a timestamp. On a database behind the latest migration, any pending change that makes SQLite rebuild the table creates the text column with its check, and copying the old values fails. A data migration reading the column fails too. |
| **Keep a field describing the old column** | Chosen. History stays true, so a new database and a deployed one take the same path and differ only in holding rows. Django's own documentation recommends keeping a field class that historical migrations reference. |

The stand-in reports `CharField` from `get_internal_type()`, which does not match its column, on
purpose. Without that, a generated `AlterField` left in the migration casts the timestamps to
`varchar(10)` on PostgreSQL, which truncates them silently, and the check accepts the result:
`1990` becomes `1990-01-01`. With it, PostgreSQL raises an error.

## Revisit if

- A project has to move a table it cannot stop writing to. The check runs before the column changes,
  and a row written between the two is not checked.
- django-partial-date is no longer in use anywhere. The stand-in stays for as long as any project's
  migration history names it.
