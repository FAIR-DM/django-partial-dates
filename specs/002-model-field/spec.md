# Feature Specification: Storing a partial date on a model

**Feature Branch**: `002-model-field`

**Created**: 2026-10-30

**Status**: Draft

**Serves**: G1, G9 · **Roadmap**: R2 · **Issue**: #8 · **Builds on**: FS-001

**Input**: A developer building a Django model needs a field that stores a partial date exactly as
it was recorded: a year, a year and month, or a full date, and nothing more. The field should
accept the partial date value, an ISO string or nothing, and give back the partial date value when
the row is read. The database itself should refuse a malformed value however it is written, so bad
data cannot get in through a raw query or a bulk update. Fixtures written with `dumpdata` should
load back with `loaddata` unchanged, empty values included, which the package this one replaces
gets wrong. The field has to behave the same on PostgreSQL and SQLite, because projects develop on
one and deploy on the other.

## Summary

A model field for a partial date. A developer adds it to a model, migrates, and stores a partial
date at year, month or day precision, or no date at all. The field takes the partial date value
from FS-001, its ISO form or `None`, and gives back the partial date value whenever a row is read.
The column holds the ISO form and nothing else, as ADR 0001 records, and the database refuses any
other text whichever route writes it. Fixtures written with `dumpdata` load back unchanged with
`loaddata`, empty values included. The field behaves the same on PostgreSQL and SQLite.

The value type itself is FS-001 and is not restated here. Out of scope, each owned elsewhere:

