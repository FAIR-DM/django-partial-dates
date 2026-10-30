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
  empty, and `loaddata` reads them back, in JSON, JSON Lines and XML.
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
- The developer guide: installation, a page on entering a partial date in a form, and a querying page that states which uncertain dates each
  filter includes, with recipes for June of any year and for adding every uncertain date to a
  range, leaving every one out, and taking in the whole of a month or year. It also covers
  ordering, counting by year, month and day, a date axis, a drilldown, and where each database
  sorts a row holding no date.
- Continuous integration runs the whole test suite on PostgreSQL 17, on Django 5.2 and 6.1,
  alongside the SQLite matrix.
- The package skeleton: packaging, continuous integration and the release flow.

### Changed

- Django is now a dependency of the package.
