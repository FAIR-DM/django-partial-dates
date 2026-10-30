# Decisions — FS-004: Entering and editing a partial date

Decisions made while specifying, where the issue and the roadmap were silent. Each one came from
the goals, the constitution, FS-001, FS-002, FairDM's form field and widget as prior art, and
Django's `SelectDateWidget`, read at the version this package installs.

## The reading of the issue that the spec is written from

A user sees year, month and day selects, fills in what they know and leaves the rest empty, and can
add or take away a part on a later edit. Entries that make no sense, such as a day with no month,
are refused. A developer gets this from the model field in a model form and in the admin with
nothing declared, and can declare the form field on a form with no model. It serves G4 and depends
on #8, which is delivered. The move from django-partial-date (#20), display (R6) and the release
are out of scope.

## D1 — Two stories

Entering a date is what a user does. Getting that into forms and the admin is what a developer
does. The two are never merged. Every rule about what can be entered is a scenario under the first.
Admin use, plain forms, the options carried over from the model and the choice of years are
scenarios under the second.

**ADR:** none — how the specification is divided, not a design decision.

## D2 — A day with no month is refused, never dropped

FairDM's widget joins the parts with `if m and d`, so a day with no month is discarded without a
word and the date saves at a precision the user did not choose. The issue asks for this to be
stopped. The same goes for a month or a day with no year, which FairDM's widget joins into text
that is not a date.

**ADR:** none — the behaviour the issue asks for.

## D3 — A required field still takes a year alone

Django's `SelectDateWidget` leaves the empty choice out of all three selects when the field is
required. A required date would then have no way to say "year only", and the first year in the list
would be chosen for anyone who left it alone. Every select keeps its empty choice on every field.
"Required" means a year was given. FairDM's widget inherits this defect.

**ADR:** none — follows from G4.

## D4 — The offered years list choices, and limit nothing

The roadmap and GOALS.md fix the widget as selects. A select holds a fixed list, and FS-001 accepts
years 1 to 9999. So:

- With nothing said, a field offers 1900 to the current year, newest first, as FairDM's does.
- A developer can name the years for one field.
- A stored year outside the list is added to the list for that form. Django's widget would show
  another year or none, and saving would then lose the stored one.
- The form field accepts any year the value accepts, because that stored year has to survive being
  posted back. A limit is a validator, which Django already offers.
- The default list is worked out when the form is shown. FairDM's is worked out when the form class
  is defined, so a running server misses the new year until it restarts.

The default leaves a site recording pre-1900 dates naming its years. A longer default makes the
select harder to use for everyone else, and every option here is one line for a developer.

**ADR:** none — one field's default, changed in a line.

## D5 — Three error codes

The testing standard asserts errors by field and code, so the codes are part of the behaviour.
`required` and `invalid` are Django's own. `incomplete` is the code Django's `MultiValueField` uses
when a part is missing, and it separates "you have not said enough" from "that date does not
exist". The wording stays out of the specification and is translatable.

**ADR:** none — follows Django's conventions.

## D6 — No JavaScript

A list of days that follows the chosen month would need a script, which the package would have to
ship and a project would have to load, against FR-018 and Constitution Article II. The list holds 1
to 31 and a day that does not exist is refused on submission, as Django's own widget does.

**ADR:** none — follows Article II.

## D7 — Year, month, day in every language

Django orders its selects by the locale's date format, so a German form would start with the day.
The selects here read from what is known to what may not be, and they match the ISO form, as
FairDM's do. The order is a behaviour of the field, so it is stated in the specification.

**ADR:** none — a behaviour of the widget, stated in the specification.

## D8 — Typing a date is not part of this feature

FairDM also has a masked text field for `yyyy-mm-dd`. The issue, the roadmap and GOALS.md all
describe selects, and the roadmap moves the select field and widget. The text field is left where
it is. If a project needs one here, that is a new request.

**ADR:** none — a scope boundary.

