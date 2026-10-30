# Developer guide

This guide is for a developer building a Django project with `django-partial-dates`. It covers
installing the package, querying the dates it stores and moving a project from
django-partial-date.

- [Installation](installation.md): install the package and add the field to a model.
- [Querying](querying.md): filter partial dates by year, month, day or range, and find out which
  uncertain dates each filter includes.
- [Moving from django-partial-date](moving-from-django-partial-date.md): convert a column
  django-partial-date wrote, point your old migrations at a stand-in field, and correct the values
  the conversion refuses.
