# Developer guide

This guide is for a developer building a Django project with `django-partial-dates`. It covers
installing the package, querying the dates it stores, entering them in a form, showing them to a
reader and moving a project
from django-partial-date.

- [Installation](installation.md): install the package and add the field to a model.
- [Querying](querying.md): filter partial dates by year, month, day or range, and find out which
  uncertain dates each filter includes.
- [Entering a partial date](forms.md): use the form field in a model form, the admin or a plain
  form, name the years it offers, and learn what the user sees and what each error means.
- [Showing a partial date](showing.md): get the text a reader sees, at the precision it was
  recorded and in the active language.
- [Moving from django-partial-date](moving-from-django-partial-date.md): convert a column
  django-partial-date wrote, point your old migrations at a stand-in field, and correct the values
  the conversion refuses.
