# Decisions — FS-005: Moving from django-partial-date

Decisions made while specifying, where the issue and the roadmap were silent. Each was resolved
from the goals, the constitution, ADR 0001, FS-002, the source of django-partial-date 1.3.2, and
its two known users.

## The reading of the issue that the spec is written from

A developer whose project stores dates with django-partial-date gets one migration operation that
converts an existing column in place to the column FS-002 defines, on PostgreSQL and SQLite, losing
no value, and a how-to guide to the move that includes stopping the existing migrations importing
the old package. It serves G5. Forms and the admin (R4), history tools (R7), and the changes to
FAIR-DM and django-literature themselves are out of scope. Every assumption made in that
reading is recorded here.

## What the old column holds

Read from the 1.3.2 source, then confirmed by writing rows through its field on SQLite and
PostgreSQL 17, with `USE_TZ` on and off.

| Fact | Evidence |
|---|---|
| The column is `timestamp with time zone` on PostgreSQL, `datetime` on SQLite | `get_internal_type()` returns `DateTimeField`, and the columns were inspected |
| The precision is the seconds: 0 year, 1 month, 2 day | `get_prep_value` builds `datetime(y, m, d, second=precision)` |
| SQLite holds text, `1990-06-14 00:00:02`, and years pad to four digits | `typeof()` on the written rows |
| A value is written naive, with no conversion | The field overrides `get_prep_value` only, so the database applies the connection's time zone |
| With `USE_TZ` on, that zone is UTC, whatever `TIME_ZONE` says | The session time zone with `TIME_ZONE = America/New_York` was UTC |
| With `USE_TZ` off, that zone is `TIME_ZONE`, offsets with seconds included | Under `Europe/Berlin`, 1800 was stored at `+00:53:28` and read back correctly |
| An empty value, `None` or `""`, is `NULL` | `get_prep_value`, and the written rows |
| Seconds other than 0, 1 and 2 are read as day precision | The precision setter falls back to `DAY`. `1990-06-14 13:45:37` read as `1990-06-14` |
| Year precision can hold a real month and day | The setter calls `date.replace()` and discards the result. `PartialDate(date(1990, 6, 14), PartialDate.YEAR)` stored `1990-06-14 00:00:00` and read as `1990` |
| A year below 1000 is displayed unpadded | `strftime("%Y")` gave `990-03`, which is what a fixture holds |

## D1 — Two stories

Converting a column, and removing the package from a project, are two things a developer sets out
to do. Precision, empty values, refusals, time zones, rollback and the two databases are scenarios
under the first. The existing migrations and the guide are under the second, because the guide
exists to get a project to the point where the old package is gone. Both are P1: G5 is not met
until the old package can be uninstalled.

**ADR:** none — how the specification is divided, not a design decision.

## D2 — A value converts only if it is exactly what the old field writes, and anything else stops the migration

The issue says no value is lost, and G5 says the same. Three treatments of an unclean value were
considered: convert to what the old field displays, skip it and report, or stop. Converting
destroys what the column held beyond the ISO form, which is the loss G5 rules out. Skipping leaves a
column that cannot be given FS-002's check. Stopping loses nothing and costs the developer a
correction, and only they can say what a value meant. The rule is the same on both databases.

**ADR:** docs/adr/0002-convert-exactly-and-keep-a-stand-in-field.md

## D3 — What the old field displays is not the test

`1990-06-14 00:00:00` shows as `1990`, and `1990-06-14 13:45:37` shows as `1990-06-14`. Both are
refused, though the old field reads them without complaint. The first can be written through that
package's Python interface, because its precision setter does nothing, so a real month and day may
sit under it. In the code read, both known users build their values from text, so neither should meet this
refusal.

**ADR:** docs/adr/0002-convert-exactly-and-keep-a-stand-in-field.md

## D4 — The operation reads in the connection's time zone

The connection's zone is the one the old field wrote and read in, so reading there gives the same
date it gave. ADR 0001's warning about the old column is about Django's `__year` lookups, which
convert to the current time zone, and the conversion uses neither those nor the current time zone.
A project whose settings changed after its rows were written has stored times that no longer fall
on the three stored times, and D2 refuses them, instead of converting them a day out.

**ADR:** docs/adr/0002-convert-exactly-and-keep-a-stand-in-field.md

## D5 — Existing migrations point at a stand-in field

Two ways to stop existing migrations importing the old package were considered.

- **Swap them to this package's field.** Rejected. The migrations would then claim a text column
  while a deployed database holds a timestamp. On a database behind the latest migration, any
  pending change that makes SQLite rebuild the table creates the text column with its check, and
  the copy of the old values fails. A data migration reading the column would fail as well.
- **Keep a field that describes the old column.** Chosen. History stays true, so every database
  takes the same path, and a new database and a deployed one differ only in holding rows. Django's
  own documentation recommends keeping a field class that historical migrations reference.

The spec names what the developer sees. The field's name and the shape of the edit are for the plan.

**ADR:** docs/adr/0002-convert-exactly-and-keep-a-stand-in-field.md

## D6 — The operation takes the arguments of Django's field alteration

`makemigrations` writes an `AlterField` for the change of field. If the operation takes the same
arguments, the developer's edit to a generated migration is one word, and the migration state gets
the field's options from the same place.

**ADR:** none — the shape of one operation's arguments, stated in the spec.

## D7 — The conversion is reversible

The issue does not ask for it. A deployment that goes wrong needs to roll back, and every ISO form
maps back to exactly one stored value, so the cost is small. It restores the stored values
exactly, because D2 means nothing was dropped on the way in.

**ADR:** none — behaviour stated in the spec, with no alternative that lasts.

## D8 — No separate check command

A refused migration changes nothing, so applying it to a copy of the data is the check. A separate
command would be a second implementation of FR-002 (Article II).

**ADR:** none — something not built, recorded here so it is not asked again.

## D9 — The guide includes what a project's own code changes

The issue names migrations, and `docs/ROADMAP.md` lists them. A developer also has to replace the old
value class, and both known users call it directly (`PartialDate("2019")`, `.date`, `.precision`,
`PartialDate.YEAR`). The move is not finished without it, so the guide lists the replacements. The
package adds no compatibility layer for them.

**ADR:** none — the content of a guide.

## D10 — No prototype

This feature changes no screens, so no prototype is made.

**ADR:** none — nothing downstream inherits it.

## D11 — The stand-in field reports `CharField` to Django's schema editor

A generated `AlterField` left in place of the conversion would otherwise cut every PostgreSQL value
to ten characters, and the check accepts the result, so `1990` would silently become `1990-01-01`.
Reporting `CharField` removes the `USING` cast, and PostgreSQL then raises an error instead. It was
measured on both databases (`research.md`). It is one method and it costs nothing else, because the
field is only ever read from migration history.

**ADR:** docs/adr/0002-convert-exactly-and-keep-a-stand-in-field.md

## D12 — The middle step of the conversion is a plain `CharField`

A subclass with no check would be a public name frozen into nothing. `models.CharField(max_length=10)`
is the same column. Added from the design review.

**ADR:** none — local to the operation.

## D13 — The Python check is the guard against truncation

The design review pointed out that the rewrite expression truncates a value that gets past the
check, through the output of `sqlmigrate` or a row written between the check and the `ALTER`. An
expression that raises on its own needs a different failure trick per database, for a route a
developer has to choose. The guide says the output of `sqlmigrate` carries no check, and that
writes stop during the move. Revisit if a project needs to move a table it cannot stop writing to.

**ADR:** none — recorded here with its reason to revisit.
