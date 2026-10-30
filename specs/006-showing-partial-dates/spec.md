# Feature Specification: Showing a partial date to a reader

**Feature Branch**: `006-showing-partial-dates`

**Created**: 2026-10-30

**Status**: Draft

**Serves**: G7 · **Roadmap**: R6 · **Issue**: #28 · **Builds on**: FS-001, FS-002, FS-004

**Input**: A developer showing a recorded date on a page needs it to appear in the reader's locale
at its own precision, so a date known only to the year reads as that year and never as the first of
January. Getting this wrong is easy in a template today, which is how a reader ends up believing in
a day nobody recorded. The same should hold wherever a partial date is on show, including the
admin's change list and detail pages.

## Summary

How a partial date reaches someone reading a site. A user reads `1990` as a year, `1990-06` as a
month and year in their language, and `1990-06-14` as a full date in their language. No day or
month appears that nobody recorded.

A developer gets that text from a template filter or from Python, and says once on an admin class
that its list columns and read-only fields show it.

Everything else about a partial date stays as it is. `{{ value }}`, `str()`, `isoformat()`, the
stored value and every serialiser keep giving the ISO form, in every language.

Out of scope, each owned elsewhere:

- entering and editing a date, including the selects on the admin's change form (FS-004)
- ready-made django-filter filters and Django REST framework serializer fields (R8, #30), which
  read and write the ISO form
- moving FairDM's own formatting onto this package, which is a change to that project

Also out of scope:

- showing two dates as a span, such as `1990 to 1992`
- relative text, such as "3 years ago"
- calendars other than the Gregorian calendar
- a developer choosing a different format at the point of use
- the admin's sidebar filters, search and date hierarchy, which are not showing a stored value

The words used here are defined in `CONTEXT.md`. `1990`, `1990-06` and `1990-06-14` stand for
partial dates at year, month and day precision. This feature adds one term: the **display form** is
the text a partial date is shown to a reader as, in the active language at its own precision.

"Django's `YEAR_MONTH_FORMAT`" and "Django's `DATE_FORMAT`" mean the format of that name for the
active language, as `django.utils.formats` resolves it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A user reads a partial date in their own language, at the precision it was recorded (Priority: P1)

A user reading a page sees a date written the way their language writes dates, and sees exactly as
much of it as was recorded. A date known to the year reads as a year. Nothing suggests a month or a
day that nobody knows.

**Why this priority**: It is the feature. A reader cannot tell an invented 1 January from a recorded
one, so this is where the promise the rest of the package keeps reaches a person.

**Independent Test**: Produce the display form of a value at each precision in several languages,
and compare it with what Django's own formatting gives for that language.

**Acceptance Scenarios**:

1. **Given** a date at year precision, **When** a user reads it, **Then** they read the year, and
   no month or day appears.
2. **Given** a date at month precision, **When** a user reads it, **Then** they read the month and
   year as Django's `YEAR_MONTH_FORMAT` writes them, and no day appears.
3. **Given** a date at day precision, **When** a user reads it, **Then** they read the date as
   Django's `DATE_FORMAT` writes it.
4. **Given** one stored date and two users with different active languages, **When** each reads it,
   **Then** each reads it in their own language, including the month's name.
5. **Given** a site that shows numbers with a thousands separator, **When** a user reads a date at
   any precision, **Then** the year carries no separator.
6. **Given** a year below 1000, **When** a user reads it at each precision, **Then** the year is
   written the same way at all three.
7. **Given** a date at any precision and a site in any time zone, **When** a user reads it, **Then**
   it is the same date, with no shift to another day, month or year.
8. **Given** a staff user reading an admin list or a read-only field that shows the display form,
   directly or in an inline, **When** the page opens, **Then** they read what scenarios 1 to 7
   describe.
9. **Given** a staff user who may view a row but not change it, **When** they open it in an admin
   that shows the display form, **Then** every partial date on the page reads as scenarios 1 to 7
   describe.

---

### User Story 2 - A developer shows a partial date in a template, in Python and in the admin (Priority: P2)

A developer with a partial date on a page applies a template filter and gets the display form. Where
there is no template, such as an email subject, a CSV export or a chart label, they get the same
text in Python. On an admin class they say once that it shows the display form, and every partial
date in its list columns and read-only fields follows.

**Why this priority**: It is how User Story 1 reaches a page, but the display form can be produced
without the filter and the admin, so it follows.

**Independent Test**: Render a template using the filter, call the Python route, and open an admin
list and change page for a model with the field, in a project configured only as the documentation
says, and read what each shows.

**Acceptance Scenarios**:

1. **Given** a project with the package's app in `INSTALLED_APPS`, **When** a template loads the
   package's tag library and applies the filter to a partial date, **Then** it renders the display
   form for the active language.
2. **Given** an empty value, **When** the filter is applied, **Then** it renders empty text, so
   Django's `default` filter works after it and the reader never sees `None`.
3. **Given** a value that is not a partial date, **When** the filter is applied, **Then** it renders
   empty text and the page raises no error, as Django's `date` filter does.
4. **Given** code running outside a template, **When** a developer asks for the display form of a
   partial date, **Then** they get the same text the filter gives, for the active language.
5. **Given** a developer who activates a language for one block of code, **When** they ask for the
   display form inside it, **Then** they get that language's text.
6. **Given** a project whose format module sets its own `YEAR_MONTH_FORMAT` or `DATE_FORMAT`,
   **When** a date is shown, **Then** the project's format is used.
7. **Given** a template that shows a partial date with no filter, or code that calls `str()` or
   `isoformat()`, **When** any language is active, **Then** the result is the ISO form, and what is
   stored and what the serialisers write do not change.
8. **Given** the display form in a template with autoescaping on, **When** it renders, **Then** it
   is escaped like any other text.
9. **Given** a `ModelAdmin` that says once that it shows the display form, **When** a partial date
   field is named in `list_display`, **Then** the column shows the display form, and keeps its
   heading, its sorting and any link it has to the row.
10. **Given** the same admin, **When** a partial date field is in `readonly_fields`, **Then** it
    shows the display form under its own label, wherever the admin's `fields` or `fieldsets` place
    it.
11. **Given** an inline that says the same, **When** a partial date field on it is read-only,
    **Then** it shows the display form.
12. **Given** the same admin and a user who may view but not change a row, **When** the page opens,
    **Then** every partial date field on it shows the display form.
13. **Given** the same admin and a user who may change the row, **When** the change form opens,
    **Then** an editable partial date field still shows the selects of FS-004, and saving the form
    stores what it stored before.
14. **Given** the same admin and a partial date field in `list_editable`, **When** the list opens,
    **Then** the field can still be edited.
15. **Given** the same admin and a row with no date, **When** the row is shown, **Then** the admin's
    empty value display appears.
16. **Given** an admin that says nothing, **When** a partial date is shown, **Then** it shows the
    ISO form, as it does today, and no part is invented.
17. **Given** a project that does not add the package's app to `INSTALLED_APPS`, **When** it uses
    the Python route or the admin display, **Then** both work.
18. **Given** a project that adds the package's app to `INSTALLED_APPS`, **When** `makemigrations`
    runs, **Then** the app needs no migration and adds no model.

---

### Edge Cases

- A site with `USE_I18N = False` shows the display form in its `LANGUAGE_CODE`, as Django's own
  date formatting does.
- A language Django ships no formats for falls back as Django's own date formatting does.
- A year below 1000 reads with four digits, as Django's `Y` format writes it, so `0990` reads as
  `0990` at every precision.
- A partial date field reached through a relation in `list_display`, such as `sample__collected`,
  shows the ISO form. A developer who wants the display form there adds a method using the Python
  route.
- A method or callable a developer writes for `list_display` is left alone.
- A user who may add to an inline keeps the ISO form on that inline's existing rows. Django builds
  new and existing rows from one list of fields, and the new rows have to stay editable.
- The filter takes partial dates only. A `datetime.date`, including a period's start or end, already
  has Django's `date` filter, and gets empty text here as any other value does.

## Clarifications

### Session 2026-10-30

- Q: Which of Django's formats does a full date use? → A: `DATE_FORMAT`, the format Django itself
  uses for a date in a template and in the admin. It names the month, as a month-precision date
  does, so a list mixing precisions reads as one list, and `06/07/1990` cannot be misread. FairDM's
  helper uses `SHORT_DATE_FORMAT` and would change at this one precision when it moves over.
- Q: Does showing the display form change what `{{ value }}` or `str()` give? → A: No. FS-001 made
  the ISO form what a value turns into, and `str()` staying the same in every language is what lets
  code use it safely. The filter is what a developer reaches for to show a date to a reader.
- Q: Can the admin show the display form with nothing declared? → A: No. Django's admin calls
  `str()` on any field type it does not know and offers no hook for a field to supply its own
  display. Changing `str()` or patching Django are both ruled out, so a developer says so once on
  each admin class. Without that the admin shows the ISO form, which is honest but in no language.
- Q: Does "the admin's detail pages" include staff who may only view? → A: Yes. Django shows such a
  user every field as read-only, so it is the most common place an admin reads a date.
- Q: Does the template filter need an entry in `INSTALLED_APPS`? → A: Yes. Django finds tag
  libraries through installed apps, so a project using the filter adds the package's app. This is
  the only part of the package that needs it. The Python route, the admin display, the model field
  and the form field all work without it.
- Q: What happens to an empty value or something that is not a partial date in a template? → A: It
  renders empty text, as Django's `date` filter does. A template must not fail on a row with no
  date, and `default` then supplies whatever the site shows for a missing value.
- Q: Does this add strings to translate? → A: No. Month names and date formats come from Django's
  own translations for the active language, so the package adds nothing to its message catalog.
- Q: Does any of this need a design judgement that only a person looking at it can settle? → A: No.
  The feature adds no page and no control. It changes the text in places a page already has for it,
  and that text is computed, so a test can assert all of it. No prototype is built.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (US1): The display form of a date at year precision MUST hold the year and nothing else.
- **FR-002** (US1): The display form of a date at month precision MUST be written with Django's
  `YEAR_MONTH_FORMAT` for the active language, and MUST hold no day.
- **FR-003** (US1): The display form of a date at day precision MUST be written with Django's
  `DATE_FORMAT` for the active language.
- **FR-004** (US1): The display form MUST follow the language active when it is produced, not the
  language active when the value was read or the process started.
- **FR-005** (US1): The year in the display form MUST carry no thousands separator, whatever the
  site's number settings, and MUST be written the same way at all three precisions.
- **FR-006** (US1): The display form MUST NOT depend on the time zone.
- **FR-007** (US2): The package MUST provide a template filter, in a tag library of its own, that
  gives the display form of a partial date.
- **FR-008** (US2): The filter MUST give empty text for an empty value and for anything that is not
  a partial date, and MUST NOT raise an error.
- **FR-009** (US2): The filter's output MUST NOT be marked safe, so the template layer escapes it.
- **FR-010** (US2): The package MUST provide a way to get the display form in Python that needs no
  template and no request, and it MUST give the same text as the filter.
- **FR-011** (US2): `str()`, `isoformat()`, a partial date in a template with no filter, the stored
  value and the output of the serialisers MUST NOT change.
- **FR-012** (US2): A developer MUST be able to say once, on a `ModelAdmin` or an inline, that it
  shows the display form, with nothing to declare for each field.
- **FR-013** (US2): Such an admin MUST show the display form in `list_display` columns, in
  `readonly_fields` and on every field shown to a user who may view but not change the row.
- **FR-014** (US2): A column showing the display form MUST keep its heading, its sorting by the
  stored order and any link it has to the row.
- **FR-015** (US2): Such an admin MUST leave editable fields, `list_editable` columns, and methods
  and callables a developer wrote exactly as they would otherwise behave.
- **FR-016** (US2): Such an admin MUST show the admin's empty value display for a row with no date.
- **FR-017** (US2): Only the template filter MAY need an entry in `INSTALLED_APPS`. Adding that
  entry MUST add no model and need no migration.

### Key Entities

- **Display form**: the text a partial date is shown to a reader as, in the active language at its
  own precision. It is derived when it is shown, and it is never stored or parsed back.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across every language Django ships and all three precisions, the display form names no
  part that was not recorded.
- **SC-002**: A developer can show a partial date to a reader by adding one filter to a template,
  once the package's app is installed.
- **SC-003**: A developer gets the display form across an admin class with one declaration on it,
  and no partial date field of its model then shows the ISO form in a list or a read-only field, for
  any staff user who can open the page.
- **SC-004**: With any language active, every value already stored, serialised or written by
  `isoformat()` is unchanged by this feature.

## Assumptions

- The developer uses Django 5.2 LTS or the current stable release, as the constitution's stack
  article sets out.
- The site's language is chosen the way Django chooses it, usually by `LocaleMiddleware`. The
  package does not choose a language.
- Django's translations and format modules are the source of how a language writes a date. A
  language whose `YEAR_MONTH_FORMAT` or `DATE_FORMAT` a project dislikes is changed with a format
  module, which is Django's own mechanism.
