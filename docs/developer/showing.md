# Showing a partial date

A reader should see a partial date at the precision it was recorded at, written the way their
language writes dates. A date known to the year reads as a year, and nothing suggests a month or a
day that nobody gave. `PartialDate.display_form()` gives that text. This page shows what it gives at
each precision, how to show it in a template, in Python and in the admin, and why it is a method and
not what `str()` returns.

## Get the display form of a date

Import the value, and Django's translation module if you need a language other than the active
one.

```python
>>> from django.utils import translation
>>> from partial_dates import PartialDate
```

Call `display_form()` on the value.

```python
>>> with translation.override("en"):
...     PartialDate(1990).display_form()
'1990'
>>> with translation.override("en"):
...     PartialDate(1990, 6).display_form()
'June 1990'
>>> with translation.override("en"):
...     PartialDate(1990, 6, 14).display_form()
'June 14, 1990'
```

The method returns text for the language active when you call it, so it needs Django's settings to
be configured, which any running project has.

## Show a date in a template

A template needs the package's app, because Django finds a tag library through an installed app.
Add it to `INSTALLED_APPS`. The app adds no model and needs no migration.

```python
INSTALLED_APPS = [
    # ...
    "partial_dates",
]
```

Load the library in the template and apply the filter.

```python
>>> from django.template import engines
>>> template = engines["django"].from_string(
...     "{% load partial_dates %}{{ value|partial_date }}"
... )
>>> with translation.override("de"):
...     template.render({"value": PartialDate(1990, 6)})
'Juni 1990'
```

An empty value, and anything that is not a partial date, renders as empty text, so the page raises
no error and Django's `default` filter supplies whatever a missing date should show.

```python
>>> template = engines["django"].from_string(
...     "{% load partial_dates %}{{ value|partial_date|default:'unknown' }}"
... )
>>> template.render({"value": None})
'unknown'
```

The text is escaped like any other text in the template. A template that shows a date with no
filter, as `{{ value }}`, still writes the ISO form.

## Show a date in the admin

Django's admin does not know the type, so in a list and in a read-only field it writes a partial
date as its ISO form, `1990-06`, whatever the language. Say once, on each admin class, that it
shows the display form.

1. Import the mixin. It is in its own module, so a project that does not use the admin never
   loads it.

   ```python
   from partial_dates.admin import PartialDateDisplayMixin
   ```

2. Put it before `ModelAdmin` in the bases of the admin class, and before `TabularInline` or
   `StackedInline` in the bases of an inline.

   ```python
   from django.contrib import admin

   from samples.models import Note, Sample


   class NoteInline(PartialDateDisplayMixin, admin.TabularInline):
       model = Note


   @admin.register(Sample)
   class SampleAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
       list_display = ["collected", "published"]
       readonly_fields = ["catalogued"]
       inlines = [NoteInline]
   ```

3. Open the admin. Nothing else needs declaring, and the admin needs no entry in
   `INSTALLED_APPS` for the package.

The mixin shows the display form for every partial date field of the model:

- in a list, where the column keeps its heading, its sorting by the stored order and its link to
  the row. A field in `list_editable` keeps its selects and saves as before.
- in a field of `readonly_fields`, under the label and help text of the model field, in a default
  layout, in `fields` and in `fieldsets`.
- on every field of a page a user may only view. A field the admin leaves out, with `exclude`,
  `fields` or the form's `Meta.fields`, stays off the page.
- in an inline, on a read-only field and on a page a user may only view, including a user who may
  view the parent and change the inline.

An empty value shows the admin's own empty display, which `empty_value_display` changes.

Some things keep the ISO form:

- A field reached through a relation, as `record__date` in `list_display`, because the mixin
  reads the fields of the admin's own model.
- A method on the admin or the model that returns a partial date. It shows what it returns, so
  call `display_form()` in it.
- An admin class with no mixin.
- The existing rows of an inline a user may add to. They are shown as Django shows them, and the
  new rows keep their selects.

The add page and the change page of a user who may change the row keep the year, month and day
selects for every field that is not read-only.

## Show a date in another language

Activate the language around the call. The same value reads in each language, including the name of
the month.

```python
>>> value = PartialDate(1990, 6, 14)
>>> with translation.override("de"):
...     value.display_form()
'14. Juni 1990'
>>> with translation.override("ja"):
...     value.display_form()
'1990年6月14日'
```

In a view, Django has already activated the language of the request, so call the method and use
the text. The method works without the app entry, and it gives the same text the filter renders.
The admin mixin uses the language of the request in the same way.

## What each precision shows

| Precision | Format Django applies | English | German |
|---|---|---|---|
| Year | `Y` | 1990 | 1990 |
| Month | `YEAR_MONTH_FORMAT` | June 1990 | Juni 1990 |
| Day | `DATE_FORMAT` | June 14, 1990 | 14. Juni 1990 |

A site that sets its own `YEAR_MONTH_FORMAT` or `DATE_FORMAT` in a format module sees its own
format here, as it does anywhere else Django writes a date. A year below 1000 has four digits at
every precision, so year 990 reads `0990`. The year never carries a thousands separator, whatever
the site's number settings.

## Try it in the example project

The example project in `example/` turns the mixin on for its sample admin, and its list page uses
the filter. After `uv run python example/manage.py seed`, sign in at `/admin/` as `view-only.user`
with the password `password` to read the samples and their notes as the display form with no
selects. `staff.user` changes them with the selects, and a browser asking for German
or Japanese reads the same dates in those languages. The example project's setup is in the
[forms guide](forms.md#run-the-example-project).

## Why the display form is a method

`str()` and `isoformat()` give `1990`, `1990-06` and `1990-06-14` in every language. Code that
stores, sorts and compares a date depends on that, so it does not change. The display form is
for a reader, and it is worked out each time from the language active at that moment, so one stored
value reads correctly for each person.

## Why a month does not read as a day

Each precision has a format that names only what was recorded. A month is written with the format
Django has for a month and a year, which names no day, so no day is written and none is invented.
