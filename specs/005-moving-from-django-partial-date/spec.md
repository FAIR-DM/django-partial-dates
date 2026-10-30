# Feature Specification: Moving from django-partial-date

**Feature Branch**: `005-moving-from-django-partial-date`

**Created**: 2026-10-30

**Status**: Draft

**Serves**: G5 · **Roadmap**: R5 · **Issue**: #20 · **Builds on**: FS-001, FS-002

**Input**: A developer whose project stores dates with django-partial-date needs to move an
existing column to this package without losing a value, on PostgreSQL and SQLite.
django-partial-date keeps a timestamp with the precision hidden in its seconds, so every project
has the same conversion to do, and it should be a few lines in that project's own migration rather
than something each one writes for itself. The developer also needs to know how to make the move,
including how to change the existing migrations so they no longer import django-partial-date.

## Summary

A migration operation that converts a column written by django-partial-date, in place, into the
column FS-002 defines, and a guide to the whole move. The developer changes the model to this
package's field, and puts one operation per field in a migration. Every value comes out as the ISO
form of the partial date it records, and every empty value stays empty.

No data is lost, and that rule decides what happens to a value that cannot be converted cleanly.
A value converts only when it is exactly what django-partial-date writes for a partial date. Any
other value stops the migration before anything has changed, on both databases, and the error says
which rows to look at. The operation never rounds, truncates or guesses.

The existing migrations of a project import django-partial-date, so removing the package would
break them. This package gives them a field to point at instead, so that they keep describing the
column they created, and a project can uninstall django-partial-date whatever state each of its
databases is in.

Out of scope, each owned elsewhere:

- the form field, the widget and the admin (R4)
- moving FAIR-DM and django-literature themselves, which are changes to those projects
- round trips through django-reversion and other model-history tools (R7)

The words used here are defined in `CONTEXT.md`. Stored timestamps are written as the old column
holds them on SQLite, `1990-06-14 00:00:02`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A developer converts an existing column (Priority: P1)

A developer whose model holds a date in a django-partial-date column changes the model to this
package's field and adds one operation for that field to a migration. Applying the migration turns
the column into the one FS-002 defines, with every value intact, and writing no SQL and no Python
of their own. If a value cannot be converted cleanly, the migration stops with nothing changed and
tells them which rows to correct.

**Why this priority**: It is the feature. Goal G5 is that a project moves with a migration and
loses no data, and the conversion is the same work for every project.

**Independent Test**: On each database, create a table with a column in the old form, write rows
through raw SQL holding each stored form below, apply a migration holding the operation, and
compare the column and what the field reads with what was written.

**Acceptance Scenarios**:

1. **Given** rows holding `1990-01-01 00:00:00`, `1990-06-01 00:00:01` and `1990-06-14 00:00:02`,
   **When** the developer applies the migration, **Then** the column holds `1990`, `1990-06` and
   `1990-06-14`, and the field reads back the partial date values they stand for.
2. **Given** a row holding a date before the year 1000, such as `0990-03-01 00:00:01`, **When** the
   developer applies the migration, **Then** the column holds the four-digit ISO form `0990-03`.
3. **Given** rows at the earliest and latest dates the ISO form can hold, at each precision,
   **When** the developer applies the migration, **Then** each converts to its ISO form.
4. **Given** a field that allows no date and rows holding none, **When** the developer applies the
   migration, **Then** those rows still hold no value, and no row has gained a date.
5. **Given** a field that requires a date, **When** the developer applies the migration, **Then**
   the column still refuses a row without one.
6. **Given** the migration applied, **When** the column is compared with one created by FS-002's
   field with the same options, **Then** they do not differ: the text type and length, the
   comparison byte by byte, and the check refusing malformed text are all in place.
7. **Given** a field with an index, or named in a unique constraint or in `Meta.indexes`, **When**
   the developer applies the migration, **Then** that index or constraint is in place on the
   converted column and still enforced.
