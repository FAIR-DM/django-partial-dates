# Entering a partial date

A person fills in a partial date with three selects: a year, a month and a day. They give the
parts they know and leave the rest empty, and the form gives you back a `PartialDate` at the
precision they entered, or `None` when they entered nothing. This page shows what the user sees,
how to declare the field on a plain Django form, and what each error means.

`partial_dates.forms.PartialDateField` is the form field and `partial_dates.forms.PartialDateWidget`
is the widget it renders with. The package root exports the model field of the same name, so import
the form field from `partial_dates.forms`. Neither needs an entry in `INSTALLED_APPS`, a template
setting or a static file, and neither uses JavaScript.

## Declare the field on a form

Declare `PartialDateField` as you would any other form field.

```python
>>> from django import forms
>>> from partial_dates import PartialDate
>>> from partial_dates.forms import PartialDateField

>>> class EventForm(forms.Form):
...     happened = PartialDateField()
```

The field renders as three selects named `happened_year`, `happened_month` and `happened_day`,
inside one `fieldset` whose `legend` is the field's label. Each select has an accessible name of
its own, saying which part it holds.

## Read what the user entered

Submit the form and read `cleaned_data`. The value is a `PartialDate` holding exactly the parts
the user gave.

```python
>>> form = EventForm({"happened_year": "1990", "happened_month": "", "happened_day": ""})
>>> form.is_valid()
True
>>> form.cleaned_data["happened"]
PartialDate(year=1990, month=None, day=None)

>>> form = EventForm({"happened_year": "1990", "happened_month": "6", "happened_day": "14"})
>>> form.is_valid()
True
>>> form.cleaned_data["happened"]
PartialDate(year=1990, month=6, day=14)
```

A field declared with `required=False` gives `None` when all three selects are empty.

```python
>>> class OptionalEventForm(forms.Form):
...     happened = PartialDateField(required=False)

>>> form = OptionalEventForm({"happened_year": "", "happened_month": "", "happened_day": ""})
>>> form.is_valid(), form.cleaned_data["happened"]
(True, None)
```

## Open a form on a stored date

Pass the stored value as the field's initial value, as a `PartialDate` or as its ISO text. Each
recorded part is selected and every unknown part is left empty, so the form shows nothing that was
not recorded.

```python
>>> form = EventForm(initial={"happened": PartialDate(1990, 6)})
>>> form["happened"].value()
PartialDate(year=1990, month=6, day=None)
>>> form = EventForm(initial={"happened": "1990-06"})
>>> form["happened"].value()
'1990-06'
```

Both open with the year `1990` and the month June selected, and the day empty. A stored year that
the year select does not list is added to it, so it is selected when the form opens and saving the
form keeps it.

## Change how much of a date is known

The user adds a part by choosing it, and takes a part away by emptying its select. The value is
recorded at the precision the selects now hold.

```python
>>> stored = PartialDate(1990, 6, 14)
>>> form = EventForm(
...     {"happened_year": "1990", "happened_month": "", "happened_day": ""},
...     initial={"happened": stored},
... )
>>> form.is_valid()
True
>>> form.cleaned_data["happened"]
PartialDate(year=1990, month=None, day=None)
>>> form.changed_data
['happened']
```

To reduce a full date to a year, the user empties both the month and the day. Emptying only the
month is refused, as the next section explains.

A form saved without touching it reports that nothing changed, at every precision.

```python
>>> form = EventForm(
...     {"happened_year": "1990", "happened_month": "6", "happened_day": "14"},
...     initial={"happened": stored},
... )
>>> form.is_valid(), form.changed_data
(True, [])
```

## Handle a refused entry

An entry that makes no sense is refused with an error on the field, and the form comes back with
every select showing what the user picked. Each error carries a code.

| Code | When |
|---|---|
| `required` | The field is required and all three selects are empty. |
| `incomplete` | A day is given without a month, or a month or day is given without a year. |
| `invalid` | The date does not exist, such as 30 February or 29 February 1900, or a submission no select can produce, such as text or a year of `0`. |

```python
>>> form = EventForm({"happened_year": "1990", "happened_month": "", "happened_day": "14"})
>>> form.has_error("happened", code="incomplete")
True
>>> form = EventForm({"happened_year": "1990", "happened_month": "2", "happened_day": "30"})
>>> form.has_error("happened", code="invalid")
True
>>> form = EventForm({"happened_year": "", "happened_month": "", "happened_day": ""})
>>> form.has_error("happened", code="required")
True
```

A refused entry is never saved with a part changed or dropped, and never raises. The messages are
translatable. They live in the `en` catalog under `partial_dates/locale`.

## Why a required field takes a year alone

Required means a year was given. The month and day selects always offer an empty choice, and so
does the year select, so a required field still takes a year on its own, and nobody records a year
by leaving the form alone. Django's own date widget leaves the empty choice out of a required
field, which would leave no way to say "year only".

## Why a day with no month is refused

Dropping the day would save a date the user did not enter, and the package keeps its promise never
to change a part someone gave. The entry is refused with `incomplete`, and the user decides which
part to change.

## Why the day list does not follow the month

The day select always lists 1 to 31. Following the month would need JavaScript, which the package
would have to ship and your project would have to load. A day that does not exist is refused with
`invalid` when the form is submitted, as it is in Django's own date widget.
