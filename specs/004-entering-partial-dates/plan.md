# Implementation Plan: Entering and editing a partial date

**Branch**: `004-entering-partial-dates` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: `specs/004-entering-partial-dates/spec.md`, `research.md`

## Summary

One new module, `partial_dates/forms.py`, holding a `MultiWidget` of three selects and a
`MultiValueField` that gives back a `PartialDate`. The model field's `formfield()` returns it, and
the admin then needs nothing. A small `example/` project serves the form and the admin. A new guide
page documents both.

## Technical context

- **Language**: Python 3.12 and later. Django 5.2 LTS, 6.0 and 6.1
- **Dependencies**: none new. `django.contrib.admin`, `auth`, `sessions` and `messages` join the
  test settings and `example/` only
- **Testing**: pytest-django, against SQLite by default and PostgreSQL with
  `TEST_DATABASE=postgresql`
- **Constraints**: nothing stored changes and no migration ships in the package (Article XI). The
  package stays free of `INSTALLED_APPS`, templates and static files (FR-018)

## Constitution check

| Article | How the plan meets it |
|---|---|
| I Testing | Test-first per task. Errors asserted by field and code. No test asserts wording or layout |
| II Simplicity | Two classes on Django's own multi-part field and widget. No JavaScript |
| III Anti-abstraction | No base class of ours. No new argument on either field |
| IV Integration-first | Scenarios go through real forms, a model form and the admin's views |
| V Security | Everything is rendered by Django's templates, so a posted value is escaped. Nothing is built by hand |
| VI Documentation | Guide page, README, CHANGELOG. Guide examples are run by a test |
| VII Dependencies | None added |
| VIII i18n | Every message and select name uses `gettext_lazy`, and the `en` catalog is updated |
| IX Data model | No model ships in the package |
| X Cohesion | Two classes, as Django shapes a field and a widget |
| XI Storage | Untouched |
| XII Filters | No filter added |
| XIII Compatibility | Once the stories are done, the suite runs locally on Django 5.2, 6.0 and 6.1 on SQLite, and on 6.1 on PostgreSQL |

No violations.

## Design

### `partial_dates/forms.py`

```python
class PartialDateWidget(forms.MultiWidget):
    def __init__(self, attrs=None, years=None): ...
    def decompress(self, value): ...
    def get_context(self, name, value, attrs): ...


class PartialDateField(forms.MultiValueField):
    widget = PartialDateWidget
    default_error_messages = {"incomplete": ..., "invalid": ...}

    def __init__(self, **kwargs): ...
    def compress(self, data_list): ...
```

- `PartialDateWidget.__init__` builds `{"year": Select, "month": Select, "day": Select}`. Each select
  has an `aria-label` naming its part, and an empty choice labelled the same. Months come from
  `MONTHS`, days are 1 to 31. `years` is kept on the instance as a tuple, or `None`.
- `decompress` takes `None`, `""`, a `PartialDate` or an ISO form and returns `[year, month, day]`,
  with `None` for an unknown part. Text that is not an ISO form gives three `None`s, because a posted
  hidden initial reaches it, and a hand-edited one must not raise.
- `get_context` decomposes the value when it is not already a list, works out the year list from
  `self.years`, or from today's year down to 1900, and reads the value's year as a whole number,
  because a refused entry holds posted text. It adds that year when it lies in 1 to 9999 and is not
  among them, so nothing is listed twice and a year no date can have is never offered. It then sets
  `self.widgets[0].choices` and calls `super()`.
- `PartialDateField.__init__` passes three `forms.IntegerField(required=False)` and
  `require_all_fields=False` to `super()`.
- `compress` returns `None` for an empty list. It raises `ValidationError(code="incomplete")` when
  the year `is None`, or the month `is None` and the day is not, so that year `0` reaches `PartialDate`
  and gives `invalid`. It returns `PartialDate(year, month, day)`, turning `ValueError` into
  `ValidationError(code="invalid")`.

The module uses Django's naming, `partial_dates.forms.PartialDateField` beside
`partial_dates.fields.PartialDateField`, as `forms.DateField` sits beside `models.DateField`. The
package root's `PartialDateField` stays the model field.

### `partial_dates/fields.py`

```python
def formfield(self, **kwargs):
    return super().formfield(**{"form_class": forms.PartialDateField, **kwargs})
```

### Test app

- `tests/settings.py` gains `django.contrib.admin`, `auth`, `sessions`, `messages`, `MIDDLEWARE`,
  `TEMPLATES` and `ROOT_URLCONF = "tests.urls"`. `partial_dates` stays out of `INSTALLED_APPS`.
- `tests/models.py` gains `Note`, with a foreign key to `Record` for the inline, `drafted` defaulting to `PartialDate(1990, 6)` and `reviewed` defaulting to a callable, each
  with `verbose_name` and `help_text`. `NoteFactory`, a `note` fixture and a class in
  `tests/test_factories.py` go with it. `tests/migrations/0003_note.py` is made with
  `makemigrations tests`.
- `tests/admin.py` registers `Record` with a `Note` inline, and `Event`. `tests/urls.py` serves the
  admin.
- `tests/test_forms.py` mirrors the new module. `tests/test_admin.py`, `tests/admin.py` and
  `tests/urls.py` join `non-mirror-paths` in `pyproject.toml`, because the package has no admin
  module.

### `example/`

As D11. `example/manage.py`, `example/project/` for settings and URLs, and `example/samples/` holding
one app:

- `Sample`, with `collected` required, `published` optional and `catalogued` defaulting to `1990`.
  `Note`, with a foreign key and an optional `written`, for the inline.
- `admin.py`, a `ModelForm` with `CreateView` and `UpdateView`, a list page, and a page with a plain
  form that shows what it cleaned.
- `management/commands/seed.py`, idempotent, creating `regular.user`, `staff.user` and `super.user`
  with the email addresses `<name>@example.com` and the password `password`, and a sample at each
  precision, one in 1850 and one in 0990.

`.gitignore` already covers its database. `pyproject.toml` adds `example/` to deptry's `extend_exclude`, and a
ruff per-file ignore for its placeholder secret and seeded passwords.

### Documentation

- `docs/developer/forms.md`, new: use the field in a model form and the admin, declare it on a plain
  form, name the years, add a limit with a validator, what each error code means, and how to
  translate the messages. The example project is shown running on localhost, and its seeded sign-ins
  are stated to be for local use. Its `>>>` examples run in `tests/test_guide.py`.
- `docs/developer/index.md`, `docs/index.md`, `README.md` (status, usage, scope), `CHANGELOG.md`,
  and R4's line in `docs/ROADMAP.md`.
- `specs/002-model-field/spec.md`: the assumption about a form showing plain text is rewritten to
  read as current (D13).

## Risks

- `tests/migrations/0003_note.py` and the shared documents may collide with work merging in parallel.
  The branch is brought up to date before review, and the test migration is renumbered if needed.
- `MultiValueField`'s internals are stable across the supported range, but the suite is run on each
  Django version to confirm it.