- lookups, transforms, range filters and what ordering by the field means (R3)
- the form field, the widget and the admin (R4)
- converting a column written by django-partial-date (R5)
- showing a partial date to a reader, and template filters (R6)
- round trips through django-reversion and other model-history tools (R7)
- running the suite against PostgreSQL in continuous integration (#9)

The words used here are defined in `CONTEXT.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A developer stores a partial date on a model (Priority: P1)

A developer adds a partial date field to a model, makes and applies its migration, then saves rows
holding partial dates at each precision, or no date where the field allows it, and reads back
partial date values. The database holds exactly the ISO form that was recorded, and refuses any
other text however it is written, so a raw query or a bulk update cannot put a malformed value in
the table. It all behaves the same on PostgreSQL and on SQLite.

**Why this priority**: It is the field. Every later item, from lookups to forms to the move from
django-partial-date, stores and reads values through it.

**Independent Test**: On each database, migrate a test model with the field, save values at each
precision through every write route, read them back, and try to write malformed text through the
ORM and through raw SQL.

**Acceptance Scenarios**:

1. **Given** a model with a partial date field, **When** the developer makes its migration and
   applies it, **Then** the column is created holding text of at most ten characters, compared
   byte by byte, with a check that refuses malformed values, and the developer has declared no
   constraint, collation or extra column for it.
2. **Given** the migration already made, **When** the developer makes migrations again with
   nothing changed, **Then** no new migration is made.
3. **Given** a partial date value at year, month or day precision, **When** the developer saves it
   and reads the row back, **Then** the field gives back an equal partial date value, and the
   column holds its ISO form.
4. **Given** the ISO form `1990`, `1990-06` or `1990-06-14` as text, **When** the developer saves
   it, **Then** reading the row back gives the partial date value it stands for.
5. **Given** a field that allows no date, **When** the developer saves `None`, **Then** the column
   holds no value and reading the row back gives `None`.
6. **Given** a field that allows no date, **When** the developer saves empty text, **Then** it is
   stored as no date, the same as `None`, and the column never holds empty text.
7. **Given** a field that requires a date, **When** the developer saves a row without one, **Then**
   the database refuses the row.
8. **Given** text that is not a partial date in ISO form, or a value of another type such as a real
   date or a number, **When** the developer writes it through the ORM, by saving an instance or
   through `create()`, `update()`, `bulk_create()` or `bulk_update()`, **Then** it is refused
   before anything is written, and the rows keep their previous values.
9. **Given** an instance holding text that is not a partial date, **When** the developer validates
   the instance with `full_clean()`, **Then** the error is attached to the field and carries the
   code `invalid`.
10. **Given** a valid instance holding an ISO form as text, **When** the developer validates it with
    `full_clean()`, **Then** the field's value on the instance becomes the partial date value.
11. **Given** each text the partial date value refuses (an unpadded part, a month outside 1–12, a
    day that does not exist in its month such as `1990-02-30` or `1900-02-29`, the year `0000`, a
    time, an EDTF level 1 marker, surrounding spaces), and empty text, **When** it is written to
    the column by raw SQL, **Then** the database refuses the write.
12. **Given** each valid ISO form, including `0001`, `9999-12-31` and `2000-02-29`, **When** it is
    written to the column by raw SQL, **Then** the database accepts it and the field reads it back
    as the partial date value.
13. **Given** a partial date value or its ISO form, **When** the developer filters for rows exactly
    equal to it, **Then** exactly the rows holding that value at that precision are found, so
    `1990` does not find `1990-01-01`.
14. **Given** a default set on the field as a partial date value or its ISO form, **When** the
    developer saves a row without giving a value, **Then** the row holds the default.
15. **Given** any of the scenarios above, **When** the suite runs against PostgreSQL and against
    SQLite, **Then** each gives the same result on both.

---

### User Story 2 - A developer moves partial dates in and out with fixtures (Priority: P2)

A developer writes the rows of a model with a partial date field to a fixture with `dumpdata`, and
loads that fixture with `loaddata`, into the same database or the other supported one. Every value
comes back unchanged, empty values included.

**Why this priority**: The package this one replaces cannot serialise an empty value, which breaks
`dumpdata` and the tools built on Django's serialisers. Fixtures are how projects seed test data
and move records between a development database and a deployed one.

**Independent Test**: Dump rows holding values at each precision and empty values in each of
Django's built-in fixture formats, flush, load, and compare.

**Acceptance Scenarios**:

1. **Given** rows holding values at year, month and day precision, **When** the developer runs
   `dumpdata`, **Then** each value is written as its ISO form.
2. **Given** a row whose field holds no date, **When** the developer runs `dumpdata`, **Then** the
   value is written as empty, and the command does not fail.
3. **Given** a fixture written by `dumpdata` from those rows, **When** the developer runs
   `loaddata` into an empty database, **Then** every row reads back with an equal partial date
   value, and every empty value reads back as `None`.
4. **Given** a fixture written by hand holding ISO forms as text, **When** the developer loads it,
   **Then** the rows hold the partial date values those forms stand for.
5. **Given** a fixture holding text that is not a partial date, **When** the developer loads it,
   **Then** loading fails and no row holds the malformed text.
6. **Given** each fixture format Django ships without an extra install (JSON, JSON Lines and XML),
   **When** the developer dumps and loads with it, **Then** scenarios 1 to 5 hold.
7. **Given** a fixture dumped from SQLite, **When** the developer loads it into PostgreSQL, or the
   other way round, **Then** every value reads back unchanged.

---

### Edge Cases

- The earliest and latest values, `0001` and `9999-12-31`, store, read, dump and load without
  error on both databases.
- A year below 1000 is stored with four digits (`0990`), and text written without the leading zero
  (`990`) is refused by every route.
- Exact-match filtering compares the ISO form, so values of different precision are never equal,
  which matches the partial date value's own equality.
- A model may hold several partial date fields. Each gets its own column and its own check, and
  their names do not collide.

## Clarifications

### Session 2026-10-30

- Q: What does an empty value look like in the column? → A: The column holds no value (`NULL`).
  Empty text is stored as no date, the same as `None`, and the check refuses empty text in the
  column. A field has one way to say "no date", so a filter for empty rows never has to ask for two.
- Q: What does the database check refuse? → A: Everything the partial date value refuses, not only
  the shape: a month outside 1–12, a day that does not exist in its month and year, leap years
  included, and a year outside 0001–9999. A narrower check would let a raw query store text the
  field cannot read back.
- Q: When an invalid value is written through the ORM, what does the developer see? → A: The
  partial date value's own refusal, raised before the query runs. `full_clean()` turns it into a
  validation error on the field with the code `invalid`. Raw SQL that bypasses the field meets the
  database check, which raises the database's integrity error.
- Q: Does the field give back the partial date value straight after assignment? → A: It behaves as
  Django's own date field does. A value read from the database is always a partial date value.
  Text assigned to an instance stays as assigned until the instance is validated or read back.
- Q: Is any querying in scope? → A: Exact-match filtering only, which finding a stored row needs.
  Ordering, ranges, the `year`, `month`, `day` and `start` lookups and what each matches are R3.
- Q: Is the column indexed? → A: As for any Django field, the developer decides with `db_index` or
  `Meta.indexes`. The package defines a field, not a model, so it has no query path of its own to
  index.
- Q: Which fixture formats are covered? → A: The ones Django ships without an extra install: JSON,
  JSON Lines and XML. django-reversion and other history tools are R7.
- Q: Does the partial date value still work without Django? → A: Django becomes a runtime
  dependency of the package with this feature, as the roadmap plans. Importing and using the
  partial date value still needs no configured Django settings. FS-001's statement that the
  package has no runtime dependency is rewritten in this pull request to say so.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (US1): The package MUST provide a model field a developer declares on a model to hold
  one partial date per row.
- **FR-002** (US1): The field's column MUST be text of at most ten characters, compared byte by
  byte (the `C` collation on PostgreSQL), with no companion column, as ADR 0001 records. The field
  MUST set this itself, and its migration MUST carry it.
- **FR-003** (US1): The column MUST carry a database check, created by the field's own migration,
  that refuses any text the partial date value refuses (FS-001, FR-002 and FR-005), and empty
  text.
- **FR-004** (US1): Making migrations a second time with nothing changed MUST make no migration.
- **FR-005** (US1): The field MUST accept a partial date value, its ISO form as text, or `None`,
  and MUST store the ISO form. Empty text MUST be stored as no date.
- **FR-006** (US1): Every value read from the database MUST be a partial date value, or `None` for
  no date.
- **FR-007** (US1): Any other value MUST be refused before it is written, through every ORM write
  route: saving an instance, `create()`, `update()`, `bulk_create()` and `bulk_update()`.
- **FR-008** (US1): `full_clean()` MUST report an invalid value as a validation error on the field
  with the code `invalid`, and MUST leave a valid value on the instance as a partial date value.
- **FR-009** (US1): The field MUST support Django's standard field options, including allowing no
  date, a default given as a partial date value or its ISO form, uniqueness and indexing.
- **FR-010** (US1): Filtering for exact equality MUST accept a partial date value or its ISO form,
  and MUST match only rows holding that value at that precision.
- **FR-011** (US1): Every behaviour in this specification MUST be the same on PostgreSQL and on
  SQLite. The test suite MUST select its database from the environment, so it runs against either.
- **FR-012** (US1): Importing and using the partial date value MUST need no configured Django
  settings.
- **FR-013** (US2): `dumpdata` MUST write each value as its ISO form and each empty value as empty,
  in JSON, JSON Lines and XML.
- **FR-014** (US2): `loaddata` MUST read the ISO form and empty values back unchanged, and MUST
  refuse text that is not a partial date.

### Key Entities

- **Partial date field**: a model field holding one partial date, or no date, per row. Its column
  holds the ISO form, compared byte by byte, guarded by a database check. It takes in and gives
  back the partial date value from FS-001.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every valid ISO form from `0001` to `9999-12-31` round-trips through the field
  unchanged on both databases: saved, read back, dumped and loaded.
- **SC-002**: No text the partial date value refuses can be left in the column by any route, the
  ORM or raw SQL, on either database.
- **SC-003**: The serialisation defect listed in `docs/reference/prior-art.md` cannot be
  reproduced: a fixture holding empty values dumps and loads without error and without change.
- **SC-004**: The whole test suite passes against PostgreSQL and against SQLite with the same
  results.
- **SC-005**: A developer adds the field to a model with one line and declares nothing else for it:
  no constraint, no collation, no companion field.

## Assumptions

- The developer uses Django 5.2 LTS or the current stable release, on PostgreSQL or SQLite, as the
  constitution's stack article sets out. Other databases are not supported.
- A model form or the admin shows the field as year, month and day selects, with nothing for the
  developer to configure (FS-004).
- A developer moving from django-partial-date waits for R5. This field does not read that
  package's columns.