## D9 — "The admin" means its add and change forms

The issue says a person enters and edits a date in the admin. Lists and `readonly_fields` are
display (R6). Filters and search are not entering a date. The model field is a direct `Field`
subclass, so nothing in the admin's default field overrides applies to it, and `formfield()` is the
only change it needs.

**ADR:** none — a scope boundary.

## D10 — The package still needs no app entry

`docs/developer/installation.md` says the package has no app to add to `INSTALLED_APPS`, and the
issue says nothing has to be configured. The widget therefore uses templates Django's form renderer
finds on its own. If planning finds that a template of the package's own is needed, it has to be
done without changing that sentence. A host project that translates the messages adds the package's
`locale` directory to `LOCALE_PATHS`.

**ADR:** none — keeps a promise already documented.

## D11 — A small example project serves the form and the admin

The package has no pages of its own, so the screens this feature adds cannot be walked. The
repository gains an `example/` directory:

- A Django project on SQLite, with one app and one model holding a required, an optional and a
  defaulted partial date field, an inline, an admin registration and one page with a plain form.
- A seed command that creates the staff and regular sign-ins and a row at each precision, including
  a year outside the default list.
- Run with `uv run python example/manage.py runserver 0.0.0.0:8033`. Port 8033 is the one this
  project keeps for it.
- Outside the wheel and the sdist, which already list what they include. Excluded from deptry, and
  its database file is ignored by git.

It is a task of User Story 2, not a story of its own, and R6 will use it for display. The tests stay
in `tests/`, which keeps its own app and adds `django.contrib.admin` and what that needs.

**ADR:** none — development tooling.

## D12 — No design prototype

No prototype is built. The widget is decided in GOALS.md and the roadmap, FairDM has run the same three
selects, the feature draws no page of its own, and everything it does can be asserted by a test.

**ADR:** none — a judgement for this feature only.

## D13 — Earlier text this feature changes

FS-002's assumption that a model form shows the field as plain text until R4, and the README's
"Form handling is not written yet", stop being true. Both are rewritten in the feature's pull
request to read as current, alongside a developer guide page on forms and the admin.

**ADR:** none — documentation that ships with the change.

## D14 — A `MultiWidget` and a `MultiValueField`, rebuilt rather than moved

GOALS.md calls FairDM's `SelectDateWidget` subclass the starting point. Its behaviour is kept and
its base class is not, because `SelectDateWidget` would need nearly every method replaced and still
drops the empty choices on a required field (research R1, R2). `MultiWidget` and `MultiValueField`
are Django's own way to build a value from parts.

**ADR:** none — inside one module, invisible to a developer using it.

## D15 — The form field shares the model field's name, in its own module

`partial_dates.forms.PartialDateField` sits beside `partial_dates.fields.PartialDateField`, as
`forms.DateField` sits beside `models.DateField`. The package root keeps exporting the model field
only. `PartialDateFormField`, FairDM's name, would be a second convention for the same relation.

**ADR:** none — follows Django's naming.

## D16 — Years are named on the widget

Naming years is a matter of display, and `PartialDateWidget(years=...)` reaches every route Django
already has: `Meta.widgets`, `formfield_overrides` and `widget=`. The form field and the model field
take no new argument (research R3).

**ADR:** none — a local API choice, documented in the guide.

## D17 — The label names the group

US-1 scenario 18 and FR-009 say the field's label leads to the year. Django renders a multi-part
widget in a `fieldset` with the label as its `legend`, which names the group, and the year is the
first select a keyboard reaches. A `for` on a `legend` would be invalid and would do nothing, so
none is added. The requirement is met that way (research R4).

**ADR:** none — follows Django's rendering.

## D18 — Test app additions

`Note`, a test model with a foreign key to `Record`, gives the admin tests an inline, because no
existing test model has a relation. `django.contrib.admin` and what it needs join the test settings
and `example/` only.

**ADR:** none — test scaffolding.
