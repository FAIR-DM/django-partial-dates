# Decisions — FS-002: Storing a partial date on a model

Decisions made while specifying, where the issue and the roadmap were silent. Each was resolved
from the goals, the constitution, ADR 0001, the prior-art notes and FS-001.

## The reading of the issue that the spec is written from

A developer gets a model field for one partial date per row. It takes the partial date value, its
ISO form or `None`, stores the ISO form in one `varchar(10)` column with byte-order collation and
a database check, and gives back the partial date value when a row is read. The database refuses
malformed text whichever route writes it. `dumpdata` and `loaddata` round-trip every value, empty
ones included. It behaves the same on PostgreSQL and SQLite. Lookups and range filters (R3), form
handling and the admin (R4), the move from django-partial-date (R5), display (R6) and model
history (R7) are out of scope, and so is the PostgreSQL job in continuous integration (#9). It
serves G1 and G9.

## D1 — Two stories

Storing and reading values on a model, and moving them in and out with fixtures, are two things a
developer sets out to do. Migrations, empty values, the database check, validation, defaults,
exact-match filtering and the two databases are scenarios under the first. The fixture formats and
cross-database loading are scenarios under the second.

**ADR:** none — how the specification is divided, not a design decision.

## D2 — An empty value is `NULL`, never empty text

Django's text fields store an empty value as empty text. This field stores `NULL` instead, and
treats empty text written through the field as no date. The column then has one way to hold "no
date", the check can refuse empty text outright, and a filter for empty rows has one condition.
It is also what the replaced package's users expect from a date column.

**ADR:** none — a behaviour of the field, stated in the specification.

## D3 — The database check refuses everything the value refuses

The issue asks for "a malformed value" to be refused. A check on the shape alone would let a raw
query store `1990-02-30`, which the field could then not read back. The check therefore matches
FS-001's validation exactly: month 1–12, the day exists in its month and year with Gregorian leap
years, year 0001–9999. How the check is written so that it works on both databases is planning
work.

**ADR:** none — ADR 0001 already requires the check, and this fixes only what it covers.

## D4 — Refused values: the value's error on save, `invalid` on `full_clean()`

Writing an invalid value through the ORM raises the partial date value's own error before any
query runs, as Django's date field does with an unparseable date. `full_clean()` reports it as a
validation error on the field with the code `invalid`, Django's own code for an unparseable value,
because the testing standard asserts validation errors by field and code.

**ADR:** none — follows Django's conventions for a field.

## D5 — Exact-match filtering is in scope, everything else is R3

Exact equality is needed to find a stored row (`get()`, uniqueness) and comes from the field
converting its query value. Ordering, ranges and the `year`, `month`, `day` and `start` lookups,
with what each one matches, are R3's, so this specification makes no promise about them.

**ADR:** none — a scope boundary between roadmap items.

## D6 — Indexing is the developer's decision

Constitution Article IX asks each model field to be a deliberate indexing decision. The package
ships a field, not a model, so it has no query path of its own. The developer indexes it with
`db_index` or `Meta.indexes`, as for any field.

**ADR:** none — the article applies to models a package defines, and this package defines none.

## D7 — Fixture formats: JSON, JSON Lines and XML

These are the formats Django ships without an extra install. R7's line about "JSON produced by
`django.core.serializers`" overlaps with this: `dumpdata` is that serialiser, so this feature
covers it and R7 is left with django-reversion and other model-history tools.

**ADR:** none — a scope boundary between roadmap items.

## D8 — Django becomes a runtime dependency, and FS-001 is rewritten to match

The roadmap makes Django a dependency with the first module that imports it, which is the field.
FS-001 FR-006 and SC-005 say the package has no runtime dependency. They are rewritten in this
pull request to say that the partial date value needs no configured Django settings, which this
specification requires (FR-012).

**ADR:** none — planned in the roadmap.

## D9 — The suite selects its database from the environment

The issue requires the same behaviour on PostgreSQL and SQLite. The continuous integration job for
PostgreSQL is #9, a change under `.github/` handled separately. The test settings select the
database from the environment, so the suite runs against a local PostgreSQL before review and #9
needs only to set the variables.

**ADR:** none — test configuration.

## D10 — No sketch

The feature changes no screen. Until R4 the field appears in forms and the admin however Django
shows a plain text field.

**ADR:** none.

## D11 — The field subclasses `models.Field`, with a `CharField` column

`CharField` adds a length validator that calls `len()` on the cleaned value, which is a partial
date value, and converts every value to text. Subclassing `models.Field` and naming `CharField`
as the internal type gives the `varchar(10)` column on every backend without either (research R1).

**ADR:** none — an implementation choice inside one class, invisible to a developer using it.

## D12 — The collation and the check come from the field, not from the migration

The collation is set per backend in `db_parameters()` and the check is the field's column check,
`db_check()`, which the schema editor writes into the column definition (research R2 and R3).
Neither appears as an argument in a migration, so a developer declares nothing and a second
`makemigrations` finds nothing. Django's `AlterField` never reads a field's own column check, so
changing the check in a later release, or converting an existing column to this field (R5), needs
its own `RunSQL` operation, shipped with that release as Constitution Article XIII asks of storage
changes.

**ADR:** none — ADR 0001 already fixes the collation and the check; this is where Django lets a
field supply them.

## D13 — psycopg 3 as a development dependency

The PostgreSQL run needs a driver. `psycopg[binary]` is added to the development group only, so
projects choose their own driver at runtime.

**ADR:** none — a test-only dependency.

## D14 — Two dispatch groups for US-1

US-1 holds eight tasks over two concerns: the column and its check, then what the field takes in
and gives back. Each group leaves the tree green on its own.

**ADR:** none — how the build is divided.

## D15 — Design review outcome

- DR SPEC-001 (high): a `PartialDate` default could not be written to a migration. `deconstruct()`
  now writes it as its ISO form, tested in T002.
- DR SPEC-002 (medium): SQLite accepted text with an embedded NUL. The SQLite arm of the check
  compares the byte length with the character length, tested in T003.
- DR ARCH-001 (medium): factories, fixtures and the `verbose_name`/`help_text` check the testing
  standard requires are added to T001.
- DR SPEC-003 (low): D12 corrected: `AlterField` never reads the field's check. Watch item for R5.
- DR SPEC-004 (low): the two database runs belong to T010, and T003 reads accepted rows back.
- Notes taken: the import test moves to `tests/test_init.py`, `value_to_string` goes through
  `get_prep_value`, and `Event.on` is renamed `occurred`. The migration records the path
  `partial_dates.fields.PartialDateField`, which is therefore a stable name.

**ADR:** none — corrections to this feature's plan.

## D16 — Choices made during the build

- The check SQL contains no `", "` sequence. Django's SQLite introspection splits a table's SQL
  on it to find the columns, and failed on a check that held one.
- `value_to_string` returns `None` for an empty value, where Django's signature says `str`. The
  serialisers write `None` as empty, which is what US-2 needs, so the override carries a type
  ignore.
- The test settings name `BigAutoField` as the default primary key. Django 6.0 changed the
  default, and without it the test migration differed on Django 5.2.
- The fixture tests compare the output of `dumpdata` with the committed files byte for byte.
  They pass on Django 5.2, 6.0 and 6.1 and on both databases.
- A malformed XML fixture fails with a validation error rather than a deserialisation error, so
  the test accepts either.

**ADR:** none — local to this feature's code and tests.
