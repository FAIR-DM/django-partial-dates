# Entering a partial date

A person fills in a partial date with three selects: a year, a month and a day. They give the
parts they know and leave the rest empty, and the form gives you back a `PartialDate` at the
precision they entered, or `None` when they entered nothing. A model form and the admin use the
selects for a `PartialDateField` with nothing for you to declare. This page shows what the user
sees, how to use the field in a model form, in the admin and on a plain Django form, how to name
the years it offers, and what each error means.

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

## Use the field in a model form

Declare nothing about the form field. A model form built on a model with a `PartialDateField`
shows the three selects.

```python
class Record(models.Model):
    date = PartialDateField(
        null=True, blank=True, help_text="When the record happened."
    )
```

```python
>>> from django.forms import modelform_factory
>>> RecordForm = modelform_factory(Record, fields=["date"])
>>> type(RecordForm.base_fields["date"]).__module__
'partial_dates.forms'
>>> form = RecordForm({"date_year": "1990", "date_month": "6"})
>>> form.is_valid()
True
>>> form.cleaned_data["date"]
PartialDate(year=1990, month=6, day=None)
```

Saving the form stores the value at the precision entered, and editing a row moves it between
precisions. Saving a row without touching it leaves it as it was and reports no change.

The model field's options carry over:

- `blank=True` makes the date optional, and without it the year is required.
- `verbose_name` and `help_text` become the form field's label and help text.
- A `default`, whether a `PartialDate`, its ISO text or a callable, is selected when the form opens
  on a new row, and saving the form unchanged stores it.
- `unique=True` refuses a date another row holds at the same precision, with the error code
  `unique` on the field.
- A validator on the model field receives the `PartialDate`, and its error appears on the field.

```python
>>> RecordForm.base_fields["date"].required
False
>>> str(RecordForm.base_fields["date"].help_text)
'When the record happened.'
```

## Use the field in the admin

Register the model as you would any other. The admin shows the three selects on the add and
change forms, and in inlines, with no form or widget override.

```python
from django.contrib import admin


class NoteInline(admin.TabularInline):
    model = Note


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    inlines = [NoteInline]
```

Lists, `readonly_fields`, filters and search show the date as they show any other value, and are
not changed by the package.

## Name the years

With nothing said, a field offers the years from the current year down to 1900, newest first. The
current year is read each time the form is shown, so a server that is already running offers the
new year when it arrives.

To offer other years, pass them to the widget as a list, a range or a generator. They are shown in
the order you give them.

```python
>>> from partial_dates.forms import PartialDateWidget

>>> class SurveyForm(forms.Form):
...     surveyed = PartialDateField(
...         widget=PartialDateWidget(years=range(2030, 1799, -1))
...     )
```

The widget reaches every route Django offers for choosing a widget. In a model form, name it in
`Meta.widgets`. In the admin, name it in `formfield_overrides` or in a form of your own.

```python
>>> class NamedYearsForm(forms.ModelForm):
...     class Meta:
...         model = Record
...         fields = ["date"]
...         widgets = {"date": PartialDateWidget(years=range(2030, 1799, -1))}
```

Naming years changes the one field. Other fields on the form keep the default list.

The years you offer are what the select lists, and they limit nothing. A stored year the list does
not hold is added to it when the form opens, so saving the form keeps it. The field accepts any year
a `PartialDate` accepts.

```python
>>> form = SurveyForm({"surveyed_year": "1650"})
>>> form.is_valid()
True
>>> form.cleaned_data["surveyed"]
PartialDate(year=1650, month=None, day=None)
```

A year below 1000 is recorded with four digits, so choosing `990` records `0990`.

## Limit the dates with a validator

To refuse dates outside a range, add a validator to the model field or to the form field. It
receives the `PartialDate`, and the error it raises appears on the field.

```python
>>> from django.core.exceptions import ValidationError

>>> def not_before_1950(value):
...     if value.year < 1950:
...         raise ValidationError("Enter a date from 1950.", code="too_early")

>>> class RecentForm(forms.Form):
...     when = PartialDateField(validators=[not_before_1950])

>>> RecentForm({"when_year": "1900", "when_month": "6"}).has_error("when", code="too_early")
True
>>> RecentForm({"when_year": "1990"}).is_valid()
True
```

## Translate the messages

The messages the field shows, and the names on the selects, are translatable. The package carries
the `en` catalog under `partial_dates/locale`. The month names come from Django and follow the
active language already. To translate the rest into a language:

1. Copy `partial_dates/locale/en/LC_MESSAGES/django.po` to `locale/<language>/LC_MESSAGES/django.po`
   in your project.
2. Translate each `msgstr`, and set the `Language` header.
3. Run `python manage.py compilemessages`.
4. Check that `LOCALE_PATHS` in your settings lists your project's `locale` directory.

The order of the selects stays year, month, day in every language.

## Run the example project

The repository holds a small project, in `example/`, that serves a model form, a form with no
model and the admin, so you can try the field before you use it. Run these commands from a clone
of the repository, once the development environment is installed with `uv sync`.

1. Create the database and fill it.

   ```console
   $ uv run python example/manage.py migrate
   $ uv run python example/manage.py seed
   ```

   The `seed` command is safe to run again. It adds a sample at each precision, one in 1850 and
   one in 0990, and four sign-ins.

2. Start the server.

   ```console
   $ uv run python example/manage.py runserver 8033
   ```

3. Open `http://localhost:8033/`. The list links to each sample, to a page that adds one, to a
   page with a form that has no model and shows what it cleaned, and to the admin.

The sign-ins `regular.user`, `staff.user`, `super.user` and `view-only.user` each have the email
address of their name at `example.com`, and all have the password `password`. The staff user can add
and change the sample models in the admin, and the view-only user can read them. They are for use on
your own machine, and the project is not set up to be served to anyone else.

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

## Why the offered years limit nothing

A select holds a fixed list, and a partial date accepts years 1 to 9999. If the list were a limit,
editing a row that holds 1850 would lose the year the moment it was saved, because the list starts
at 1900. The list is a convenience for choosing, and a validator is the way to say a date is not
allowed.
