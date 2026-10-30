# Showing a partial date

A reader should see a partial date at the precision it was recorded at, written the way their
language writes dates. A date known to the year reads as a year, and nothing suggests a month or a
day that nobody gave. `PartialDate.display_form()` gives that text. This page shows what it gives at
each precision, how to show it in a template and in Python, and why it is a method and not what
`str()` returns.

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

## Why the display form is a method

`str()` and `isoformat()` give `1990`, `1990-06` and `1990-06-14` in every language. Code that
stores, sorts and compares a date depends on that, so it does not change. The display form is
for a reader, and it is worked out each time from the language active at that moment, so one stored
value reads correctly for each person.

## Why a month does not read as a day

Each precision has a format that names only what was recorded. A month is written with the format
Django has for a month and a year, which names no day, so no day is written and none is invented.
