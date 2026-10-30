# Tasks: Showing a partial date to a reader

**Input**: `spec.md`, `plan.md`, `research.md` in `specs/006-showing-partial-dates/`

Every task is test-first: the test is written and seen to fail before the code. A test that passes
on its first run records in its task's evidence the change to the code that turns it red. No test
asserts fixed wording, and literal text is asserted only where it is computed from a date. No name
starts with an underscore. Lines are at most 88 characters.

## Phase 1: User Story 1 — A user reads a partial date in their own language (P1)

**Goal**: a partial date gives its display form, at its own precision, in the active language.

**Independent test**: `uv run pytest tests/test_partial_date.py::TestDisplayForm`.

### Group 1

- [x] T001 [US1] `PartialDate.display_form()`. Class `TestDisplayForm` in
  `tests/test_partial_date.py`: each precision as literal text in English, German and Japanese
  (US-1 1–3, FR-001 to FR-003), one value under two languages, with the language changed after the
  value was built (US-1 4, FR-004), `USE_THOUSAND_SEPARATOR` with a format that would group the year
  (US-1 5, FR-005), year 990 at all three precisions gives the same year text (US-1 6, FR-005), a
  time zone far from UTC changes nothing (US-1 7, FR-006), `USE_I18N=False` with
  `LANGUAGE_CODE="de"` gives the German text, and a language Django ships no formats for gives what
  Django's own `date_format` gives for it (edge cases)
- [x] T002 [US1] SC-001: for every language in `settings.LANGUAGES`, the text of a year equals the
  year format applied to 1 January and to 31 December of it, and the text of a month equals the month
  format applied to its first and its last day. Class `TestDisplayFormNamesOnlyRecordedParts`
- [x] T003 [US1] Documentation for `display_form`: `docs/developer/showing.md` with the display form
  at each precision and the Python route, run by `tests/test_guide.py`, linked from
  `docs/developer/index.md` and `docs/index.md`. **display form** in `CONTEXT.md`. A CHANGELOG entry
  and a README section

## Phase 2: User Story 2 — A developer shows a partial date (P2)

**Goal**: a developer gets the display form from a template and from Python, and across an admin
class with one declaration.

**Independent test**: `uv run pytest tests/test_templatetags tests/test_admin.py`.

### Group 2

- [x] T004 [US2] The `partial_date` filter in `partial_dates/templatetags/partial_dates.py`, and
  `"partial_dates"` in `tests/settings.py`. Class `TestPartialDateFilter` in
  `tests/test_templatetags/test_partial_dates.py`: a value renders its display form for the active
  language (US-2 1, FR-007), `None` renders empty and `default` works after it (US-2 2, FR-008), a
  string, a number, a `datetime.date` and an object render empty with no error (US-2 3, FR-008), and
  the result is escaped: the output is not a `SafeString`, and a format module whose format emits `<`
  renders `&lt;` with autoescape on (US-2 8, FR-009)
- [x] T005 [US2] The Python route. Add to `TestDisplayForm`: inside `translation.override` it gives
  that language's text (US-2 5), it equals what the filter renders for each precision and with no
  request (US-2 4, FR-010), and a project's format module sets `YEAR_MONTH_FORMAT` and `DATE_FORMAT`
  (US-2 6). The format module lives under `tests/`, with `FORMAT_MODULE_PATH` overridden and
  `reset_format_cache()` called around the test
- [x] T006 [US2] What must not change, class `TestISOFormStays` in `tests/test_partial_date.py`:
  under a language other than English, `str()`, `isoformat()` and a template with no filter give the
  ISO form, and `dumpdata`'s JSON and what is stored are the same (US-2 7, FR-011)
- [x] T007 [US2] The app entry. `makemigrations --check` is clean with the entry, the app config has
  no models (US-2 18, FR-017), and the Python route works with the entry removed by
  `modify_settings` (US-2 17, first half). Rewrite the sentence in
  `docs/developer/installation.md`, and add the filter and the app entry to
  `docs/developer/showing.md`, with its template example rendered by `tests/test_guide.py`

### Group 3

- [x] T008 [US2] `PartialDateDisplayMixin` in `partial_dates/admin.py`, its list half. The admin fixture
  as the plan says, with the expected heading read from the model field. Class `TestAdminList` in `tests/test_admin.py`: the column
  shows the display form and the ISO form is gone, it keeps its heading and is sorted by the stored
  order on the page and through `?o=` (US-2 9, FR-013, FR-014), it keeps the link to the row, by
  default and named in `list_display_links` (US-2 9), `list_editable` renders its selects and the POST
  saves (US-2 14, FR-015), an empty value shows the admin's empty display, including with a custom
  `empty_value_display` (US-2 15, FR-016), a method named in `list_display` and a `__` path are left
  alone (edge cases), and an admin with no mixin shows the ISO form (US-2 16). The English admin's
  list reads as US-1 8
- [x] T009 [US2] The change page. Class `TestAdminReadOnly`: a field in `readonly_fields` shows the
  display form with its label and help text, both read from the model field, in a default layout, in declared `fields` and in
  `fieldsets`, including a nested tuple (US-2 10, FR-013), an editable field keeps its selects and
  saving stores it, leaving the read-only field alone (US-2 13, FR-015), an empty read-only field
  shows the empty display (US-2 15), and the add page shows selects
- [x] T010 [US2] View-only and inlines. Class `TestAdminViewOnly`: a view-only user reads every
  partial date as the display form, with no selects (US-2 12, FR-013, US-1 9), and a field left out by `exclude`,
  by `fields` or by the form's `Meta.fields` stays off the page. An inline with the mixin shows the
  display form on a read-only field (US-2 11, US-1 8), on a view-only page, and for a user who may
  view the parent and change the inline. An inline a user may add to keeps selects on its new rows,
  with the parent changeable and with it read-only. A user who may add but not change a row sees selects on the
  add page. The admin display works with the app entry removed (US-2 17, second half)
- [x] T011 [US2] Documentation and example. The admin section of `docs/developer/showing.md`: the
  mixin, what it covers, the `__` case, and what an admin with no mixin shows. The example project as
  the plan says, with `seed` adding `view-only.user`. README, CHANGELOG, and R6 in
  `docs/ROADMAP.md` as delivered

- [x] T012 [US2] A default given as text, read from an unsaved row on the add page, shows the display
  form rather than the admin's empty display. Class `TestAdminReadOnly`
- [x] T013 [US2] A read-only field the form declares is not asked for on save, as Django's own
  `get_form` arranges for a field named in `readonly_fields`. Class `TestAdminReadOnly`
- [x] T014 [US2] A column named in `sortable_by` stays sortable. Class `TestAdminList`

## Dependencies and Dispatch

Groups run in order on one worktree. Group 2 and Group 3 both change `docs/developer/showing.md`, in
different sections. US-1 8 and 9 read pages only the mixin produces, so their tests sit with T008
to T010.
