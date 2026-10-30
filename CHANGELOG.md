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
- The developer guide: installation, and a querying page that states which uncertain dates each
  filter includes, with recipes for June of any year and for adding every uncertain date to a
  range, leaving every one out, and taking in the whole of a month or year.
- Continuous integration runs the whole test suite on PostgreSQL 17, on Django 5.2 and 6.1,
  alongside the SQLite matrix.
- The package skeleton: packaging, continuous integration and the release flow.

### Changed

- Django is now a dependency of the package.
