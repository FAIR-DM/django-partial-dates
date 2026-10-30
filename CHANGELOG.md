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
- The developer guide: installation, and a querying page that states which uncertain dates each
  filter includes, with recipes for June of any year and for adding every uncertain date to a
  range, leaving every one out, and taking in the whole of a month or year. It also covers
  ordering, counting by year, month and day, a date axis, a drilldown, and where each database
  sorts a row holding no date.
- Continuous integration runs the whole test suite on PostgreSQL 17, on Django 5.2 and 6.1,
  alongside the SQLite matrix.
- The package skeleton: packaging, continuous integration and the release flow.

### Changed

- Django is now a dependency of the package.