8. **Given** the migration applied, **When** the developer makes migrations again, **Then** no new
   migration is made.
9. **Given** a project with `USE_TZ` on and a `TIME_ZONE` west of UTC, or with `USE_TZ` off and any
   `TIME_ZONE`, **When** the developer applies the migration, **Then** every value converts to the
   date django-partial-date read from it, so `1990` never becomes `1989`.
10. **Given** a row whose stored value is a time other than 00:00:00, 00:00:01 or 00:00:02, such
    as `1990-06-14 13:45:37`, **When** the developer applies the migration, **Then** it is refused.
11. **Given** a row whose stored seconds say year precision on a date other than 1 January, such as
    `1990-06-14 00:00:00`, or month precision on a day other than the first, such as
    `1990-06-14 00:00:01`, **When** the developer applies the migration, **Then** it is refused.
12. **Given** a stored value that has no ISO form, because it falls outside the years 0001 to 9999,
    or is PostgreSQL's `infinity`, or on SQLite is text that is not a real timestamp, a number or
    empty text, **When** the developer applies the migration, **Then** it is refused.
13. **Given** any refused value, **When** the migration stops, **Then** every row and the column
    are unchanged, including the rows that could have converted, and the error names the model,
    the field and the number of refused values, and gives the primary key and stored value of the
    first of them.
14. **Given** a refused value in a migration marked as not atomic, **When** the migration stops,
    **Then** the column holding that value is unchanged.
15. **Given** a migration that stopped on refused values, **When** the developer corrects those
    rows and applies it again, **Then** it completes.
16. **Given** the migration applied, **When** the developer migrates backwards past it, **Then**
    the column returns to the old form and each row holds the same stored value it held before,
    with empty values still empty.
17. **Given** one migration converting several fields, on one model or on several, including a
    field with its own `db_column` and a model with its own `db_table`, **When** the developer
    applies it, **Then** each column is converted.
18. **Given** the migration Django generated for the change of field, **When** the developer turns
    it into the conversion, **Then** the only edit is the name of the operation, because the
    operation takes the same arguments as Django's own field alteration.
19. **Given** a database other than PostgreSQL and SQLite, **When** the developer applies the
    migration, **Then** the operation refuses to run before anything changes.
20. **Given** scenarios 1 to 18, **When** the suite runs against
    PostgreSQL and against SQLite, **Then** each gives the same result on both.

---

### User Story 2 - A developer removes django-partial-date from a project (Priority: P1)

A developer follows the guide from start to finish: they change the references in the project's
existing migrations so that nothing imports django-partial-date, change the models, convert the
columns and uninstall the package. Every database the project has reaches the same schema,
whether it is a deployed one with years of rows, one that is some migrations behind, or a new one
built from empty.

**Why this priority**: A converted column is no use to a project that cannot uninstall the old
package, and until the existing migrations stop importing it, it cannot.

**Independent Test**: Take a test app whose migrations reference the old field in the ways real
projects do, make the changes the guide lists, and with django-partial-date not installed, migrate
one database from empty, one holding rows at the latest migration before the conversion, and one
holding rows several migrations behind. Compare the three schemas.

**Acceptance Scenarios**:

1. **Given** existing migrations that create and alter a field through django-partial-date,
   **When** the developer changes each reference as the guide says, **Then** the migrations load
   and run with django-partial-date not installed.
2. **Given** those changed migrations, **When** the developer migrates a new database from empty,
   **Then** it ends with the same column as a converted database.
3. **Given** a deployed database that has applied every existing migration, **When** the developer
   migrates it, **Then** only the new migration runs, and its values convert as in User Story 1.
4. **Given** a database some migrations behind and holding rows, with a pending migration that
   alters the table holding the date, **When** the developer migrates it, **Then** every migration
   completes on both databases and the values convert, including where SQLite rebuilds the table
   before the conversion.
