# Tasks: Storing a partial date on a model

**Input**: `spec.md`, `plan.md`, `research.md` in `specs/002-model-field/`

Every task is test-first: the test is written and seen to fail before the code. Tests go in
`tests/test_fields.py` in the class named. No test asserts an error message or any wording.
Validation errors are asserted by field and code, database refusals by exception type.

## Phase 1: User Story 1 — A developer stores a partial date on a model (P1)

**Goal**: declare the field, migrate, save and read partial dates, and have the database refuse
anything else, on SQLite and PostgreSQL.

**Independent test**: `uv run pytest tests/test_fields.py`, then the same with
`TEST_DATABASE=postgresql` and the `PG*` variables set.

### Group 1

- [x] T001 [US1] Test settings choose the database from `TEST_DATABASE` and the `PG*` variables
  (research R5). `"tests"` becomes an installed app. `tests/models.py` with `Record` and `Event`
  as `plan.md` describes, every field with a `verbose_name` and `help_text`, and
  `tests/migrations/0001_initial.py` made by `makemigrations tests`. `tests/factories.py`
  (`RecordFactory`, `EventFactory`), fixtures wrapping them in `tests/conftest.py`, and
  `tests/test_factories.py`. `tests/test_models.py`: one parametrised test that every test-model
  field has a `verbose_name` and `help_text`.
  `tests/models.py`, `tests/migrations/` and `tests/fixtures/` join the conformance
  `non-mirror-paths` in `pyproject.toml`. `dependencies = ["django>=5.2"]` in `pyproject.toml`,
  lock updated with `uv lock`
- [x] T002 [US1] `PartialDateField` in `partial_dates/fields.py`, re-exported from
  `partial_dates/__init__.py`: `__init__` fixing `max_length` at 10 and refusing it as an
  argument, `deconstruct()`, `get_internal_type()`, `db_parameters()` with the `C` collation on
  PostgreSQL, `description`, `empty_strings_allowed = False`. Tests in `TestColumn`: the column
  is `varchar` of length 10 read through `connection.introspection`, collated `C` on PostgreSQL,
  `deconstruct()` carries no `max_length`, a `PartialDate` default deconstructs to its ISO form
  and the field serialises with `MigrationWriter.serialize`, passing `max_length` raises `TypeError`, and
  `makemigrations --check --dry-run` finds nothing for the test app (US-1 1, 2)
