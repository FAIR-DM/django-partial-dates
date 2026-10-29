# Tasks: A partial date value for Python code

**Input**: `spec.md`, `plan.md`, `research.md` in `specs/001-partial-date-value/`

Every task is test-first: the test is written and seen to fail before the code. Tests go in
`tests/test_partial_date.py` in the class named. No test asserts an error message.

## Phase 1: User Story 1 — A developer records a partial date in Python (P1)

**Goal**: build, read and write a partial date, refusing anything invalid.

**Independent test**: `uv run pytest tests/test_partial_date.py::TestBuilding
tests/test_partial_date.py::TestReadingTheIsoForm tests/test_partial_date.py::TestWritingTheIsoForm`

### Group 1

- [ ] T001 [US1] `Precision` enum and the `PartialDate` frozen dataclass with `year`, `month`,
  `day` and the `precision` property, in `partial_dates/partial_date.py`, re-exported with
  `Precision` from `partial_dates/__init__.py`. Tests in `TestBuilding`: scenarios US1.1–US1.3 and
  US1.6, and that assigning a part raises and leaves the value unchanged (US1.12, SC-001)
- [ ] T002 [US1] Validation in `__post_init__`: a day without a month, a month outside 1–12, a day
  the month does not have (`1990-02-30`, `1990-04-31`, `1990-02-29`, `1900-02-29`), years 0 and
  10000, a year of `None` (`PartialDate(None, 6)`), a part that is a `str`, a `float` or a `bool` — each raises `ValueError`. `2000-02-29`,
  `0001-01-01` and `9999-12-31` build. Tests in `TestBuilding` (US1.7–US1.9, US1.11, US1.13,
  edge cases)
- [ ] T003 [US1] `fromisoformat` classmethod. Tests in `TestReadingTheIsoForm`: the three forms
  equal the built values (US1.4), and each refused text from US1.10 plus `0000`, `10000`,
  `1990-13`, a trailing newline, Unicode digits and a non-`str` argument raise `ValueError`
- [ ] T004 [US1] `isoformat()` and `__str__`. Tests in `TestWritingTheIsoForm`: each precision
  writes its form, a year below 1000 writes four digits, and every value at every precision in
  years 0001, 1999, 2000 and 9999 reads back from its own ISO form equal and writes the same text
  (US1.5, SC-004)
- [ ] T005 [US1] README: change the *Status* line, add a *Usage* section showing a value built
  from parts and read from text, its parts, its `precision` and its ISO form. CHANGELOG
  `[Unreleased]` → *Added*: the partial date value

**Checkpoint**: a developer can build, read and write a partial date.

## Phase 2: User Story 2 — A developer sorts partial dates and keys collections by them (P1)

**Goal**: ISO order, equality and hashing.

**Independent test**: `uv run pytest tests/test_partial_date.py::TestOrdering
tests/test_partial_date.py::TestEquality`

### Group 1

- [ ] T006 [US2] `__lt__`, `__le__`, `__gt__`, `__ge__` over the sort key. Tests in
  `TestOrdering`: the mixed list sorts as US2.1 says (SC-001), sorting every value in 1999–2000
  gives the order of their ISO forms as text (US2.2, SC-002), each operator agrees with text
  comparison over every pair of the plan's pair sample (US2.3), and ordering against a `date`, a
  `str` and an `int` raises `TypeError` (US2.7)
- [ ] T007 [US2] Equality and hashing. Tests in `TestEquality`: values with the same parts are
  equal with equal hashes (US2.4), `1990` against `1990-01-01` and `1990-06` against `1990-06-01`
  are unequal (US2.5), equal values built separately are one set member and one dictionary key
  (US2.6, SC-001), and a value is unequal to a `date`, a `str` and an `int` (US2.7). No production
  code is expected: the dataclass provides it. If every test passes on first run, record that in
  the task's evidence with the mutation that turns it red (switching `eq` off)
- [ ] T008 [US2] README *Usage*: sorting and using values as set members and dictionary keys.
  CHANGELOG entry extended

**Checkpoint**: a developer can sort and collect partial dates.

## Phase 3: User Story 3 — A developer asks when a partial date could have been (P2)

**Goal**: start, end and the before / after / overlapping comparison.

**Independent test**: `uv run pytest tests/test_partial_date.py::TestPeriod
tests/test_partial_date.py::TestRelation`

### Group 1

- [ ] T009 [US3] `start` and `end` properties. Tests in `TestPeriod`: US3.1–US3.3, `1900-02` ends
  on the 28th, and `0001` and `9999` give their first and last days
- [ ] T010 [US3] `Relation` enum, re-exported from the package, and `relation_to`. Tests in
  `TestRelation`: US3.4–US3.7, US3.9 (`TypeError` for a `date`, a `str`, `None`), and over the
  pair sample: `BEFORE` and `AFTER` are each other's mirror, `BEFORE` means the first end is before
  the second start and `OVERLAPPING` means the periods share a day (US3.8), and `BEFORE` agrees
  with the coarser-precision rule written out in the test (SC-003)
- [ ] T011 [US3] README *Usage*: start, end and `relation_to`, with the reason sorting and
  "earlier" are different questions. CHANGELOG entry extended

**Checkpoint**: every acceptance scenario has a test.

## Dependencies

US1 → US2 → US3, sequential on one branch: each adds to the class and the README section the
previous one wrote.

## Coverage of the spec

| Requirement | Tasks |
|---|---|
| FR-001 | T001 |
| FR-002 | T003 |
| FR-003 | T001 |
| FR-004 | T004 |
| FR-005 | T002, T003 |
| FR-006 | T002, T003, plus `deptry` in verify |
| FR-007 | T001 |
| FR-008 | T006 |
| FR-009 | T007 |
| FR-010 | T006, T007 |
| FR-011 | T009 |
| FR-012 | T010 |
| FR-013 | T010 |
| SC-001 | T001, T006, T007 |
| SC-002 | T006 |
| SC-003 | T010 |
| SC-004 | T004 |
| SC-005 | verify (`deptry`), `pyproject.toml` unchanged |
