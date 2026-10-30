# Feature Specification: Entering and editing a partial date

**Feature Branch**: `004-entering-partial-dates`

**Created**: 2026-10-30

**Status**: Draft

**Serves**: G4 · **Roadmap**: R4 · **Issue**: #19 · **Builds on**: FS-001, FS-002

**Input**: A person recording a date needs to enter as much of it as they know and no more: a year,
a year and month, or a full date, and to change how much they know when they come back to edit it.
They should be stopped from saying something that makes no sense, such as a day with no month. A
developer who puts a partial date field on a model should get this in their forms and in the Django
admin without configuring anything.

## Summary

How a partial date gets into a site. A user sees a year, a month and a day select, fills in the
parts they know, and leaves the rest empty. Coming back to edit, they see what was recorded and
nothing else, and can add a part or take one away. An entry that makes no sense is refused with a
reason, and the form comes back as they left it.

A developer gets all of this from the model field: a model form and the admin use it with nothing
declared. For a form with no model behind it, the package provides the form field to declare
directly, and a developer can say which years a field offers.

Out of scope, each owned elsewhere:

- converting a column written by django-partial-date (R5, #20)
- showing a partial date to a reader, including in the admin's lists and on read-only fields (R6)
- ready-made django-filter filters and Django REST framework serializer fields (R8)
- moving FairDM and django-literature onto this package, which are changes to those projects

Also out of scope: typing a date as text, a calendar picker, and dates before year 1, which the
partial date value does not hold.

The words used here are defined in `CONTEXT.md`. `1990`, `1990-06` and `1990-06-14` stand for
partial dates at year, month and day precision.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A user enters and edits a partial date, giving as much of it as they know (Priority: P1)

A user filling in a form picks the year, and the month and day if they know them. When they know
more or less than was recorded, they come back and change it. They cannot record something that
makes no sense, and when they try, they are told why and keep what they entered.

**Why this priority**: It is the feature. Being able to say how much of a date is known is why the
form exists, and a form that invents or drops a part breaks the promise the rest of the package
keeps.

**Independent Test**: Submit a form holding a partial date field with each combination of filled
and empty selects, on a blank form and on one holding a stored value at each precision, and read
what was stored and what the form showed.

**Acceptance Scenarios**:

1. **Given** a blank form, **When** the user picks a year and leaves the month and day empty,
   **Then** a date at year precision is recorded, with no month or day.
2. **Given** a blank form, **When** the user picks a year and a month and leaves the day empty,
   **Then** a date at month precision is recorded, with no day.
3. **Given** a blank form, **When** the user picks a year, a month and a day, **Then** a date at day
   precision is recorded.
4. **Given** a field that requires a date, **When** the form is shown, **Then** the month and day
   can still be left empty, and the year starts with nothing chosen, so nobody records a year by
   leaving the form alone.
5. **Given** a stored date at any precision, **When** the user opens the form, **Then** each
   recorded part is selected and each unknown part is empty, so nothing is shown that was not
   recorded.
6. **Given** a stored `1990`, **When** the user adds a month, or a month and a day, **Then** the
   date is recorded at the new precision.
7. **Given** a stored `1990-06-14`, **When** the user empties the day, or the month and the day,
   **Then** the date is recorded at the new precision, and the emptied parts are gone from it.
8. **Given** a stored date at any precision, **When** the user saves the form without touching it,
   **Then** the stored value does not change, and the form reports that nothing changed.
9. **Given** a field that allows no date, **When** the user empties all three selects, **Then** no
   date is recorded.
10. **Given** a field that requires a date, **When** the user submits with all three selects empty,
    **Then** the entry is refused with the error code `required`.
11. **Given** any form, **When** the user picks a day without a month, **Then** the entry is refused
    with the error code `incomplete`, whether the day was picked on a blank form or the month was
    emptied on a stored date, and the day is never dropped silently.
12. **Given** any form, **When** the user picks a month or a day without a year, **Then** the entry
    is refused with the error code `incomplete`.
13. **Given** any form, **When** the user picks a day that does not exist in its month and year,
    such as 30 February or 29 February 1900, **Then** the entry is refused with the error code
    `invalid`, and 29 February 2000 is accepted.
14. **Given** an entry that was refused, **When** the form comes back, **Then** the error is on the
    partial date field, every select shows what the user picked, including the parts of a
    combination that makes no sense, and nothing has been saved.
15. **Given** a stored date whose year is not among the years the field offers, **When** the user
    opens the form, **Then** that year is selected, and saving the form keeps it.
16. **Given** a submission that no select can produce, such as text, a year of `0000` or a month of
    `13`, **When** it reaches the form, **Then** it is refused with the error code `invalid`, and
    the site gives an error on the form, never a server error.
17. **Given** a site running in any language, **When** the form is shown, **Then** the selects come
    in the order year, month, day, and the months are named in the active language.
18. **Given** a user of a screen reader or a keyboard, **When** they move through the field,
    **Then** each select has a name of its own saying which part it holds, and the field's label
    leads to the year.
19. **Given** a browser running no JavaScript, **When** the user does any of the above, **Then** it
    works the same.

---

### User Story 2 - A developer gets partial date entry in their forms and the admin, with nothing to configure (Priority: P2)

A developer who has a partial date field on a model builds a model form or registers the model in
the admin, and the field is ready to use. A developer writing a form with no model behind it
declares the form field and gets a partial date back. If the years a field offers do not suit the
data, the developer says which years it offers.

**Why this priority**: It is how User Story 1 reaches a site, but the form field works without it,
so it follows.

**Independent Test**: In a project that declares nothing for the package, build a model form and an
admin for a model with the field, and a plain form declaring the form field, and submit each.

**Acceptance Scenarios**:

1. **Given** a model with a partial date field, **When** the developer builds a model form for it
   and declares nothing about the field, **Then** the form shows the three selects, and saving
   stores a partial date.
2. **Given** that model registered in the admin, with no form or widget override, **When** a staff
   user adds or changes a row, directly or in an inline, **Then** the field behaves as in User
   Story 1.
3. **Given** a form with no model, **When** the developer declares the package's form field and the
   form is submitted, **Then** the cleaned value is a partial date value, or `None` for no date.
4. **Given** a model field, **When** its form field is built, **Then** the field's `blank`,
   `verbose_name` and `help_text` carry over: `blank=True` makes the date optional, and the other
   two become the form field's label and help text.
5. **Given** a model field with a default, as a partial date value, as its ISO form or as a
   callable, **When** the form opens on a new row, **Then** the default is selected, and saving the
   form unchanged stores it.
6. **Given** a model field declared `unique`, **When** a user enters a date another row holds at the
   same precision, **Then** the entry is refused with the error code `unique`, on the field.
7. **Given** a validator on the model field or the form field, **When** the form is submitted,
   **Then** the validator receives the partial date value, and its error appears on the field.
8. **Given** a developer who says nothing about years, **When** the form is shown, **Then** it
   offers 1900 to the current year, newest first.
9. **Given** a developer who names the years for one field, **When** the form is shown, **Then**
   that field offers those years, and other fields keep theirs.
10. **Given** a form that is already running, **When** the calendar year changes, **Then** the
    default list offers the new year with no restart.
11. **Given** a project that adds nothing to `INSTALLED_APPS`, `TEMPLATES` or its static files for
    this package, **When** a form holding the field is rendered, **Then** it renders and works.
12. **Given** two partial date fields on one form, or one field in a form with a prefix or in a
    formset, **When** the form is submitted, **Then** each value is read and validated on its own.

---

### Edge Cases

- A year below 1000 offered by a developer is recorded with four digits, so picking `990` records
  `0990`, and a stored `0990` opens with that year selected.
- An offered year that the partial date value refuses, such as `0`, is refused on submission like
  any other entry the value refuses.
- A submission that leaves out some of the selects entirely is read as if they were empty.
- A field with `blank=True` and no `null=True` behaves as Django's date field does: emptying it
  fails at the database, and a developer who wants no date declares both.
- `editable=False` and `choices` on the model field behave as they do on any Django field.

## Clarifications

### Session 2026-10-30

- Q: What does "required" mean for a field whose month and day are optional? → A: The year is
  required. A required field still takes a year alone, so its month and day selects always have an
  empty choice, and its year starts with nothing chosen.
- Q: When a month is emptied while a day stays selected, is the day dropped? → A: No. The entry is
  refused, because dropping it would save something the user did not say. To reduce a full date to
  a year, the user empties both.
- Q: Are the offered years a limit? → A: No. They are what the select lists. The form accepts any
  year the partial date value accepts, so a stored year outside the list survives an edit. A
  developer who wants a limit adds a validator.
- Q: Does the list of days follow the chosen month? → A: No. It always holds 1 to 31, which needs
  no JavaScript, and a day that does not exist is refused on submission.
- Q: Which error says what? → A: `required` for an empty required field, `incomplete` when a part
  is given without the part it depends on, `invalid` for a date that does not exist or a submission
  no select can produce. The message says what is wrong in words a user can act on, and it is
  translatable.
- Q: What does "the admin" cover? → A: The add and change forms, inlines included. Lists,
  `readonly_fields`, filters and search are not entering a date.
- Q: Can a date be typed? → A: Not in this feature. The roadmap's form is three selects.
- Q: Does any of this need a design judgement that only a person looking at it can settle? → A: No.
  The three selects are already decided, the feature adds no page of its own, and everything it
  does can be asserted by a test, so no prototype is built.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** (US1): The package MUST provide a widget of year, month and day selects, in that order
  in every language.
- **FR-002** (US1): The month and day selects MUST always offer an empty choice, and so MUST the
  year select, on every field, including one that requires a date.
- **FR-003** (US1): A stored value, a default and a refused entry MUST each open with exactly the
  parts they hold selected, and every other select empty.
- **FR-004** (US1): The year of the value being shown MUST be selectable even when it is not among
  the years the field offers.
- **FR-005** (US1): The package MUST provide a form field whose cleaned value is a partial date
  value at the precision entered, or `None` for no date.
- **FR-006** (US1): The form field MUST refuse an empty entry on a required field with the code
  `required`, a day without a month or a part without a year with the code `incomplete`, and a date
  that does not exist or a submission no select can produce with the code `invalid`.
- **FR-007** (US1): An entry MUST NOT be saved with a part the user did not give, and a part the
  user gave MUST NOT be dropped.
- **FR-008** (US1): The form field MUST report no change when the submitted parts equal the initial
  value, whichever form the initial value takes.
- **FR-009** (US1): Every select MUST carry an accessible name of its own, and the field's label
  MUST lead to the year select.
- **FR-010** (US1): The widget and the form field MUST work with no JavaScript.
- **FR-011** (US1): Every message a user can see MUST be translatable, and the months MUST be named
  in the active language.
- **FR-012** (US2): The model field's `formfield()` MUST return the package's form field, with the
  field's standard options carried over.
- **FR-013** (US2): The admin MUST use that form field for the model field with no override, on its
  add and change forms and in inlines.
- **FR-014** (US2): A developer MUST be able to declare the form field on a form with no model.
- **FR-015** (US2): With nothing said, a field MUST offer 1900 to the current year, newest first,
  with the current year read when the form is shown.
- **FR-016** (US2): A developer MUST be able to name the years one field offers.
- **FR-017** (US2): The offered years MUST NOT limit what the form field accepts.
- **FR-018** (US2): Using the form field MUST need no entry in `INSTALLED_APPS`, no template setting
  and no static files.

### Key Entities

- **Partial date form field**: the form's half of the model field. It reads what was submitted and
  gives back the partial date value from FS-001, or `None`, or a refusal.
- **Partial date widget**: the year, month and day selects a user fills in.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can record a date at each of the three precisions, and move a stored date
  between any two of them, by changing the selects and saving, with no other step.
- **SC-002**: Across every combination of empty, valid and impossible year, month and day, an
  entry is either stored with exactly the parts given or refused with a reason. None is stored with
  a part changed or dropped, and none gives a server error.
- **SC-003**: Saving a form unchanged leaves every stored value as it was, at every precision,
  including years the field does not offer.
- **SC-004**: A developer adds the field to a model and has working entry in a model form and in the
  admin with no line of code about the form field, the widget or the package's settings.

## Assumptions

- The developer uses Django 5.2 LTS or the current stable release, as the constitution's stack
  article sets out.
- A site that needs years before 1900 by default names them for the field. The default list follows
  the form FairDM already runs.
- Typing a date, as FairDM's masked text field does, stays with whoever needs it. The form field
  makes no promise about any widget but its own.
