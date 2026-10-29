# Implementation Plan: A partial date value for Python code

**Branch**: `001-partial-date-value` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-partial-date-value/spec.md`, `research.md`

## Summary

One new module, `partial_dates/partial_date.py`, holding a frozen dataclass `PartialDate` and two
string enums, `Precision` and `Relation`. Everything comes from the standard library. The package
re-exports the three names. The README documents them, and the CHANGELOG records them.

## Technical context

- **Language**: Python 3.12 and later
- **Dependencies**: none at runtime. Standard library only: `dataclasses`, `datetime`,
  `calendar`, `enum`, `re`
- **Testing**: pytest, no database, no Django
- **Constraints**: years 0001–9999 (ADR 0001). The order must be the ISO text order the database
  will give (SC-002)
- **Scale**: one module of about 150 lines, one test module

## Constitution check

| Article | How the plan meets it |
|---|---|
| I Testing | Test-first per story. Behaviour only: no wording asserted. Validation is asserted by the error type, never its message |
| II Simplicity | One module, standard library only, no settings |
| III Anti-abstraction | No base class, no registry, no protocol. Two enums because the spec names three precisions and three answers |
| IV Integration-first | The public surface (`PartialDate`, `Precision`, `Relation`, importable from `partial_dates`) is fixed in US1 and every test goes through it |
| V Security | Untrusted text reaches `fromisoformat` only. It is matched in full against an ASCII-only pattern with no backtracking risk, and refused otherwise |
| VI Documentation | README *Usage* section and CHANGELOG entry, written per story. Full docstrings |
| VII Dependencies | None added. `deptry` stays green |
| VIII i18n | No user-facing strings. Error messages are developer-facing exceptions, as Python's own are |
| IX Data model | Not applicable: no model |
| X Cohesion | All behaviour sits on the `PartialDate` class. No module-level functions |
| XI Storage | The value holds only recorded parts. Start and end are computed when read, never stored |
| XII Filters | Not applicable: no filter |
| XIII Compatibility | Python 3.12 and later. The ISO form written is ADR 0001's |

No violations.

## Design

### Public names

`partial_dates/__init__.py` re-exports `PartialDate`, `Precision` and `Relation` and lists them in
`__all__`.

### `Precision(enum.StrEnum)`

`YEAR = "year"`, `MONTH = "month"`, `DAY = "day"`.

### `Relation(enum.StrEnum)`

`BEFORE = "before"`, `AFTER = "after"`, `OVERLAPPING = "overlapping"`.

### `PartialDate`

`@dataclass(frozen=True, slots=True)` with fields `year: int`, `month: int | None = None`,
`day: int | None = None`.

| Member | Behaviour | Requirement |
|---|---|---|
| `__post_init__` | Refuses, with `ValueError`, checking types first because `date()` raises `TypeError` for a `float`: a part that is not an `int` or is a `bool` (a `None` year included); a day without a month; any combination `datetime.date(year, month or 1, day or 1)` refuses | FR-001, FR-005, FR-006 |
| `fromisoformat(text)` classmethod | `re.fullmatch(r"([0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2}))?)?", text)`. No match, or `text` not a `str` → `ValueError`. Otherwise `cls(int(y), int(m) if m else None, int(d) if d else None)` | FR-002, FR-005 |
| `isoformat()` | `YYYY`, `YYYY-MM` or `YYYY-MM-DD`, zero-padded | FR-004 |
| `__str__` | `self.isoformat()` | FR-004 |
| `precision` property | `Precision.DAY` if day, `Precision.MONTH` if month, else `Precision.YEAR` | FR-003 |
| `start` property | `date(year, month or 1, day or 1)` | FR-011 |
| `end` property | `date(year, month or 12, day or calendar.monthrange(year, month or 12)[1])` | FR-011 |
| `__lt__`, `__le__`, `__gt__`, `__ge__` | Compare `(year, month or 0, day or 0)` of both. `other.__class__ is not self.__class__` → `NotImplemented`, the same class test the dataclass's `__eq__` makes, so ordering and equality never disagree for a subclass | FR-008, FR-010 |
| `relation_to(other)` | Not a `PartialDate` → `TypeError`. `self.end < other.start` → `BEFORE`. `self.start > other.end` → `AFTER`. Otherwise `OVERLAPPING` | FR-012, FR-013 |

Errors: refused values raise `ValueError` (building and reading, FR-006). A value of the wrong type
as the other operand of an ordering operator or `relation_to` raises `TypeError` (D12).

Equality, hashing, immutability and `repr` come from the dataclass. Equality against another type
is `NotImplemented` and so `False` (FR-009, FR-010). Setting a field raises
`dataclasses.FrozenInstanceError` (FR-007). The sort key is computed inline in each ordering
method, so the class adds no public name beyond the table. No name in the module starts with an
underscore.

The sort key is read once, in the method, from both sides. It is never stored as a field, so
equality and hashing stay on the recorded parts alone.

### Tests

`tests/test_partial_date.py`, classes by subject (research R11). The sample-wide tests:

- **SC-002**: every value at every precision in years 1999 and 2000 (757 values), sorted, gives
  the same order as their ISO forms sorted as text. All four operators are checked against text
  comparison on every pair of a smaller sample (every precision in 1999–2000 for months 1, 2, 12
  and their days), so the pair count stays under 100,000.
- **SC-003**: over the same pair sample, `relation_to` returns `BEFORE` exactly when an
  independent coarser-precision rule, written in the test from the parts (truncate both to the
  coarser precision and compare the tuples), says the first is earlier. The rule is written out
  in the test, not derived from `start`, `end` or `relation_to`.
- **SC-004**: every value at every precision in years 0001, 1999, 2000 and 9999 reads back from its
  own ISO form unchanged and writes the same text.
- **SC-001**: the four prior-art defects each have a named test: mixed-precision ordering,
  hashing, a year-only value's unknown month and day, and refusing a change to a part.
- **SC-005**: `deptry` and an unchanged empty `dependencies` list in `pyproject.toml`. No test.

## Project structure

```text
partial_dates/
├── __init__.py          re-exports PartialDate, Precision, Relation
└── partial_date.py      new
tests/
└── test_partial_date.py new
README.md                Status, Usage section
CHANGELOG.md             [Unreleased] → Added
```

## Stories and dispatch

Three stories, each one dispatch group, built in order on the feature branch: US2 and US3 add
methods to the class US1 creates, so they cannot run in parallel. Each story extends the README's
*Usage* section with the names it adds.
