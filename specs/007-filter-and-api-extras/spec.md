# Feature Specification: Ready-made django-filter filters and a Django REST framework field

**Feature Branch**: `007-filter-and-api-extras`

**Created**: 2026-10-30

**Status**: Draft

**Serves**: G10 · **Roadmap**: R8 · **Issue**: #30 · **Builds on**: FS-001, FS-002, FS-003, FS-004

**Input**: A developer whose project filters records with django-filter, or exposes them through
Django REST framework, should be able to use a partial date there without writing their own filter
or serializer field. These belong in optional extras, so a project that uses neither keeps Django
as the only dependency of the core package.

## Summary

Two optional extras, each installed on its own. The django-filter extra gives a developer a filter
for a partial date, a filter for a range of them, and filters on the year, month or day. The Django
REST framework extra gives a developer a serializer field that reads and writes the ISO form. A
project that installs neither has the same dependencies as today, and the core package never
imports either library.

A filter shows a site user the year, month and day selects FS-004 built, so they give as much of
the date as they know. The same filter reads the ISO form from a query string, so an API client can
send `?collected_after=1990-06`. Either way, an entry that is not a partial date is reported as an
error on that filter and never reaches the database.

A filter does what the lookup of the same name does, and FS-003's guide says what that is, with one
deliberate exception. A range is what a person means by "from June 1990 to March 1991", so its upper
bound takes in the whole of the period it names. Every filter documents which uncertain matches it
includes.

`PartialDateFilter`, `PartialDateRangeFilter` and the serializer field `PartialDateField` are the
public names. They live in `partial_dates.filters` and `partial_dates.rest_framework`.

Out of scope, each owned elsewhere:

