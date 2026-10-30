# Developer guide

This guide is for a developer building a Django project with `django-partial-dates`. It covers
installing the package, querying the dates it stores, entering them in a form, filtering them with
django-filter, exposing them through Django REST framework and moving a project
from django-partial-date.

- [Installation](installation.md): install the package and add the field to a model.
- [Querying](querying.md): filter partial dates by year, month, day or range, and find out which
  uncertain dates each filter includes.
- [Entering a partial date](forms.md): use the form field in a model form, the admin or a plain
  form, name the years it offers, and learn what the user sees and what each error means.
- [Filtering with django-filter](filtering.md): add a partial date filter and a range filter to
  a `FilterSet`, filter on a year, month or day, and learn which uncertain dates each includes.
- [Django REST framework](rest-framework.md): declare a serializer field that reads and writes
  the ISO form, and learn what a client gets for an entry that is not a partial date.
- [Moving from django-partial-date](moving-from-django-partial-date.md): convert a column
  django-partial-date wrote, point your old migrations at a stand-in field, and correct the values
  the conversion refuses.
