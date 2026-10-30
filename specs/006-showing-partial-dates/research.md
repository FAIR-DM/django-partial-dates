# Research: Showing a partial date to a reader

Read against Django 6.1.2, the version `uv.lock` installs, in `.venv`. The admin behaviour below was
also run on Django 5.2.18.

This specification has no `planning-notes.md` and no sketch.

## Formatting a date for a language

`django.utils.formats.date_format(value, format)` (`utils/formats.py:147`) passes the format through
`get_format` (`:100`). A name in `FORMAT_SETTINGS` (`:31`) resolves for the active language, and any
other string is used as it stands. So `date_format(value.start, "Y")` writes the year, with no number
localisation and so no thousands separator, and `YEAR_MONTH_FORMAT` and `DATE_FORMAT` resolve for
the language. The result is the same on Django 5.2. `Y` gives `0990` and `0001` on both versions.

`value.start` is a real date only as the input to a format that names no later part. It is never
shown as a date, and a test holds that the text does not depend on it.

## Template libraries need an installed app

`get_template_tag_modules` (`template/backends/django.py:133`) walks the `templatetags` package of
each installed app, so `{% load %}` of the package's library needs `partial_dates` in
`INSTALLED_APPS`. Listing the package as an app was run: apps load, `makemigrations --check` is
clean, and it needs no `apps.py`.

## Why the admin cannot be reached with nothing declared

`items_for_result` and `AdminReadonlyField.contents` both call `display_for_field`
(`contrib/admin/utils.py:433`), which ends in `display_for_value` (`:485`) and `str(value)` for a
field type it does not know. A field has no method to override there. The specification's decision
stands: one declaration on each admin class.

## The admin display, proved

A prototype mixin over the test app's `Record` and `Note` was run on Django 5.2.18 and 6.1.2 through
the test client, as a superuser, a user with view permission only and a user with add and view
permission. Every result below held on both. The three items the specification left untried are
marked.

| Behaviour | Result |
|---|---|
| `list_display` shows the display form | yes, and the ISO form is gone from the page |
| Heading, and the `column-` and `field-` classes | kept, by naming the callable after the field |
| Sorting (US-2 9), with `ordering` set and on a click | yes, by `admin_order_field` |
| **Row link (US-2 9)**, default and named in `list_display_links` | yes, by substituting in `get_list_display_links` too |
| **`list_editable` (US-2 14)** | yes: the column stays a name, its selects render, and the POST saves |
| **Saving through such an admin (US-2 13)** | yes: editable fields keep their selects, a save stores them, and a read-only field is untouched |
| `readonly_fields` | display form, under the field's label with its help text |
| A view-only user, on the row and in an inline | every partial date reads as the display form, with no selects |
| The add page, for a superuser and for a user who may add but not change | selects, so the view-only rule must not apply when `obj` is `None` |
| An inline row a user may add but not change | left editable, so the view-only rule on an inline also asks `has_add_permission` |
| An empty value in a list and in a read-only field | the admin's empty value display |

What the working shape depends on:

- A read-only callable has to be the same object in `get_fieldsets` and `get_readonly_fields`
  (`contrib/admin/options.py:859` excludes by equality). Each admin instance keeps one callable per
  field. Inline instances are created more than once per request, and that does no harm, because
  the form is built from one set and the page from another, and each set agrees with itself.
- `get_readonly_fields` cannot call `get_fieldsets`, because `get_fields` calls back into it. It asks
  `has_change_permission`, which needs nothing else.
- `get_fields` gets the field's name from `form.base_fields` and the callable from
  `get_readonly_fields`, so `get_fields` has to substitute and drop the repeat. A field read-only by
  declaration then keeps its place in the form.
- On a view-only page Django treats every name in the fieldsets as read-only
  (`options.py:2178`), but the form is built first, so the callables must be in
  `get_readonly_fields` as well. Only fields Django would show are added: an `editable=False` field
  or one in `exclude` stays out.
- A callable that returns `None` prints `None` in a read-only field, because
  `AdminReadonlyField.contents` skips `display_for_value` for callables. It returns
  `get_empty_value_display()` instead.
- `_coerce_field_name` (`templatetags/admin_list.py:191`) and `AdminReadonlyField.__init__`
  (`helpers.py:209`) both read the callable's `__name__`, which is what keeps the classes and the
  help text.
- `field_name in cl.list_display_links` (`admin_list.py:213`) compares what is in `list_display`, so
  a link named in `list_display_links` is substituted with it.

Every hook used is documented API except `__name__`, `admin_order_field` and `short_description`,
which `@admin.display` sets. Those are documented too.

## What already exists

```
display form of a value          · 7, new · searched partial_dates/, django.utils.formats.date_format does the formatting
template filter                  · 7, new · searched partial_dates/; Django's date filter refuses a PartialDate, 12 lines around display_form
tag library registration         · 4, Django · django.template.Library
admin display on an admin class  · 7, new · searched partial_dates/, the lock file and django.contrib.admin; no hook exists
empty value in the admin         · 4, Django · BaseModelAdmin.get_empty_value_display
column heading, sort, classes    · 4, Django · admin.display and a callable's __name__
format override                  · 4, Django · FORMAT_MODULE_PATH, nothing to write
month names                      · 4, Django · its own translations, nothing to write
```
