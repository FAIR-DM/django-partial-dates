# Feature Specification: A partial date value for Python code

**Feature Branch**: `001-partial-date-value`

**Created**: 2026-10-29

**Status**: Draft

**Serves**: G2 · **Roadmap**: R1 · **Issue**: #3

**Input**: A developer working with partial dates in Python needs a value they can trust: one that
holds only the year, month and day that were recorded, sorts and compares correctly whatever the
precision, can go in a set or be a dictionary key, and can say which days it might be. A developer
should also be able to ask whether one partial date is earlier than another and get an honest
answer when the two might overlap.

## Summary

A partial date value: an immutable Python object holding a year, and optionally a month and a day,
with the parts that were not recorded held as unknown. A developer builds one from its parts or
reads one from its ISO form, gets the ISO form back, sorts values, uses them as set members and
dictionary keys, asks for the start and end of a value's period, and asks whether one value is
before, after or overlapping another.

This feature is the value alone. The model field (R2), database lookups (R3), form handling (R4),
the move from django-partial-date (R5) and display to a reader (R6) build on it and are out of
scope. The words used here are defined in `CONTEXT.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A developer records a partial date in Python (Priority: P1)

A developer holding a date known to the year, the month or the day builds a partial date from its
parts, or reads one from its ISO form, and writes it back out in its ISO form. The value holds only
the recorded parts, says which precision it has, never changes once built, and refuses anything
that is not a real partial date.

**Why this priority**: Everything else in the package, and every other story here, needs a value
that holds exactly what was recorded.

**Independent Test**: Build values at each precision from parts and from the ISO form, read back
their parts, precision and ISO form, and confirm invalid input is refused.

**Acceptance Scenarios**:

1. **Given** the year 1990 alone, **When** a developer builds a partial date from it, **Then** the
   value has year precision, its year is 1990, and its month and day are unknown.
2. **Given** the year 1990 and month 6, **When** a developer builds a partial date, **Then** the
   value has month precision and its day is unknown.
3. **Given** the year 1990, month 6 and day 14, **When** a developer builds a partial date,
   **Then** the value has day precision and holds all three parts.
4. **Given** each of the texts `1990`, `1990-06` and `1990-06-14`, **When** a developer reads a
   partial date from it, **Then** the value equals the one built from the same parts.
5. **Given** a partial date at any precision, **When** a developer asks for its ISO form, **Then**
   the result is `YYYY`, `YYYY-MM` or `YYYY-MM-DD` as its precision requires, and reading that text
   back gives an equal value.
6. **Given** a year-precision value, **When** a developer reads its month or day, **Then** each is
   unknown, never a first month or a first day.
7. **Given** a day without a month, **When** a developer builds a partial date, **Then** it is
   refused.
8. **Given** a month outside 1–12, a day that does not exist in its month (`1990-02-30`,
   `1990-04-31`, `1990-02-29`), or a year outside 0001–9999, **When** a developer builds or reads
   a partial date, **Then** it is refused.
9. **Given** 29 February in a leap year (`2000-02-29`), **When** a developer builds or reads it,
   **Then** it is accepted.
10. **Given** a text that is not exactly one of the three ISO forms (`1990-6`, `19900614`,
    `90`, `1990-06-14T00:00`, `1990?`, `1990~`, ` 1990`, an empty text), **When** a developer reads
    a partial date from it, **Then** it is refused.
11. **Given** a part that is not a whole number, **When** a developer builds a partial date,
    **Then** it is refused.
12. **Given** a built partial date, **When** a developer tries to change one of its parts, **Then**
    the change is refused and the value is unchanged.
13. **Given** invalid input, **When** it is refused, **Then** the error is Python's standard error
    for an invalid value, and code that has not configured Django can catch it.

---

### User Story 2 - A developer sorts partial dates and keys collections by them (Priority: P1)

A developer with partial dates of mixed precision sorts them, tests them for equality, and uses
them as set members and dictionary keys, and gets the same order the database gives the stored
ISO form.

**Why this priority**: The replaced package's values compare wrongly across precisions and cannot
be hashed. Sorting and collecting values is the first thing code using them does.

**Independent Test**: Sort a mixed-precision list, compare pairs, and put values in a set and a
dictionary.

**Acceptance Scenarios**:

1. **Given** `1991`, `1990-06-14`, `1990` and `1990-06`, **When** a developer sorts them, **Then**
   the order is `1990`, `1990-06`, `1990-06-14`, `1991`.
2. **Given** any two partial dates, **When** a developer orders them, **Then** the order is the
   same as the order of their ISO forms compared as text.
3. **Given** two partial dates, **When** a developer tests them with each of `<`, `<=`, `>` and
   `>=`, **Then** every answer agrees with that order, at every combination of precisions.
4. **Given** two partial dates with the same recorded parts, **When** a developer compares them,
   **Then** they are equal and have the same hash.
5. **Given** `1990` and `1990-01-01`, or `1990-06` and `1990-06-01`, **When** a developer compares
   them, **Then** they are not equal.
6. **Given** several equal partial dates built separately, **When** a developer adds them to a set
   or uses them as dictionary keys, **Then** they count as one member or one key.
7. **Given** a partial date and something that is not a partial date (a real date, a text, a
   number), **When** a developer tests them for equality, **Then** they are not equal, and when a
   developer orders them, the comparison is refused.

---

### User Story 3 - A developer asks when a partial date could have been (Priority: P2)

A developer asks for the start and end of a partial date's period as real dates, and asks whether
one partial date is before, after or overlapping another, so that a rule such as "the end of
collection is not before its start" gets an honest answer when the two dates are recorded at
different precisions.

**Why this priority**: Sorting is not the same question as "is this one earlier?". Code that needs
a real date, or a chronological rule, otherwise has to invent one, which is what the replaced
package's value did and what FairDM's own coarser-precision helper works around.

**Independent Test**: Ask for the start and end of values at each precision, and compare pairs at
every combination of precisions.

**Acceptance Scenarios**:

1. **Given** `1990`, **When** a developer asks for its start and end, **Then** they are
   1 January 1990 and 31 December 1990, as real dates.
2. **Given** `1990-02` and `2000-02`, **When** a developer asks for their ends, **Then** they are
   28 February 1990 and 29 February 2000.
3. **Given** a day-precision value, **When** a developer asks for its start and end, **Then** both
   are that day.
4. **Given** `1990-06` and `1991`, **When** a developer asks how the first relates to the second,
   **Then** the answer is before, and asked the other way round, after.
5. **Given** `1990` and `1990-06`, or `1990-06` and `1990-06-14`, **When** a developer asks how
   one relates to the other, **Then** the answer is overlapping, in either order.
6. **Given** two equal partial dates, **When** a developer asks how one relates to the other,
   **Then** the answer is overlapping.
7. **Given** `1990-06-30` and `1990-07`, **When** a developer asks how the first relates to the
   second, **Then** the answer is before.
8. **Given** any two partial dates, **When** the answer is before, **Then** the first value's end
   is earlier than the second value's start, and when it is overlapping, their periods share at
   least one day.
9. **Given** a partial date and something that is not a partial date, **When** a developer asks how
   one relates to the other, **Then** the question is refused.

---

### Edge Cases

- The earliest and latest values, `0001`, `0001-01-01`, `9999` and `9999-12-31`, build, read,
  sort and give a start and end without error.
- Leap years follow the Gregorian calendar throughout, including century years (`1900-02-29` is
  refused, `2000-02-29` is accepted).
- Leading zeros are required in the ISO form (`0990`, not `990`), and a built value with a year
  below 1000 writes its year with four digits.
- Building a value with a month but no year is impossible: the year is always required.
- Two partial dates' periods are either nested or apart, never partly overlapping, because each
  period is a whole year, a whole month or a single day. "Overlapping" therefore means one period
  holds the other or they are the same.

## Clarifications

### Session 2026-10-29

- Q: What does reading a partial date from text accept beyond the three ISO forms? → A: Nothing.
  The text must be exactly `YYYY`, `YYYY-MM` or `YYYY-MM-DD`. Surrounding spaces, unpadded parts,
  the compact form without hyphens, times and EDTF level 1 markers are refused. Trimming what a
  person typed belongs to form handling (R4).
- Q: Which error does refused input raise? → A: Python's standard error for an invalid value, so the
  value works without Django configured. Turning it into a form or model error with a code is the
  field's and the form's job (R2, R4).
- Q: Is a day-precision partial date equal to the real date for the same day? → A: No. A partial
  date is equal only to another partial date with the same recorded parts, and ordering against a
  real date is refused. Mixing the two is where false certainty creeps back in, and an equality
  across types would break hashing.
- Q: What does "how one relates to the other" answer when the two are equal? → A: Overlapping.
  There are three answers only: before, after and overlapping. Equality is already answered by
  `==`.
- Q: Can a partial date be built from a real date? → A: Not in this feature. The deliverables are
  parts and the ISO form, and a real date's parts are one call away. It is added when a consumer
  needs it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (US1): A partial date MUST be buildable from a year, an optional month and an optional
  day, with an omitted part held as unknown.
- **FR-002** (US1): A partial date MUST be readable from exactly the three ISO forms, `YYYY`,
  `YYYY-MM` and `YYYY-MM-DD`, and from nothing else.
- **FR-003** (US1): A partial date MUST give back its year, month and day, an unknown part as
  `None`, and its precision as year, month or day.
- **FR-004** (US1): A partial date MUST give back its ISO form, and reading that form MUST give an
  equal value.
- **FR-005** (US1): Building or reading MUST refuse a day without a month, a month outside 1–12, a
  day that does not exist in its month and year, a year outside 0001–9999, and a part that is not
  a whole number.
- **FR-006** (US1): Refused input MUST raise Python's standard error for an invalid value. Building,
  reading and using a partial date MUST need no configured Django settings.
- **FR-007** (US1): A partial date MUST be immutable. It MUST never hold a part that was not
  given to it.
- **FR-008** (US2): Partial dates MUST be ordered as their ISO forms are ordered as text, through
  all of `<`, `<=`, `>` and `>=`.
- **FR-009** (US2): Two partial dates MUST be equal exactly when their recorded parts are equal,
  and equal values MUST have equal hashes.
- **FR-010** (US2): A partial date MUST NOT be equal to a value of another type, and ordering it
  against one MUST be refused.
- **FR-011** (US3): A partial date MUST give the start and the end of its period as real dates,
  the end taking month lengths and leap years into account.
- **FR-012** (US3): A partial date MUST answer, for another partial date, whether it is before,
  after or overlapping it: before when its period ends before the other's starts, after when it
  starts after the other's ends, and overlapping otherwise.
- **FR-013** (US3): Asking how a partial date relates to a value that is not a partial date MUST be
  refused.

### Key Entities

- **Partial date**: one calendar date recorded to the year, the month or the day. Holds a year,
  and optionally a month and a day. Has a precision, an ISO form and a period with a start and an
  end. Never changes once built.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: None of the value-class defects listed in `docs/reference/prior-art.md` can be
  reproduced: values of different precision order correctly, values hash, a year-only value
  reports no month or day, and no part can be changed after building.
- **SC-002**: For every pair of valid partial dates, the order the value gives is the order of
  their ISO forms compared as text, so Python and the database never disagree.
- **SC-003**: For every pair of partial dates, "before" is the answer exactly when the coarser-
  precision "is earlier" rule FairDM uses today answers yes, so that rule can be replaced without
  a change in behaviour.
- **SC-004**: Every valid ISO form from `0001` to `9999-12-31` reads and writes back unchanged.
- **SC-005**: The value works in code that has not configured Django.

## Assumptions

- The developer is writing Python that handles partial dates outside a model field, or will use
  this value through the field in R2.
- The calendar is the proleptic Gregorian calendar of Python's own dates, for every year from
  0001 to 9999.
- Showing a partial date to a reader in their language is R6. The ISO form is the only text this
  feature gives back.
- Empty values (no date at all) are the field's concern (R2). A partial date always has at least
  a year.
