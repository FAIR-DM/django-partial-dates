# Tasks: Entering and editing a partial date

**Input**: `spec.md`, `plan.md`, `research.md` in `specs/004-entering-partial-dates/`

Every task is test-first: the test is written and seen to fail before the code. A test that passes
on its first run, because Django already behaves that way, records in its task's evidence the change
to the code that turns it red. Errors are asserted by field and code. No test asserts wording,
layout or appearance. No name starts with an underscore. Line length is 88.

## Phase 1: User Story 1 — A user enters and edits a partial date, giving as much of it as they know (P1)

**Goal**: a plain Django form with the form field does everything a user does.

**Independent test**: `uv run pytest tests/test_forms.py tests/test_guide.py`, then the same with
`TEST_DATABASE=postgresql` and the `PG*` variables set.

### Group 1

- [ ] T001 [US1] `PartialDateWidget` and `PartialDateField` in `partial_dates/forms.py`, as `plan.md`
  describes. Tests in `tests/test_forms.py`: `TestEntering`, a year, a year and month, and a full date
  give the value at that precision, on a required and an optional field (US-1 1–3); a required field
  offers an empty choice in all three selects and selects no year on a blank form (US-1 4); all empty
  gives `None` or `required` (US-1 9, 10). `TestEditing`, an initial value as a `PartialDate` and as
  ISO text opens with exactly its parts selected (US-1 5); adding and emptying parts changes the
  precision (US-1 6, 7); unchanged parts leave `changed_data` empty and the value equal, at each
  precision (US-1 8); a year outside the offered years is selected and survives a submission (US-1 15)
- [ ] T002 [US1] Tests in `tests/test_forms.py`, `TestRefusing`: a day with no month and a part with no
  year give `incomplete` (US-1 11, 12); 30 February, `1900-02-29` and month `13` give `invalid`, and
  `2000-02-29` is accepted (US-1 13); text, year `0`, and a 5,000-digit year give `invalid`, with no
  exception (US-1 16); a refused entry re-renders with each submitted part selected, the error on the
  field and nothing in `cleaned_data` for it (US-1 14). `TestEveryCombination`, parametrised over
  empty, valid and impossible values of each part: each entry is either the value with exactly those
  parts or an error with a code (SC-002)
- [ ] T003 [US1] Tests in `tests/test_forms.py`, `TestAcrossLanguages`: under `translation.override`
  with a day-first and a year-first language the selects keep the order year, month, day, and each
  month's label equals `MONTHS` in that language (US-1 17, FR-011). `TestAssistiveUse`: each select has
  a distinct non-empty `aria-label`, the field renders in a `fieldset` with its label as the `legend`,
  and the year is the first select (US-1 18). `TestNoScript`: `Form.media` is empty and the render holds
  no script (US-1 19). The new messages go in `partial_dates/locale/en/LC_MESSAGES/django.po`
- [ ] T004 [US1] `docs/developer/forms.md`, first half: what a user sees, what each error code means,
  declaring the field on a plain form. `docs/developer/index.md`, `docs/index.md`, `README.md` (status
  and a usage section) and `CHANGELOG.md`. `tests/test_guide.py` gains a test running the page's `>>>`
  examples. Both public names are quoted

**Checkpoint**: a plain form does everything US-1 asks, and the page says so.

## Phase 2: User Story 2 — A developer gets partial date entry in their forms and the admin, with nothing to configure (P2)

**Goal**: the model field, the admin and a project with nothing configured.

**Independent test**: `uv run pytest tests/test_fields.py tests/test_forms.py tests/test_admin.py`, then
the same on PostgreSQL.

### Group 1

- [ ] T005 [US2] `formfield()` in `partial_dates/fields.py`. Tests in `tests/test_fields.py`,
  `TestFormField`, using a `ModelForm` on `Record` and `Event`: nothing declared gives the three selects
  and saving stores the value at each precision, and editing a row moves it between precisions and
  saves unchanged without a change (US-2 1, SC-001, SC-003); `blank`, `verbose_name` and `help_text`
  carry over (US-2 4); a default as a value, as ISO text and as a callable is selected on a new row and
  stored unchanged (US-2 5); a duplicate on `Event.occurred` gives `unique` on the field (US-2 6); a
  validator on the model field and on the form field receives a `PartialDate`, and its error is on the
  field (US-2 7)
- [ ] T006 [US2] `tests/settings.py`, `tests/admin.py`, `tests/urls.py`, `Note` and its migration, and
  `pyproject.toml`, as `plan.md` describes. Tests in `tests/test_admin.py`: a staff user adds and changes
  a `Record` with the admin client, year only and full, with a `Note` inline, and the rows hold those
  values; an unchanged save records that nothing changed; a day with no month redisplays with the error
  on the field and saves nothing; text in a part gives an error page, not a server error (US-2 2, SC-004)
- [ ] T007 [US2] Tests in `tests/test_forms.py`: `TestDeclaring`, a form with no model cleans to a value
  or `None` (US-2 3). `TestOfferedYears`, the default runs from today's year to 1900, newest first
  (US-2 8), `years` changes one field and not another (US-2 9), a year outside `years` is still accepted
  (FR-017), and the list follows the clock on a form class already defined (US-2 10). `TestSeveralFields`,
  two fields on a form, a prefix and a formset (US-2 12). `TestNothingConfigured`, a fresh interpreter
  with `settings.configure` naming no apps and no templates renders and cleans the form (US-2 11, FR-018).
  Edge cases: `990` records `0990`, a stored `0990` opens selected, a part left out of the submission
  reads as empty
- [ ] T008 [US2] `example/`, `.gitignore` and `pyproject.toml`, as `plan.md` describes. Check by hand:
  `migrate`, `seed` run twice, then `runserver`, with each page answering. `uv build` leaves `example/`
  out of the wheel and the sdist
- [ ] T009 [US2] `docs/developer/forms.md`, second half: model forms, the admin, naming the years, a
  limit as a validator, translating the messages, running the example. `README.md` scope, the R4 line in
  `docs/ROADMAP.md`, `CHANGELOG.md`, and the assumption in `specs/002-model-field/spec.md` (D13)

**Checkpoint**: every scenario passes on both databases.
