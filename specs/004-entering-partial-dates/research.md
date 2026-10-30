# Research — FS-004: Entering and editing a partial date

Read against Django 6.1 as installed here, and against 5.2. The suite runs on 5.2, 6.0 and 6.1 at
the end of the build. A trial form built on the design below was run
before planning, and every outcome stated here came from it or from Django's source.

## R1 — The widget is a `MultiWidget`, not a `SelectDateWidget`

FairDM subclasses `forms.SelectDateWidget`, and GOALS.md names that widget as the starting point.
Rebuilt on the value type, almost none of the base class survives:

| What `SelectDateWidget` does | What this feature needs |
|---|---|
| Leaves out the empty choice when the field is required | Always an empty choice (FR-002) |
| Orders the selects by the locale's date format | Year, month, day in every language (FR-001) |
| `format_value` reads a date or date text | Reads a `PartialDate`, an ISO form or the parts of a refused entry (FR-003) |
| `value_from_datadict` builds date text, with zeros for empty parts | Keeps each part as given, for validation and for redisplay |
| Fixed year list | A year outside the list stays selectable (FR-004) |

FairDM's subclass overrides three of those and still has the first and the last defect.

`forms.MultiWidget` with three `forms.Select` subwidgets needs one method, `decompress`, and one
override, `get_context`, for the year list. Named subwidgets give `<name>_year`, `<name>_month` and
`<name>_day`. A refused entry comes back as the submitted list, so redisplay needs no code (FR-003).

## R2 — The form field is a `MultiValueField`

`forms.MultiValueField` with `require_all_fields=False` and three optional `IntegerField`
subfields does the reading:

- All parts empty gives `required`, or `None` on an optional field.
- A part that is not a whole number gives `invalid`, from `IntegerField`.
- `has_changed` compares part by part through `decompress`. A stored value, a default as text and
  the hidden initial of a callable default all compare correctly, because `decompress` reads ISO
  text (FR-008).
- `BoundField.build_widget_attrs` puts no `required` attribute on a select whose subfield is
  optional, so a browser does not demand a month.

`compress` is the only logic the package writes. Two things rule out letting `MultiValueField`
detect a missing part itself: it appends the bare `incomplete` message to its error list, which
loses the code, and it cannot see that a day depends on a month. `compress` raises `incomplete` for
a missing year or a day with no month, and turns the `ValueError` of `PartialDate` into `invalid`.

Trial outcomes, each on a required field: year only, year and month, and a full date are accepted.
All empty gives `required`. A day with no month and a month with no year give `incomplete`. `1900-02-29`,
month `13`, year `0`, text and a 5,000-digit year give `invalid`. A refused entry keeps its
selections.

## R3 — The offered years are set at render

A `Select`'s choices are fixed when it is built, and a form field is built when the form class is
defined. `PartialDateWidget.get_context` therefore sets the year choices on each render, from the
`years` the widget was given or from 1900 to today's year. A form's fields are deep-copied per
instance, widgets included, so this touches no other form. The value's own year is added when it
is not among them.

Naming the years goes on the widget: `PartialDateWidget(years=...)`, in `Meta.widgets`, in
`formfield_overrides`, or as `widget=` on the form field. These are the routes Django already gives,
so the form field and the model field take no new argument.

## R4 — The label is the group's legend

`MultiWidget.use_fieldset` is true and `id_for_label` returns nothing, so Django renders the field's
label as the `<legend>` of a `<fieldset>`, with no `for`. That is the correct structure for a group
of controls under WCAG 1.3.1. Keyboard focus reaches the year first because it is the first select.
Making the label point at the year would put a `for` on a `<legend>`, which is invalid HTML and does
nothing in a browser. Each select gets its own name from an `aria-label` (FR-009).

## R5 — The admin needs no code

`ModelAdmin.formfield_for_dbfield` looks the field's classes up in `formfield_overrides`. A direct
`models.Field` subclass matches nothing there, so it falls through to `formfield()`.

## R6 — Translation

Months come from `django.utils.dates.MONTHS`, which is lazily translated by Django's own catalog.
The package's messages use `gettext_lazy`. Without an app entry, Django does not find the package's
`locale` directory, so a project that translates them lists it in `LOCALE_PATHS`, as D10 says.

## What already exists

```
partial date value             · 2, repo    · partial_dates.partial_date.PartialDate
widget of three selects        · 4, Django  · django.forms.MultiWidget, django.forms.Select
reading and refusing the parts · 4, Django  · django.forms.MultiValueField, IntegerField
month names                    · 4, Django  · django.utils.dates.MONTHS
rendering                      · 4, Django  · django/forms/widgets/multiwidget.html
limiting the years accepted    · 4, Django  · a validator, not built
admin integration              · 4, Django  · ModelAdmin.formfield_for_dbfield
decompress and year list       · 7, new     · searched MultiWidget, SelectDateWidget, FairDM's widget
compress                       · 7, new     · searched MultiValueField, PartialDate
example project                · 7, new     · no project in the repository, D11
```
