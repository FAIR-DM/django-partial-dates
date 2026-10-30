# Implementation Plan: Ready-made django-filter filters and a Django REST framework field

**Branch**: `007-filter-and-api-extras` | **Date**: 2026-10-30 | **Spec**: `spec.md`

## Summary

Two new modules, `partial_dates/filters.py` and `partial_dates/rest_framework.py`, each imported by
nothing in the core. Two extras in `pyproject.toml`. Two guide pages. One filter on the example
project's list. No migration and no change to any existing module of the package.

## Technical Context

- **Language and stack**: Python 3.12+, Django 5.2 and 6.x, PostgreSQL and SQLite
- **Dependencies**: `django-filter>=26.2` and `djangorestframework>=3.18`, as extras and in the dev
  group, never required
- **Testing**: pytest. `tests/test_filters.py` and `tests/test_rest_framework.py` mirror the modules

## Constitution Check

| Article | How the plan meets it |
|---|---|
| II, III Simplicity | Each class has a present use. No base class, no registry, no setting |
| VI Documentation | Two guide pages, README and CHANGELOG, in the story that adds the name |
| VII Dependencies | Justified by G10. Extras only. `deptry` reads `optional-dependencies` |
| VIII i18n | The serializer's one new message is wrapped and added to the `en` catalog |
| X Cohesion | Behaviour lives on fields, widgets and filters |
| XII Uncertain matches | The guide states them, and tests cover each precision on both sides of a bound |
| XIII Stack | Both databases tested, with no SQL of its own |

## Design

### `partial_dates/filters.py`

```python
class PartialDateFilterWidget(PartialDateWidget): ...
class PartialDateFilterField(PartialDateField): ...  # forms.PartialDateField
class PartialDateRangeWidget(forms.MultiWidget): ...
class PartialDateRangeField(forms.MultiValueField): ...
class PartialDateFilter(django_filters.Filter): ...
class PartialDateRangeFilter(django_filters.RangeFilter): ...
```

**`PartialDateFilterWidget`** overrides `value_from_datadict`. When `data.get(name)` is not empty it
returns that text, otherwise the parent's parts. An empty `?collected=` falls through to the parts.

**`PartialDateFilterField`** takes `years=None`, keyword-only, and defaults `widget` to
`PartialDateFilterWidget(years=years)`. `clean` turns a `str` into a value with
`PartialDate.fromisoformat`, raising `ValidationError(self.error_messages["invalid"], code="invalid")`
on `ValueError`, and passes anything else to the parent.

**`PartialDateRangeWidget`** is `MultiWidget` with
`{"after": PartialDateFilterWidget(years=years), "before": PartialDateFilterWidget(years=years)}`.
`decompress` gives `[value.start, value.stop]` for a `slice` and `[None, None]` otherwise.

**`PartialDateRangeField`** holds two `PartialDateFilterField(required=False)`, with
`require_all_fields=False`, the same `years` for both. `compress` gives `None` when both are `None`,
otherwise `slice(after, before)`, which is the shape `RangeFilter` takes.

**`PartialDateFilter`**: `field_class = PartialDateFilterField`. `__init__` reads the lookup, using
django-filter's default when none is given.

- `exact`, `gt`, `gte`, `lt`, `lte`: nothing changes.
- `year`, `month`, `day`, alone or followed by `__exact`, `__gt`, `__gte`, `__lt`, `__lte`:
  `self.field_class = forms.IntegerField`.
- Anything else raises `ImproperlyConfigured`, which covers the `in` and `range` that
  `filter_for_lookup` builds and a mistaken `month__isnull`.

**`PartialDateRangeFilter`**: `field_class = PartialDateRangeField`. `filter` replaces a `stop` with
the day-precision `PartialDate` of `value.stop.end`, then calls `super().filter`. Nothing else, so
`exclude`, `distinct`, `method` and one join come from django-filter.

### `partial_dates/rest_framework.py`

```python
class PartialDateField(serializers.Field):
    default_error_messages = {"invalid": _("Enter a date as YYYY, YYYY-MM or YYYY-MM-DD.")}
```

- `to_representation(value)`: `value.isoformat()` for a `PartialDate`, otherwise
  `PartialDate.fromisoformat(value).isoformat()`.
- `to_internal_value(data)`: a `PartialDate` is returned. Anything else goes to `fromisoformat`, and
  `ValueError` becomes `self.fail("invalid")`.

### Packaging

`[project.optional-dependencies]` gains `django-filter` and `djangorestframework`. Neither module is
imported from `partial_dates/__init__.py`, `fields.py` or `forms.py`.

### Tests

- `tests/test_filters.py`: a `FilterSet` per case, over `Sample` rows from `SampleFactory`.
- US-2 runs through a page: a `FilterView` in `tests/urls.py` over `Sample`, with a test template
  rendering `filter.form` and the list, using the Django test client.
- `tests/test_rest_framework.py`: serializers over `Sample`, plus a `ListAPIView` with
  `DjangoFilterBackend`, `authentication_classes = []`, `permission_classes = []` and a JSON
  renderer, through `APIRequestFactory`, for US-1 scenario 10.
- Absence: a fresh interpreter, as `tests/test_init.py` does, with `sys.modules["rest_framework"] =
  None` or `sys.modules["django_filters"] = None` set before the import. Setting an entry to `None`
  makes importing it raise `ImportError`, so the test shows the library is not needed. Its base
  includes a check that `partial_dates.fields` and `partial_dates.forms` import with both blocked.
- A test of a guide's examples and tables goes in `tests/test_guide.py`, beside the others.

### Documentation

- `docs/developer/filtering.md`, a how-to for a `FilterSet`: installing, one date, a range, a part,
  `Meta.fields`, the table of what a range finds and the rule for when it finds nothing, how it
  differs from the `range` lookup, what a user sees, and the recipes.
- `docs/developer/rest-framework.md`: installing, declaring the field, reading and writing, refused
  input, and `ModelSerializer`.
- Both linked from `docs/developer/index.md`, `docs/index.md`, and the README, with a CHANGELOG entry
  in the story that adds the name.

### ADR

D3 graduates at convergence, with the number next free on origin/main at that moment.

## Stories and order

The foundational task is done first and directly. US-1, US-2 and US-3 follow in that order on this
branch, because US-2 tests what US-1 builds, and US-3 touches none of it.