5. **Given** existing migrations that reference a project's own subclass of the old field, **When**
   the developer changes those references and rebases the subclass on this package's field,
   **Then** scenarios 1 to 4 hold.
6. **Given** existing migrations that rename the field or alter one of its options, **When** the
   developer migrates, **Then** scenarios 2 to 4 hold.
7. **Given** the move finished, **When** the developer makes migrations, **Then** no new migration
   is made, and nothing in the project imports django-partial-date.
8. **Given** a fixture written by django-partial-date's field, **When** the developer loads it
   after the move, **Then** the values and the empty values load unchanged.
9. **Given** the guide, **When** a developer reads it, **Then** it takes them through every step
   of the move in the order that works, and every code example in it runs against the package.

---

### Edge Cases

- A model inherits its field from an abstract base, so each concrete model has its own column and
  its own operation.
- An old column that was never used holds no rows, and converts like any other.
- A column a project created with its own timestamp values and later declared as django-partial-date
  has times of day in it, and every such row is refused. The guide shows how to correct them.
- On a PostgreSQL database whose view depends on the column, the database refuses the change and
  the column stays as it was.
- A database router that excludes the model from a database excludes the operation there too, as
  for Django's own operations.
- django-partial-date dumps a year below 1000 without its leading zero, as `990-03`, which is not
  the ISO form. FS-002's field refuses it in a fixture, and the guide says so.
- An earlier data migration that imports django-partial-date's value class needs its own edit,
  which the guide describes.
- A developer who leaves the `AlterField` Django generated in place of the conversion gets a
  database error on a table holding rows, on both databases, and no value changes. Django's own
  alteration would otherwise cut every PostgreSQL value to its first ten characters, which writes
  a month and a day nobody recorded.
- A project keeps this package installed after the move, because its migrations refer to it.

## Clarifications

### Session 2026-10-30

- Q: What happens to a value that cannot be converted cleanly? → A: The migration stops before
  anything changes, on both databases, and the error says which rows. A value converts only when
  it is exactly what django-partial-date writes for a partial date, because any other value holds
  more than the ISO form can carry, or something other than a date. Dropping that silently is the
  loss G5 rules out, and the developer is the only one who can say which reading is right.
- Q: What about a value django-partial-date itself reads without complaint, such as
  `1990-06-14 00:00:00`, which it shows as `1990`, or `1990-06-14 13:45:37`, which it shows as
  `1990-06-14`? → A: Both are refused. The first holds a month and a day the ISO form at year
  precision has no room for, and the second holds a time. What the old field happens to show is
  not evidence of what was recorded. Its precision setter does not clear the parts it should, so
  the first shape can be written through its Python interface, and a developer may need that day.
- Q: Does the operation read the timestamp in a particular time zone? → A: In the time zone of
  Django's database connection, which is the one django-partial-date's field wrote and read it in.
  A value that does not fall on one of the three stored times there is refused, so a project whose
  time zone settings changed after the rows were written gets a refusal, never a date one day out.
- Q: Can the move be undone? → A: Yes. Migrating backwards restores the old column and every stored
  value, so a deployment that goes wrong can roll back like any other.
- Q: Does a project need a way to check its data before deploying? → A: No further tool. A refused
  migration changes nothing, so applying it is the check, and the guide says to do that first on a
  copy of the data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (US1): The package MUST provide a migration operation that converts one
  django-partial-date column, in place, into the column FS-002 defines, taking the same arguments
  as Django's own field alteration, and updating the migration state to match.
- **FR-002** (US1): The operation MUST convert a stored value only when it is a timestamp at
  00:00:00, 00:00:01 or 00:00:02, and that time's precision is consistent with its date: 00:00:00
  on 1 January (year), 00:00:01 on the first of a month (month), 00:00:02 on any date (day), in the
  years 0001 to 9999.
- **FR-003** (US1): A converted value MUST be the ISO form at the precision the seconds record, with
  four digits of year.
