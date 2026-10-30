# Tasks: Moving from django-partial-date

**Input**: `spec.md`, `plan.md`, `research.md` in `specs/005-moving-from-django-partial-date/`

Every task is test-first: the test is written and seen to fail before the code. A test that passes
on its first run records in its task's evidence the change to the code that turns it red. No test
asserts wording. No name starts with an underscore. Lines are at most 88 characters.

## Phase 1: User Story 1 — A developer converts an existing column (P1)

**Goal**: one operation in a migration converts an old column in place, or changes nothing.

**Independent test**: `uv run pytest tests/test_conversion.py`, then the same with
`TEST_DATABASE=postgresql` and the `PG*` variables set.

### Group 1

- [ ] T001 [US1] `OldPartialDateField` in `partial_dates/conversion.py`. Tests in
  `tests/test_conversion.py`, class `TestOldPartialDateField`: creating a model with it gives the
  old column on each database (`timestamp with time zone`, `datetime`), a row written by raw SQL
  reads back and saves unchanged, and any `Field` option passes through `deconstruct()`
- [ ] T002 [US1] `ConvertPartialDateField` forwards and `UncheckedPartialDateField`, with no refusal
  yet, on the steps in `research.md`. Class `TestConversion`: each precision, `0990-03-01 00:00:01`,
  the earliest and latest dates (US-1 1–3), empty values (US-1 4), a required field stays required
  (US-1 5), a converted column compared with a new one, including its check, by raw SQL refused and
  accepted the same (US-1 6), `db_index`, `unique`, `Meta.indexes` and a unique constraint in place
  and enforced (US-1 7), the state after the operation equal to the target field and no change
  detected against it (US-1 8)
- [ ] T003 [US1] `USE_TZ` and `TIME_ZONE`. Class `TestTimeZones`: `USE_TZ` on with `TIME_ZONE` west of
  UTC, and `USE_TZ` off with a zone east of UTC and with one west of it, on a date before 1900 where
  the zone's offset has seconds (US-1 9). PostgreSQL's session zone is what varies, and on SQLite
  the test confirms settings do not matter
- [ ] T004 [US1] `db_column`, `db_table`, several fields and several models in one migration through
  `Migration.apply` (US-1 17), and a model the router excludes is left alone (edge case). Class
  `TestConversionTargets`

### Group 2

- [ ] T005 [US1] Refusal and `RefusedValuesError`. Class `TestRefusal`, one parametrised test per
  kind: a time of day (US-1 10), seconds 3 to 59, a fraction of a second, year precision off 1 January, month
  precision off the first (US-1 11), and outside 0001–9999, `infinity` and a BC date on PostgreSQL, and
  on SQLite impossible dates, non-timestamp text, a number, empty text and text with an offset
  (US-1 12). Each asserts the column and every row are unchanged, and the error's model, field,
  count, keys and values, by attribute (US-1 13). A migration with `atomic = False` leaves the
  column unchanged (US-1 14), and correcting the row lets the migration complete (US-1 15)
- [ ] T006 [US1] `database_backwards`. Class `TestBackwards`: stored values byte for byte, on a
  column that started as timestamps, including empty values, then forwards again, with an indexed
  field and a unique one (US-1 16). On PostgreSQL the values compare as stored in a session zone
  other than UTC as well
- [ ] T007 [US1] An unsupported vendor (US-1 19), with a fake connection vendor. `reduce` returning
  `False`, through `MigrationOptimizer`, so a conversion followed by `AlterField` keeps both.
  `sqlmigrate`-style `collect_sql` runs with no reads, and `describe` and the name fragment
- [ ] T008 [US1] A generated `AlterField` left in place on a table with rows fails on both databases
  and changes nothing (the edge case). Class `TestBareAlterField`. Changing
  `OldPartialDateField.get_internal_type` to return `"DateTimeField"` turns it red on PostgreSQL:
  put the command and the failure in the evidence
- [ ] T009 [US1] US-1 18: `ConvertPartialDateField("m", "f", field)` deconstructs and writes through
  `MigrationWriter` to a migration that imports and runs, with the same arguments as `AlterField`.
  The rest of the docs step for this story: `CHANGELOG.md`, and the names in `CONTEXT.md`

## Phase 2: User Story 2 — A developer removes django-partial-date from a project (P1)

**Goal**: following the guide, a project drops the old package from every database it has.

**Independent test**: `uv run pytest tests/test_moving.py tests/test_guide.py`, then the same with
`TEST_DATABASE=postgresql` and the `PG*` variables set.

### Group 3

- [ ] T010 [US2] `tests/moving/`: the app, its models, migrations `0001` to `0004` as `plan.md` lists,
  in `INSTALLED_APPS`, `tests/moving/fields.py` holding the project's own subclass, rebased on
  `PartialDateField`. Nothing imports `partial_date`. `makemigrations --check` clean (US-2 1, 7)
- [ ] T011 [US2] `tests/test_moving.py`. Class `TestDatabases`: from empty (US-2 2), from `0003`
  holding rows (US-2 3), from `0001` holding rows, through the alteration and the rebuild (US-2 4),
  each for the subclass (US-2 5) and the rename and alteration (US-2 6). Schemas compared with the
  one from empty, and the three reached by `MigrationExecutor`
- [ ] T012 [US2] A fixture holding ISO forms and `null`, as `dumpdata` wrote it from the old field,
  loads into the converted table (US-2 8). `tests/moving/fixtures/`

### Group 4

- [ ] T013 [US2] `docs/developer/moving-from-django-partial-date.md` and the entry in
  `docs/developer/index.md`, covering FR-015, FR-016 and FR-017, the `AlterField` warning, the
  remedy for each kind of refused value, and a table of the old value class's names and their
  replacements. Class `TestMovingGuide` in `tests/test_guide.py`: every Python block runs against
  the package, and the steps name the test app's end state (US-2 9)
- [ ] T014 [US2] `README.md` and `docs/ROADMAP.md` (R5 delivered, with its issues). `docs/index.md` if
  it lists the guides

## Dependencies

Group 2 builds on Group 1, Group 3 on Group 2, Group 4 on Group 3. Stories run in order on one
worktree, the feature's own.
