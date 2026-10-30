# Decisions — FS-006: Showing a partial date to a reader

Decisions made while specifying, where the issue and the roadmap were silent. Each one came from
the goals, the constitution, FS-001, FS-002, FS-004, FairDM's `format_partial_date()` as prior art,
and Django's admin and format code, read at the versions this package installs.

## The reading of the issue that the spec is written from

After this feature, a developer can show a partial date to a reader from a template, from Python
and in the admin, and a user reads it in their language at the precision it was recorded. Neither
way exists today, so it is a feature and no existing specification holds it.

It covers the text a date is shown as, and nothing about entering one (FS-004) or the extras for
django-filter and Django REST framework (#30). It serves G7 and depends on #8, which is delivered.

No question was put to the maintainer. Every place the issue was silent was filled as recorded
below, and each entry is open to being overruled when the specification is reviewed.

## D1 — Two stories

Reading a date is what a user does. Showing one is what a developer does. They are never merged.
The filter, the Python route and the admin are all one thing a developer sets out to do, so they
are scenarios under one story. Staff reading the admin are users, and are covered under the first
story.

**ADR:** none — how the specification is divided, not a design decision.

## D2 — A full date uses `DATE_FORMAT`, not FairDM's `SHORT_DATE_FORMAT`

The roadmap calls FairDM's helper the shape to generalise, and that helper writes a full date with
`SHORT_DATE_FORMAT`. The shape is kept and this one choice is not:

- `DATE_FORMAT` is what Django uses for a date in a template and in the admin, so a partial date at
  day precision reads like every other date on the page.
- It names the month, as `YEAR_MONTH_FORMAT` does, so a list mixing precisions reads as one list.
- `SHORT_DATE_FORMAT` gives `06/07/1990`, which a reader cannot place without knowing the locale.

Consequence: FairDM's day-precision text gets longer when it moves over, which that project can
weigh then.

**ADR:** none — one default, changed in a line.

## D3 — No format argument

The filter takes no format and the Python route takes no style. No caller here needs one, and three
precisions make a single format string the wrong shape, so an argument would need its own design. A
project that wants different text for a language uses a format module, which is Django's mechanism
and covers every use at once. If FairDM needs short dates beside long ones, that is a new request.

**ADR:** none — a scope boundary, under Article II.

## D4 — `str()` stays the ISO form

Making `str()` follow the language would give the admin and `{{ value }}` the display form with
nothing declared. It is rejected:

- FS-001 made `str()` the ISO form, and it is delivered behaviour.
- `str()` is used for logs, keys, f-strings and text a program reads back. Its result would change
  with whichever language the current request had, and `PartialDate.fromisoformat(str(value))` would
  stop working in any language but those that happen to match.
- `datetime.date` keeps `str()` as ISO and leaves display to formatting, and this follows it.

**ADR:** none — keeps a delivered contract.

## D5 — The admin needs one declaration on each admin class

The issue wants the display form wherever a date is on show, including the admin, and every other
part of this package works with nothing declared. The admin cannot:

- `display_for_field` in `django.contrib.admin.utils` handles field types it knows and otherwise
  calls `str()` on the value. It offers no method a field can define.
- The change list and `AdminReadonlyField` both go through it.
- Patching that function when the app loads would be a hidden global change to Django, and would
  miss modules that imported it by name. Reaching it through `flatchoices` would be a trick that
  also changes the admin's filters.

So a developer says so once on each `ModelAdmin` or inline. Until then the admin shows the ISO form,
which invents nothing, so a project is never worse off for not declaring it.

This was checked before the specification promised it. A throwaway mixin over `RecordAdmin` showed
the display form in `list_display`, in `readonly_fields` and to a view-only user, on Django 5.2 and
6.1. Saving through such an admin, `list_editable` and the row link were not tried, and the
specification's scenarios cover them. Two things it found, for the plan:

- Django compares a read-only callable by identity between `get_form` and `get_fieldsets`, so each
  field's callable has to be the same object across calls.
- `get_fieldsets` calls `get_fields`, which calls `get_readonly_fields`, so `get_readonly_fields`
  cannot ask for the fieldsets without recursing.

Whether the plan keeps that shape is for research. The specification only fixes that it is one
declaration.

**ADR:** none — the design is settled in the plan, and the reason is recorded here.

## D6 — "The admin's detail pages" means read-only display, including view-only staff

An editable field on the change form shows the selects of FS-004, and that stays. So the admin's
detail view means `readonly_fields`, and the page Django gives a user who may view a row and not
change it, where every field is read-only. Without that second case the people who only read the
admin would be the ones who keep the ISO form.

**ADR:** none — a scope reading.

## D7 — The template filter brings the first `INSTALLED_APPS` entry

Django discovers tag libraries through installed apps. FS-004's D10 kept the package free of an app
entry and that remains true of everything else, but `{% load %}` cannot work without one, short of
every project naming the library in `TEMPLATES`, which is more to explain and easier to get wrong.

The app has no models and no migrations, and importing the package while apps load was checked to
work. A side benefit is that an installed app's `locale` directory is found without `LOCALE_PATHS`.

`docs/developer/installation.md` says the package has no app to add, so that sentence is rewritten
in the feature's pull request.

**ADR:** none — follows Django's discovery of tag libraries.

## D8 — The filter gives empty text for anything it cannot show

It follows Django's `date` filter: an empty value or a wrong type renders empty, and `default` then
supplies what the site shows for a missing value. Showing a dash here would be choosing a project's
wording for it. A `datetime.date` is refused like any other value, because it has Django's own
filter, and accepting it would blur which one a developer should reach for. FairDM's helper accepts
one because of its own callers.

**ADR:** none — follows Django's convention.

## D9 — The year is written by Django's `Y`, not by `str(year)`

FairDM's helper writes the year with `str(year)`, giving `990`, while its other two precisions go
through Django's `Y` and give `0990`. One value must not change shape by precision, so all three use
`Y`. Going through Django's formatting rather than the number path also keeps a thousands separator
out of the year, which is the known trap with `{{ 1990 }}` under `USE_THOUSAND_SEPARATOR`.

**ADR:** none — a behaviour stated in the specification.

## D10 — No messages to translate

Month names and date formats come from Django for the active language, so the package adds nothing
to its catalog. Constitution Article VIII is met by using them.

**ADR:** none — follows from the design.

## D11 — A field reached through a relation keeps the ISO form

`list_display` can name `sample__collected`. The admin declaration covers fields on the model
itself, and the case above says what a developer does for the other, which is one method using the
Python route. Following relations would be more machinery than any present caller needs.

**ADR:** none — a scope boundary, under Article II.

## D12 — The admin's filters, search and date hierarchy are out of scope

They choose rows and do not show a stored value, as FS-004's D9 said for entry. `date_hierarchy`
needs a `DateField`, and `list_filter` listing ISO forms is a separate question if anyone raises it.

**ADR:** none — a scope boundary.

## D13 — No design prototype

No prototype is built. The feature adds no page and no control, the text goes in places pages
already have for it, and a test can assert all of it because it is computed.

**ADR:** none — a judgement for this feature only.

## D14 — Earlier text and files this feature changes

Rewritten in the feature's pull request to read as current:

- `CONTEXT.md` gains **display form**. It is not added now because the specification's branch
  carries the specification only.
- `docs/developer/installation.md`, for D7, alongside a developer guide page on showing a date.
- `README.md` and `CHANGELOG.md`, as Article VI asks, and R6 in `docs/ROADMAP.md`.
- The example project's list page and `SampleAdmin` use the display form, so it can be walked on
  port 8033. That is a task of User Story 2, not a story of its own.

**ADR:** none — documentation that ships with the change.

## D15 — Names: `display_form`, `partial_date`, `PartialDateDisplayMixin`

`PartialDate.display_form()` sits beside `isoformat()` and names the term in `CONTEXT.md`. The
filter reads as `{{ value|partial_date }}`, as `date` does for a date, and the library loads as
`{% load partial_dates %}`, the package's name. Article X puts the behaviour on the value, so a
free function like FairDM's `format_partial_date()` would be a second way in.

**ADR:** none — local API naming, documented in the guide.

## D16 — One mixin for a `ModelAdmin` and an inline

The specification asks for one declaration on either. They differ in one line, whether a user who
may add keeps an editable row, so a single class checks `InlineModelAdmin` rather than two classes
and a base.

**ADR:** none — local to one module.

## D17 — The three admin cases left untried are proved

Saving through such an admin, `list_editable` and the row link were run before planning and hold on
Django 5.2.18 and 6.1.2. `research.md` has the table and what the shape depends on.

**ADR:** none — evidence for the plan.

## D18 — A user who may add to an inline keeps the ISO form on its existing rows

Django builds new rows and existing rows from one set of fieldsets, and renders new rows with
`readonly_fields` alone, so a date cannot be the display form on one and a select on the other. New
rows must stay editable, so the existing rows of such an inline stay as Django shows them. The text
is the ISO form, which invents nothing. This is narrower than the specification's US-2 scenario 12
and is reported with the build.

**ADR:** none — a narrow edge left as Django gives it.

## D19 — Design review outcome

Verdict: changes requested, one high finding. Each was checked by running it.

- SEC-001 (high), remedied: the planned `get_readonly_fields` added every editable field on a
  view-only page, so a date the admin's form leaves out through `Meta.fields` reached view-only
  staff. The mixin now adds nothing and only substitutes names Django lists, and `get_formset`
  passes string names. Proved on Django 5.2.18 and 6.1.2, and T010 tests it.
- SPEC-001 (medium), remedied: a user who may view the parent and change the inline saw the ISO
  form. The inline now asks the parent admin, and T010 tests it. D18 records the narrower case that
  remains.
- ARCH-001 (medium), remedied: one proxy model could not express the cases, and needed a migration
  and a factory. Each test now declares its own admin on a fresh `AdminSite`, with no new model. The
  `editable=False` case is dropped: the mixin substitutes only what Django lists, and the form-field
  cases already exercise that.
- SPEC-002 (low), taken: `USE_I18N=False` and a language with no formats join T001.
- ARCH-002 (low), taken: headings, labels and help text are read from the model field.
- Notes taken: the escaping test in T004 uses a format that emits `<`, `display_form` says it needs
  settings, and `tests/test_templatetags/__init__.py` is in the plan. The note that the time zone
  test guards rather than proves FR-006 is accepted.

**ADR:** none — corrections to this feature's plan.

## D20 — Two gaps found reading the finished mixin

Reading the diff before accepting the story found two ways the mixin behaved worse than Django, each
fixed by the orchestrator because each was a line or two with its test already written.

- An unsaved row holds a default given as text, so a read-only field on the add page reached the
  admin's empty display. The callable now reads through `field.to_python`.
- `ModelAdmin.get_form` removes a declared form field by its name, which a callable no longer
  matches, so a read-only field the form declares was still required. The mixin's `get_form` removes
  it. Django's inline `get_formset` has no such step, so an inline stays as Django leaves it.

**ADR:** none — local to the mixin.