- **FR-004** (US1): An empty value MUST stay empty, and MUST NOT become a date.
- **FR-005** (US1): The operation MUST read each value in the time zone of the database connection.
- **FR-006** (US1): Before changing anything on a column, the operation MUST check every value on
  it. Any value outside FR-002 MUST stop the migration with the column and all its rows unchanged.
- **FR-007** (US1): The error MUST name the model, the field and the number of refused values, and
  MUST give the primary key and stored value of the first of them.
- **FR-008** (US1): A converted column MUST NOT differ from one FS-002's field creates with the same
  options, and its indexes and constraints MUST be in place.
- **FR-009** (US1): The operation MUST be reversible, restoring the old column and each stored
  value it converted.
- **FR-010** (US1): The operation MUST work on a column named by `db_column`, on a table named by
  `db_table`, and for fields on any concrete model, and MUST honour database routers.
- **FR-011** (US1): On a database other than PostgreSQL and SQLite, the operation MUST refuse to
  run before anything changes.
- **FR-012** (US1): Every behaviour in User Story 1 and User Story 2 MUST be the same on PostgreSQL
  and on SQLite, and both MUST be tested.
- **FR-013** (US2): The package MUST provide a field that existing migrations reference in place of
  django-partial-date's field, or of a project's subclass of it. It MUST describe the same column
  as the old field, in every option those migrations pass, so that creating, altering and
  rebuilding the table before the conversion behave as they did.
- **FR-014** (US2): The operation and that field MUST work with django-partial-date not installed,
  and the package MUST NOT gain a runtime dependency on it.
- **FR-015** (US2): The package MUST ship a how-to guide to the move, reachable from the developer
  guide's table of contents. It MUST cover, in working order: installing this package, changing the
  references in existing migrations, a project's own subclass, changing the models, writing the
  conversion, applying it first to a copy of the data, what each kind of refused value means and
  how to correct it, and uninstalling django-partial-date.
- **FR-016** (US2): The guide MUST list what a project's own code changes: the old value class's
  constructor, attributes and methods with what replaces each, and how ordering and filters differ.
- **FR-017** (US2): The guide MUST state what the move does not cover: fixtures with an unpadded
  year, earlier data migrations importing the old value class, and the exclusive lock the conversion
  holds on the table while it runs.

### Key Entities

- **Old column**: the column django-partial-date's field writes: `timestamp with time zone` on
  PostgreSQL, a `datetime` column holding text on SQLite. It holds a date, with the precision in
  its seconds: 0 for year, 1 for month, 2 for day. An empty value is `NULL`.
- **Conversion**: the migration operation that turns an old column into FS-002's column.
- **Refused value**: a value in an old column that is not one FR-002 converts.
- **Stand-in field**: the field existing migrations reference in place of the old one. It describes
  the old column and exists for migration history, never for a model.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every stored form at each precision, and every empty value, converts to the partial
  date django-partial-date's field recorded, on both databases.
- **SC-002**: Zero values are altered, dropped or rounded by the conversion: each value comes out
  exactly, or the migration refuses it with the table unchanged, on both databases.
- **SC-003**: A developer converts one column with one operation in a migration, and writes no SQL
  and no Python for it.
- **SC-004**: A project with django-partial-date uninstalled migrates to the same schema from
  empty, from the latest migration before the conversion and from several migrations behind.
- **SC-005**: The guide's steps, followed literally, complete the move on a test project shaped
  like each of the two known users: nullable indexed fields declared directly, and required fields
  declared through a project's own subclass on an abstract base.

## Assumptions

- The developer's project uses PostgreSQL or SQLite, as the constitution's stack article sets out,
  with django-partial-date 1.3, whose storage is what the stored forms above describe.
- A project brings its models to this package's field in the same change as the conversion.
  Running both packages' fields on one column during a move is not offered.
- A brief lock on the table during the conversion is acceptable. A conversion with no downtime is
  not offered.
- The migration stays in the project's own history, so the operation and the stand-in field are
  public interfaces of the package from their first release.
