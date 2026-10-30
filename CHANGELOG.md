# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `PartialDate`, an immutable value for a date known to the year, the month or the day, and
  `Precision`, which says which. A value is built from parts or read from `YYYY`, `YYYY-MM` or
  `YYYY-MM-DD`, and written back as the same text. Values sort in ISO order and are hashable,
  so they work as set members and dictionary keys. A value has a `start` and an `end`, the
  first and last day of the period it covers, and `relation_to` says whether that period is
  before, after or overlapping another, as a `Relation`.
- `PartialDateField`, a model field that stores a `PartialDate` in one ten-character text
  column in its ISO form. It takes a `PartialDate` or its ISO text and gives back a
  `PartialDate`, and stores `None` and `""` as `NULL`. It refuses any other value with
  `ValueError` on save, and with a `ValidationError` coded `invalid` in `full_clean()`. It
  finds rows by exact match on a value or its text. The database refuses malformed text
  itself, by any route. `dumpdata` writes each value as its ISO form and each empty value as
  empty, and `loaddata` reads them back, in JSON, JSON Lines and XML. Values come back unchanged,
  empty ones included, from JSON written by `django.core.serializers` and from django-reversion's
  versions, including reverting a row and recovering a deleted one.
- `year`, `month` and `day` lookups on `PartialDateField`, each taking a whole number and
  finding the rows whose recorded part equals it. A date with that part unknown is never found.
  They combine with `gt`, `gte`, `lt`, `lte`, `in`, `range` and `isnull`, and a filter on one
  year uses an index on the column. Range filters take a `PartialDate` or its ISO form as a
  bound and compare by the order of the ISO form.
- Ordering by a `PartialDateField` gives the order `sorted()` gives its values, and uses an index
  on the column. `year`, `month` and `day` work in `values`, `values_list`, `annotate`,
  `order_by` and grouping, and give whole numbers, or `None` for a part not recorded.
- A `start` transform on `PartialDateField`, giving the first day of a date's period as a
  `datetime.date`, for a date axis. It works in `values`, `values_list`, `annotate`, `order_by`,
  grouping and comparison with real dates.
- `partial_dates.forms.PartialDateField` and `partial_dates.forms.PartialDateWidget`, a form
  field and a widget of year, month and day selects for entering a partial date in a plain Django
  form. The user gives the parts they know and leaves the rest empty, and the field gives back a
  `PartialDate` at that precision, or `None`. Every select keeps an empty choice, so a required
  field still takes a year alone. A day without a month, or a month or day without a year, is
  refused with the code `incomplete`, and a date that does not exist or text no select can produce
  with `invalid`. A form opened on a stored date selects exactly the parts it records, including a
  year the select does not list, and saving it unchanged reports no change. The selects read year,
  month, day in every language, each has a name of its own for assistive technology, and nothing
  needs JavaScript, a template setting or an `INSTALLED_APPS` entry.
- `PartialDateField.formfield()` returns the form field, so a model form and the admin show the
  year, month and day selects for a partial date field with no form or widget to declare. The
  field's `blank`, `verbose_name`, `help_text`, default and `unique` carry over, and a validator on
  the model field or the form field receives the `PartialDate`. With nothing said, the year select
  lists the years from the current year down to 1900, worked out each time the form is shown, and
  `PartialDateWidget(years=...)` names others for one field. The years offered limit nothing: a
  stored year the list does not hold is added to it, and any year a `PartialDate` accepts is
  accepted.
- `PartialDate.display_form()`, the text a reader should see for a partial date, in the language
  active when it is called. A year reads as a year, a month as Django's `YEAR_MONTH_FORMAT` and a
  day as its `DATE_FORMAT`, so no month or day that nobody recorded appears. The year has four
  digits at every precision and no thousands separator. `str()` and `isoformat()` are unchanged.
- A `partial_date` template filter, loaded with `{% load partial_dates %}`, that gives the display
  form in the active language. It renders empty text for an empty value and for anything that is not
  a partial date, so `default` works after it, and its output is escaped. Django finds a tag library
  through an installed app, so a project that uses the filter adds `"partial_dates"` to
  `INSTALLED_APPS`. The app adds no model and needs no migration, and the Python route needs no
  entry.
- `partial_dates.admin.PartialDateDisplayMixin`, which an admin class or an inline names before
  `ModelAdmin`, `TabularInline` or `StackedInline` to show its partial date fields as their
  display form. A column in `list_display` keeps its heading, its sorting by the stored order and
  its link to the row, a field in `list_editable` keeps its selects, and a field in
  `readonly_fields` keeps its label, and its help text except in a tabular inline. A page a user may only view, and an inline they
  may only view, show every partial date as the display form, and a field the admin leaves out
  stays off the page. An empty value shows the admin's empty display. A field reached through a
  relation, a method and an admin with no mixin keep the ISO form. It needs no `INSTALLED_APPS`
  entry, and `django.contrib.admin` stays optional.
- An `example/` project in the repository that serves a model form, a form with no model and the
  admin on localhost, with a command that seeds sign-ins, including a view-only one, and a sample
  at each precision. Its admin and its list page show the display form, in English, German and
  Japanese. It is not part of the installed package.
- `ConvertPartialDateField`, a migration operation that converts a column written by
  django-partial-date into a `PartialDateField` in place, on PostgreSQL and SQLite. It takes the
  arguments of Django's `AlterField`, so the only edit to the migration Django generates is the
  name of the operation. Every value becomes the ISO form at the precision its seconds recorded,
  and every empty value stays empty. The operation converts a value only when it is exactly what
  django-partial-date writes. Otherwise it raises `RefusedValuesError`, naming the model, the
  field, the number of refused values and the primary key and stored value of the first 20,
  before anything has changed. Migrating backwards restores the old column and every stored value.
- `OldPartialDateField`, a field that existing migrations use in place of django-partial-date's,
  so they describe the same column and a project can uninstall that package.
- A guide to moving from django-partial-date.
- The developer guide: installation, a page on entering a partial date in a form, in a model form
  and in the admin, and a querying page that states which uncertain dates each
  filter includes, with recipes for June of any year and for adding every uncertain date to a
  range, leaving every one out, and taking in the whole of a month or year. It also covers
  ordering, counting by year, month and day, a date axis, a drilldown, and where each database
  sorts a row holding no date.
- Continuous integration runs the whole test suite on PostgreSQL 17, on Django 5.2 and 6.1,
  alongside the SQLite matrix.
- The package skeleton: packaging, continuous integration and the release flow.

### Changed

- Django is now a dependency of the package.