- showing a partial date to a reader (R6, #28), which a serializer never does, because it writes the
  ISO form
- new lookups in the database, because every filter here uses what FS-003 delivered
- moving FAIR-DM to these filters, which is a change to that project

The words used here are defined in `CONTEXT.md`. This feature needs no sketch. It adds no page and
no new control, and everything it does can be tested.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A developer adds partial date filters to a filter set (Priority: P1)

A developer whose project uses django-filter installs the extra and declares a filter on a
`FilterSet` for a `PartialDateField`, or names the field in `Meta.fields`. They get a filter that
validates what it is given, for one date, a range of dates, or a year, month or day. They do not
write a form field, and they can read in the guide exactly what each filter finds.

**Why this priority**: It is the case that started the feature. FairDM carries its own filter class
and form field because no ready-made one exists, and django-filter refuses a `PartialDateField`
named in `Meta.fields` with nothing to map it to.

**Independent Test**: Install the extra, declare each filter on a `FilterSet`, and run it over rows
at each precision, on both databases, comparing the rows found with the tables in the guide.

**Acceptance Scenarios**:

1. **Given** the extra installed, **When** the developer declares
   `PartialDateFilter(field_name="collected", lookup_expr="gte")`, **Then** the filter finds the
   rows `collected__gte` finds for the same partial date, at a bound of each precision.
2. **Given** `PartialDateFilter` with each of the lookups `exact`, `gt`, `gte`, `lt` and `lte`,
   **When** it runs against `1990`, `1990-06` and `1990-06-14` with a bound of `1990-06`, **Then**
   the rows found are those FS-003's guide gives for that lookup.
3. **Given** `PartialDateRangeFilter(field_name="collected")` declared as `collected`, **When** it
   is given `collected_after=1990-06` and `collected_before=1991-03`, **Then** it finds the rows in
   FR-005's table.
4. **Given** the same filter, **When** only one of the two bounds is given, **Then** that bound
   alone applies.
5. **Given** a first bound that sorts after the second, **When** the filter runs, **Then** it finds
   nothing and reports no error, as FS-003's `range` does.
6. **Given** `PartialDateFilter(lookup_expr="year")`, and the same with `month` and `day`, **When**
   it is given a whole number, **Then** it finds the rows that lookup finds, so `month=6` leaves out
   `1990`, and a number no date can hold finds nothing.
7. **Given** a year, month or day filter, **When** it is given something that is not a whole number,
   such as `1990.5` or `June`, **Then** the filter reports an error and is not rounded or ignored.
8. **Given** a `FilterSet` that maps `PartialDateField` to `PartialDateFilter` through
   `Meta.filter_overrides`, **When** `Meta.fields` names the field with any of `exact`, `gt`, `gte`,
   `lt`, `lte`, `year`, `month`, `day` and `isnull`, **Then** each generated filter works, with no
   filter declared.
9. **Given** a field reached across a relation, such as `dates__value`, where one record holds many
   dates, **When** a range filter runs with both bounds, **Then** both bounds apply to the same
   date, so a record with one date before the range and one after it is not found.
10. **Given** the filter used by Django REST framework's filter backend, **When** a client sends a
    query string holding text that is not a partial date, **Then** the response is a client error
    naming the filter, and no server error occurs.
11. **Given** a query string holding the ISO form under the filter's own name, such as
    `?collected=1990-06`, **When** the filter set runs, **Then** it uses that date. **Given** the
    same parameter holding `1990-6`, **Then** the filter reports an error, and the text is not
    treated as no entry.
12. **Given** a developer who names the years offered by a filter's selects, **When** the filter
    renders, **Then** it offers those years, as `PartialDateWidget(years=...)` does on a form.
13. **Given** a project with the django-filter extra installed and not Django REST framework,
    **When** the developer uses the filters, **Then** everything works and Django REST framework is
    not imported.
14. **Given** the developer's guide, **When** they look up any filter in this feature, **Then** it
    says which uncertain matches the filter includes, for a bound at each precision.

---

### User Story 2 - A user narrows a list of records by date (Priority: P2)

A user of a site is looking at a list of records and wants the ones from a date, or from a stretch
of time. They give as much of each date as they know, as they would on any form holding a partial
date, and the list narrows to match. Something they enter that makes no sense is reported, and the
page keeps working.

**Why this priority**: It is what the developer's filter exists to give someone. It comes second
because it can only be reached through a filter set from Story 1.

**Independent Test**: Put a filter set behind a list page, submit the filter form with each kind of
entry, and read the rows listed and the errors reported.

**Acceptance Scenarios**:

1. **Given** a list with a date filter, **When** the user opens it, **Then** the filter offers a
   year, a month and a day to choose from, each of which can be left empty, and every record is
   listed, including those holding no date.
2. **Given** a range filter, **When** the user gives a year as the start and a year and a month as
   the end, **Then** the list shows the records in that stretch, including every record inside the
   whole of the month they chose as the end.
3. **Given** the user leaves every part of a filter empty, **When** they submit, **Then** that
   filter does not narrow the list.
4. **Given** the user gives a day and no month, **When** they submit, **Then** the filter reports
   the same `incomplete` error a form gives. **Given** a date that does not exist, such as 30
   February, **Then** it reports `invalid`. In both cases the page responds normally.
5. **Given** a list narrowed by a date, **When** the user keeps or shares the address of the page,
   **Then** opening that address shows the same list with the same parts selected.
6. **Given** a page opened from an address holding the ISO form, **When** it renders, **Then** the
   filter's selects show the parts of that date.
7. **Given** a record holding no date, **When** the user narrows the list by any date, **Then** that
   record is not listed.

---

### User Story 3 - A developer exposes a partial date through an API (Priority: P2)

A developer whose project uses Django REST framework installs the extra and declares a serializer
field for a partial date. Clients read the ISO form and write it, a client that sends anything else
gets an ordinary validation error, and the developer writes no field of their own.

**Why this priority**: It is the second half of the issue, and it stands alone. A `ModelSerializer`
already reads and writes the ISO form through Django REST framework's fallback, so what this adds
is a field for every serializer that is not generated from the model, and a refusal of empty text.

**Independent Test**: Declare the field on a plain `Serializer` and on a `ModelSerializer`, then
read and write a value at each precision, an empty value, and each refused input.

**Acceptance Scenarios**:

1. **Given** a serializer declaring the field, **When** it reads an object holding a partial date
   at each precision, **Then** the output is `1990`, `1990-06` or `1990-06-14`, with nothing added.
2. **Given** an object holding no date, **When** the serializer reads it, **Then** the output is
   `null`.
3. **Given** an object whose attribute still holds ISO text, such as an instance not yet read back
   from the database, **When** the serializer reads it, **Then** the output is that ISO form.
4. **Given** incoming data holding each ISO form, or a `PartialDate`, **When** the serializer
   validates it, **Then** the validated value is the `PartialDate` it names, and a `ModelSerializer`
   saves it.
5. **Given** a field declared with `allow_null=True`, **When** the client sends `null`, **Then** the
   validated value is `None`. **Given** a field without it, **Then** Django REST framework's own
   `null` error is reported.
6. **Given** incoming data that is not a partial date, such as `1990-6`, `1990-02-30`, an empty
   string, the number `1990` or a list, **When** the serializer validates it, **Then** it reports a
   field error with the code `invalid`, and nothing is written.
7. **Given** a required date on a `ModelSerializer` that declares this field, **When** a client
   sends an empty string, **Then** the response is a validation error and no database error occurs.
8. **Given** the field declared with `required`, `read_only`, `source` or a validator, **When** the
   serializer runs, **Then** each option behaves as it does on any Django REST framework field.
9. **Given** an HTML form posting to the API, **When** the entry is left empty on a field that
   allows `null`, **Then** the validated value is `None`.
10. **Given** a `ModelSerializer` with nothing declared, **When** a client reads and writes a value,
    **Then** it reads and writes the same ISO form this field does.
11. **Given** a project with the Django REST framework extra installed and not django-filter,
    **When** the developer uses the field, **Then** everything works and django-filter is not
    imported.

---

### Edge Cases

- A filter on a nullable field given no entry returns the rows holding no date with the rest.
- A filter with an entry never returns a row holding no date, which is what every bound in FS-003
  does.
- A year, a month or a day of `0`, a negative number or a number too large for any date finds
  nothing, and raises nothing.
- A range bound at the latest date the ISO form can hold, `9999` or `9999-12`, works as any other.
- A query string naming both the ISO form and the select parts of one filter uses the ISO form.
- An ISO form with spaces around it, or written in digits outside ASCII, is not a partial date, and
  is refused like any other text that is not one.
- Text longer than any ISO form, and text holding a NUL character, are refused with the same error
  on a filter and on the serializer field, and never reach the database.
- `range` and `in` are not offered through `Meta.fields`. The guide points to the range filter, and
  an `in` filter is declared by the developer.

## Clarifications

### Session 2026-10-30

- Q: Does a filter take the selects or text? → A: Both. A form shows FS-004's selects, because a
  user gives only what they know, and the ISO form is read from the filter's own name, because an
  API client has no selects to fill in.
- Q: Does a range follow FS-003's `range` lookup exactly? → A: No, on one point. FS-003's bound is a
  position, so `range` to `1991-03` leaves out `1991-03-15`. A person asking for a range up to March
  means all of March, so the upper bound takes in the last day of the period it names. A filter
  declared with `lookup_expr="lte"` is the plain lookup and keeps its position.
- Q: Does a filter make its uncertain matches symmetrical? → A: No. A range stays on the sort order
  of the ISO forms, so `1990` is left out of a range from `1990-06` and `1991` is in a range to
  `1991-03`. That is one rule, which a table shows, and it stays served by an index. A developer who
  needs another rule uses django-filter's `method` with FS-003's recipes.
- Q: What are the query parameters of a range? → A: `<name>_after` and `<name>_before`, the names
  django-filter gives its own date range filter, and the names FairDM's filters already use.
- Q: Does a `ModelSerializer` change with nothing declared? → A: No. It keeps Django REST
  framework's fallback, which writes the same ISO form. A required date should declare this field,
  because the fallback passes an empty string through to the database. The guide says so, and shows
  both declaring the field and naming it in `serializer_field_mapping`.
- Q: Are filtering by precision and the `isnull` lookups part of the ready-made filters? → A:
  `isnull` is reached through `Meta.fields` and django-filter's own boolean filter. No filter is
  added for it.
- Q: What are the extras called? → A: `django-filter` and `djangorestframework`, the names of the
  packages they install, so `django-partial-dates[django-filter]` says what it adds.

## Requirements *(mandatory)*

### Functional Requirements

**Extras**

- **FR-001**: The package MUST offer an extra `django-filter` and an extra `djangorestframework`,
  each installing one library at a version that supports every Django version the package supports.
- **FR-002**: The core package MUST NOT import django-filter or Django REST framework, and its
  required dependencies MUST stay as they are. Only the module of an extra imports its library.
  Installing one extra MUST NOT require the other.

**Filters**

- **FR-003**: `PartialDateFilter` MUST validate its entry as a partial date and apply the lookup it
  is given, with `exact` as the default and with `gt`, `gte`, `lt` and `lte`, finding the rows that
  lookup finds.
- **FR-004**: `PartialDateFilter` with `year`, `month` or `day`, and with a comparison on one of
  them, MUST take a whole number and find the rows that lookup finds.
- **FR-005**: `PartialDateRangeFilter` MUST take two optional bounds, `<name>_after` and
  `<name>_before`, and find a row when it sorts at or after the first and at or before the last day
  of the period of the second. For `1990-06` and `1991-03`:

  | Row | Found | Why |
  |---|---|---|
  | `1990` | no | Uncertain. Sorts before the first bound |
  | `1990-05-31` | no | Sorts before the first bound |
  | `1990-06` | yes | Equals the first bound |
  | `1990-06-14` | yes | Inside the range |
  | `1991` | yes | Uncertain. Sorts inside the range |
  | `1991-03` | yes | Equals the second bound |
  | `1991-03-15` | yes | Inside the period of the second bound |
  | `1991-03-31` | yes | The last day of that period |
  | `1991-04` | no | Sorts after that period |
  | no date | no | A row holding no date is never found by a bound |

- **FR-006**: A range filter MUST apply both of its bounds to the same date when the field is
  reached across a relation.
- **FR-007**: A filter taking a partial date MUST use the form field and the error codes of FS-004,
  offer its selects, accept the developer's choice of years, and read the ISO form from the filter's
  own query parameter, with the ISO form used when both arrive.
- **FR-008**: A filter MUST report an entry that is not a partial date or not a whole number as an
  error on that filter, before any query runs. It MUST NOT treat the entry as no entry, and MUST NOT
  let it reach the database.
- **FR-009**: Mapping `PartialDateField` to `PartialDateFilter` through `Meta.filter_overrides` MUST
  let `Meta.fields` name the field with `exact`, `gt`, `gte`, `lt`, `lte`, `year`, `month`, `day`
  and `isnull`.

**Serializer field**

- **FR-010**: The serializer field MUST write a value as its ISO form, and `None` as `null`, whether
  the object holds a `PartialDate` or ISO text.
- **FR-011**: The serializer field MUST read an ISO form, or a `PartialDate`, into a `PartialDate`.
- **FR-012**: The serializer field MUST refuse anything else with a field error with the code
  `invalid`, including an empty string in JSON input, and MUST leave `null`, `required`, `read_only`,
  `source`, validators and HTML form input to Django REST framework's own handling.

**Documentation and quality**

- **FR-013**: A developer's guide MUST cover installing each extra, every filter with its query
  parameters, and the serializer field, including when a `ModelSerializer` should declare it.
- **FR-014**: The guide MUST state, filter by filter, which uncertain matches are included, with a
  bound at each precision, as FS-003's guide does for lookups. The tests of every filter MUST cover
  a row at each precision on both sides of each boundary.
- **FR-015**: Every filter MUST behave the same on PostgreSQL and SQLite, tested on both.
- **FR-016**: Every message a person can read MUST be translatable.
- **FR-017**: The example project MUST offer the range filter on its list of samples, so a developer
  can try it on localhost.

### Key Entities

- **Filter**: A django-filter filter on a `PartialDateField`. It holds no data of its own.
- **Serializer field**: A Django REST framework field. The ISO form is its whole wire format.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer adds a validated partial date range to a filter set with one declaration
  and writes no form field.
- **SC-002**: A developer adds a partial date to a serializer with one declaration and writes no
  field class.
- **SC-003**: FairDM's date filters can be written with this package's filters and no filter class
  or form field of FairDM's own.
- **SC-004**: No entry tried against a filter or the serializer field, of any kind, produces a
  server error.
- **SC-005**: A project installing neither extra has the same required dependencies as before, and
  the package imports and runs in it with neither library present.
- **SC-006**: Every filter's uncertain matches can be read from the guide without reading the code.

## Assumptions

- FS-003's lookups and FS-004's form field and widget are delivered, and this feature changes what
  they do for nobody who already uses them.
- A project using these filters already runs django-filter's own `FilterSet`, views and templates.
  This package ships no list view and no filter template.
- API descriptions generated from a project's serializers see the field as text. This feature adds
  no integration with a schema generator.
- Filtering on a precision itself is reached with `isnull`, as FS-003's guide describes.