- [x] T003 [US1] `db_check()` returning the check SQL of research R3. Tests in
  `TestDatabaseCheck`, by raw parameterised SQL against the `Record` table: every text in US-1
  scenario 11 plus `990`, `1990-00`, `1990-06-00`, `1990-06-32`, `199a`, `1990/06`, Arabic-Indic
  digits, an eleven-character text and `1990`, a NUL, then `junk` (on PostgreSQL the driver refuses
  it, so accept the driver's error there) is refused on `INSERT` and on `UPDATE` of an existing row
  (`IntegrityError`, or `DataError` for the overlong text); every form in US-1 scenario 12 plus
  `1990`, `1990-06`, `1990-06-14`, `1996-02-29` and `0990` is accepted and reads back through `Record.objects` as the partial date value (US-1 12), and
  `NULL` is accepted.
  Both fields of `Record` refuse, each through its own check (edge case)

**Checkpoint**: the column exists as ADR 0001 describes and refuses malformed text by any route.

### Group 2

- [x] T004 [US1] `from_db_value`, `to_python` and `get_prep_value` (research R4). Tests in
  `TestSavingAndReading`: a value at each precision saves and reads back equal, with the ISO form
  in the column read by raw SQL (US-1 3); each ISO text saves and reads back as the value (US-1 4);
  `None` and `""` save as SQL `NULL` and read back `None` (US-1 5, 6); `Event` saved with no date
  raises `IntegrityError` (US-1 7); `Record.defaulted` holds `1990` when not given, and a default
  given as a `PartialDate` works the same (US-1 14); `0001` and `9999-12-31` round-trip, `0990`
  is stored with four digits (edge cases)
- [x] T005 [US1] Tests in `TestRefusedWrites`: `"1990-6"`, `"990"`, a `datetime.date` and an `int`
  each raise `ValueError` through `save()`, `objects.create()`, `QuerySet.update()`,
  `bulk_create()` and `bulk_update()`, and the rows already in the table keep their values (US-1
  8). No production code is expected beyond T004. If every test passes on its first run, record in
  the task's evidence the mutation that turns them red
- [x] T006 [US1] `default_error_messages` with `invalid`, and `to_python` raising
  `ValidationError` with code `invalid`. Tests in `TestValidation`: `full_clean()` on an instance
  holding `"1990-6"` raises a `ValidationError` whose `error_dict` has the field with code
  `invalid` (US-1 9); `full_clean()` on an instance holding `"1990-06"` leaves a `PartialDate` on
  the attribute (US-1 10). `partial_dates/locale/en/LC_MESSAGES/django.po` made with
  `django-admin makemessages -l en` from inside `partial_dates/`
- [x] T007 [US1] Tests in `TestFiltering`: with rows holding `1990`, `1990-01`, `1990-01-01` and
  `None`, `filter(date=PartialDate(1990))` and `filter(date="1990")` find exactly the `1990` row,
  and `get(occurred=...)` finds an `Event` by its value (US-1 13). Two `Event` rows with the same `occurred`
  raise `IntegrityError`, and `Event.indexed` has an index in `connection.introspection` (FR-009).
  In `tests/test_init.py`, `TestImportWithoutSettings`: a fresh interpreter
  with `DJANGO_SETTINGS_MODULE` removed imports `partial_dates`, builds `PartialDate(1990)` and
  exits 0 (FR-012)
- [x] T008 [US1] README: *Status* says the field exists; *Usage* gains a section on the field —
  declaring it on a model, what it takes and gives back, empty values, and that the database
  refuses malformed text whichever route writes it. Examples run as written. CHANGELOG
  `[Unreleased]`: *Added* the field, *Changed* Django is now a dependency

**Checkpoint**: a developer can store and read partial dates on a model.

## Phase 2: User Story 2 — A developer moves partial dates in and out with fixtures (P2)

**Goal**: `dumpdata` and `loaddata` round-trip every value, empty ones included.

**Independent test**: `uv run pytest tests/test_fields.py::TestFixtures`, on both databases.

### Group 1

- [x] T009 [US2] `value_to_string`. `tests/fixtures/records.json`, `records.jsonl` and
  `records.xml`, each holding `Record` rows with `1990`, `1990-06`, `1990-06-14` and an empty
  value, exactly as `dumpdata` writes them. Tests in `TestFixtures`, parametrised over the three
  formats: `dumpdata tests.Record` of those rows writes each value as its ISO form and the empty
  one as empty, and its output equals the committed file (US-2 1, 2, 7); `loaddata` of the file
  into an empty table gives equal `PartialDate` values and `None` (US-2 3, 7); a hand-written
  fixture of ISO texts loads as the values (US-2 4); a fixture holding `1990-6` fails to load and
  leaves no row holding it (US-2 5)
- [x] T010 [US2] README *Usage*: fixtures written by `dumpdata` load back with `loaddata`, empty
  values included. CHANGELOG entry extended. Then run the full suite with and without
  `TEST_DATABASE=postgresql` and record both results for the pull request (US-1 15, SC-004)

- [x] T011 [US2] The test settings name `BigAutoField` as the default primary key, so the test
  migration is the same on Django 5.2, where the default was `AutoField`, and
  `makemigrations --check` passes across the supported range

**Checkpoint**: fixtures round-trip on each database, and each database reads what the other
writes.

## Dependencies

T001 → T002 → T003 → T004 → (T005, T006, T007) → T008 → T009 → T010 → T011. One worktree, in order.
