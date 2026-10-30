# Implementation Plan: Showing a partial date to a reader

**Branch**: `006-showing-partial-dates` | **Date**: 2026-10-30 | **Spec**: `spec.md`

## Summary

One method on `PartialDate` gives the display form. A template filter and an admin mixin are thin
layers over it. A developer guide page, the example project and the term in `CONTEXT.md` carry the
rest.

## Technical Context

- **Language and stack**: Python 3.12+, Django 5.2 and 6.x
- **Dependencies**: none added
- **Testing**: pytest with pytest-django, on SQLite and PostgreSQL

## Constitution Check

| Article | How the plan meets it |
|---|---|
| I Testing | Every scenario has a test. Expected text comes from literal values or from a date that differs in the unrecorded parts, never from the code under test |
| II, III Simplicity | One method, one filter, one mixin. No format argument, no setting, no base class |
| V Security | The filter's output is not marked safe, and the admin callable returns plain text |
| VI Documentation | A guide page, README, CHANGELOG and the installation page, each in the story that changes them |
| VII Dependencies | None added |
| VIII i18n | The package adds no message. Month names and formats are Django's |
| X Cohesion | The behaviour is a method on the value and methods on the mixin |
| XI Storage | Nothing stored changes. The display form is derived when shown |
| XIII Stack | Both Django lines run the admin behaviour |

## Design

### `partial_dates/partial_date.py`

```python
def display_form(self) -> str:
    """Return the date as the active language writes it, at its own precision."""
```

It maps `self.precision` to `"Y"`, `"YEAR_MONTH_FORMAT"` or `"DATE_FORMAT"` and returns
`date_format(self.start, format)`. `django.utils.formats` is imported at the top of the module:
the package already imports Django at its root.

`__str__` and `isoformat()` do not change.

### `partial_dates/templatetags/partial_dates.py`

`templatetags/__init__.py` plus one module holding `register = template.Library()` and the filter
`partial_date`. It returns `value.display_form()` for a `PartialDate` and `""` for anything else.
A developer writes `{% load partial_dates %}` and `{{ sample.collected|partial_date }}`.

### `partial_dates/admin.py`

One class, `PartialDateDisplayMixin`, placed before `ModelAdmin` or an inline in the bases. The
module is not imported by the package root, so `django.contrib.admin` stays optional, and it needs
no `INSTALLED_APPS` entry.

The behaviour, with the reasons in `research.md`, "The admin display, proved":

- **The display of one field** is a callable named after the field, with `short_description` from
  its `verbose_name` and `admin_order_field` from its name. It returns the display form, or
  `get_empty_value_display()` for an empty value. The admin instance keeps one per field.
- **Which fields are read-only for this request**: those in the admin's own `readonly_fields`, or
  every partial date field when the whole object is read-only.
- **The whole object is read-only** when `obj` is not `None`, the user may not change it, and, on an
  inline, may not add to it either.
- **Substitution** replaces those names with the callables, including inside a nested `fields`
  tuple, and leaves everything else alone.
- `get_readonly_fields` returns the substituted list, plus the callables of partial date fields
  Django would show on a read-only page: editable and not in `get_exclude`.
- `get_fields` substitutes and drops the repeat. `get_fieldsets` substitutes in place, for declared
  `fieldsets`.
- `get_list_display` and `get_list_display_links` substitute the model's partial date fields,
  except those in `list_editable`.

Partial date fields are read from `self.opts.concrete_fields`, so a name with `__` is never
touched, which is the edge case the specification states.

### Documentation and example

- `docs/developer/showing.md`, new: the display form at each precision, the filter and the app
  entry, the Python route, the admin mixin, what it does not cover, and changing a language's
  format. Linked from `docs/developer/index.md` and `docs/index.md`. Examples run in
  `tests/test_guide.py`, as the other guides do.
- `docs/developer/installation.md`: the app entry is needed only for the template filter.
- `CONTEXT.md`: **display form**. `README.md`, `CHANGELOG.md`, and R6 in `docs/ROADMAP.md`.
- `example/`: `partial_dates` in `INSTALLED_APPS`, `LocaleMiddleware` and a few `LANGUAGES`, the
  filter on the list page, the mixin on `SampleAdmin` and `NoteInline`, `list_display` and a
  read-only field, and a view-only sign-in in `seed`.

## Test Design

- `tests/test_partial_date.py`, class `TestDisplayForm`: literal text in `en`, `de` and `ja` at each
  precision. Language by `translation.override`.
- "Names no part that was not recorded" (SC-001) is tested for every language in
  `settings.LANGUAGES`: the display form of `1990` must equal `date_format` of 31 December 1990 and
  of 1 January 1990 with the same format. The text of `1990-06` must equal it for 1 June and 30 June.
  Text that changed with the unrecorded part would fail.
- `tests/test_templatetags/test_partial_dates.py`, class `TestPartialDateFilter`.
- `tests/test_admin.py`, new classes, using an admin registered with the mixin. `tests/admin.py`
  stays as it is, and a new `Record` proxy model `DisplayedRecord` with its own admin keeps the
  existing tests' admin unchanged. Its `readonly_fields`, `list_display` and `list_editable` are set
  on a test-only `ModelAdmin`, reached by URL through `tests/urls.py`'s `admin.site`.
- Permissions: a view-only user and an add-and-view user, built with `Permission` as
  `tests/test_admin.py` already does.
- `tests/settings.py` gains `"partial_dates"`. Scenario 17 removes it with `modify_settings`.

## Project Structure

```text
partial_dates/partial_date.py                 display_form
partial_dates/templatetags/__init__.py        new
partial_dates/templatetags/partial_dates.py   new
partial_dates/admin.py                        new
docs/developer/showing.md                     new
tests/test_templatetags/                      new
tests/test_partial_date.py, test_admin.py, test_guide.py, admin.py, models.py, settings.py
example/project/settings.py, example/samples/admin.py, seed.py, sample_list.html
CONTEXT.md, README.md, CHANGELOG.md, docs/developer/index.md, docs/developer/installation.md,
docs/index.md, docs/ROADMAP.md
```
