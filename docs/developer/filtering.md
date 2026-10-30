# Filtering with django-filter

You filter a list of records by a partial date with `PartialDateFilter` and
`PartialDateRangeFilter`, two filters for a django-filter `FilterSet`. They validate what a
person or an API client sends, show the year, month and day selects of the
[form field](forms.md), and read the ISO form from a query string. A partial date is uncertain,
so a filter can meet a date that might or might not be what was asked for. This page says which
dates each filter includes, so you can check a filter before you rely on it, and it shows how
to ask for another rule.

The filters live in `partial_dates.filters`, and the core package never imports django-filter.

## Set up the examples

The examples use this model, the one from the [querying guide](querying.md).

```python title="models.py"
from django.db import models

from partial_dates import PartialDateField


class Sample(models.Model):
    collected = PartialDateField(null=True, blank=True, db_index=True)
```

They run against these rows, one sample for each value, and one sample holding no date.

```python
for text in [
    "1990", "1990-05", "1990-05-31", "1990-06", "1990-06-01", "1990-06-14",
    "1990-07", "1990-12", "1991", "1991-03", "1991-03-15", "1991-03-31",
    "1991-04", "1991-06", "1991-06-02", None,
]:
    Sample.objects.create(collected=text)
```

Every result below is shown as the dates in it, in order, by `apply`, which runs a filter set
over every sample. It names `nulls_last`, so the sample holding no date comes last on both
PostgreSQL and SQLite.

```python
>>> import django_filters
>>> from django.db.models import F, Q
>>> from partial_dates import PartialDate, PartialDateField
>>> from partial_dates.filters import PartialDateFilter, PartialDateRangeFilter
>>> def show(queryset):
...     ordered = queryset.order_by(F("collected").asc(nulls_last=True))
...     return [
...         None if sample.collected is None else str(sample.collected)
...         for sample in ordered
...     ]
>>> def apply(filterset_class, data):
...     return show(filterset_class(data, queryset=Sample.objects.all()).qs)
```

## Install the extra

Install the package with the `django-filter` extra, in the environment your project runs in.

```console
$ pip install "django-partial-dates[django-filter]"
```

The extra adds django-filter and nothing else. Your project needs no entry in
`INSTALLED_APPS` for these filters. Installing it does not install Django REST framework, and
the filters never import it.

## Filter on one date

Declare `PartialDateFilter` on a `FilterSet` with the name of the field and a lookup. The
lookup is `exact` when you give none, or `gt`, `gte`, `lt` or `lte`. The entry is a partial
date, and the filter finds the rows the lookup of the same name finds.

```python
>>> class SampleFilter(django_filters.FilterSet):
...     collected = PartialDateFilter(lookup_expr="gte")
...
...     class Meta:
...         model = Sample
...         fields = []
>>> apply(SampleFilter, {"collected": "1991-03-15"})
['1991-03-15', '1991-03-31', '1991-04', '1991-06', '1991-06-02']
```

A row is compared by the order of its ISO form, so a bound is a position and not a period. A
date whose period contains the bound sorts before it. For a bound of `1990-06`, `1990` is the
uncertain match: `gt` and `gte` leave it out, and `lt` and `lte` include it. `exact` finds
only the rows equal to the bound, so a bound of `1990` does not find `1990-06`.

| Bound | Row | `exact` | `gt` | `gte` | `lt` | `lte` |
|---|---|---|---|---|---|---|
| `1990-06` | `1990` | no | no | no | yes | yes |
| `1990-06` | `1990-05` | no | no | no | yes | yes |
| `1990-06` | `1990-05-31` | no | no | no | yes | yes |
| `1990-06` | `1990-06` | yes | no | yes | no | yes |
| `1990-06` | `1990-06-01` | no | yes | yes | no | no |
| `1990-06` | `1990-06-14` | no | yes | yes | no | no |
| `1990-06` | `1990-07` | no | yes | yes | no | no |
| `1990-06` | `1991` | no | yes | yes | no | no |

The same rule holds at the other two precisions of bound.

| Bound | Row | `exact` | `gte` | `lte` |
|---|---|---|---|---|
| `1990` | `1990` | yes | yes | yes |
| `1990` | `1990-06` | no | yes | no |
| `1990` | `1990-06-14` | no | yes | no |
| `1990-06-14` | `1990` | no | no | yes |
| `1990-06-14` | `1990-06` | no | no | yes |
| `1990-06-14` | `1990-06-14` | yes | yes | yes |
| `1990-06-14` | `1990-07` | no | yes | no |

A row holding no date is never found when an entry is given, and `exclude=True` returns it.
With no entry the filter does not narrow the list, so the row is kept.

## Filter on a range

Declare `PartialDateRangeFilter` for a pair of bounds. It reads two query parameters, named
after the filter: `collected_after` and `collected_before`. Each is optional, and a bound
given alone applies alone.

```python
>>> class RangeFilter(django_filters.FilterSet):
...     collected = PartialDateRangeFilter()
...
...     class Meta:
...         model = Sample
...         fields = []
>>> apply(RangeFilter, {"collected_after": "1990-06", "collected_before": "1991-03"})
['1990-06', '1990-06-01', '1990-06-14', '1990-07', '1990-12', '1991', '1991-03',
 '1991-03-15', '1991-03-31']
>>> apply(RangeFilter, {"collected_before": "1990-06"})
['1990', '1990-05', '1990-05-31', '1990-06', '1990-06-01', '1990-06-14']
```

A row is found when it sorts at or after the first bound and at or before the last day of the
period of the second. So the second bound takes in the whole of the month or year it names.
For `1990-06` to `1991-03`:

| After | Before | Row | Found |
|---|---|---|---|
| `1990-06` | `1991-03` | `1990` | no |
| `1990-06` | `1991-03` | `1990-05-31` | no |
| `1990-06` | `1991-03` | `1990-06` | yes |
| `1990-06` | `1991-03` | `1990-06-14` | yes |
| `1990-06` | `1991-03` | `1991` | yes |
| `1990-06` | `1991-03` | `1991-03` | yes |
| `1990-06` | `1991-03` | `1991-03-15` | yes |
| `1990-06` | `1991-03` | `1991-03-31` | yes |
| `1990-06` | `1991-03` | `1991-04` | no |
| `1990-06` | `1991-03` | no date | no |

The uncertain matches follow the order of the ISO form, as they do for `gte`. `1990` sorts
before the first bound and is left out. `1991` sorts inside the range and is found, though
all of its days might fall after March. Bounds of the other precisions give the same rule.

| After | Before | Row | Found |
|---|---|---|---|
| `1990` | `1990` | `1990` | yes |
| `1990` | `1990` | `1990-06` | yes |
| `1990` | `1990` | `1990-12` | yes |
| `1990` | `1990` | `1991` | no |
| `1990-06-14` | `1990-06-14` | `1990` | no |
| `1990-06-14` | `1990-06-14` | `1990-06` | no |
| `1990-06-14` | `1990-06-14` | `1990-06-01` | no |
| `1990-06-14` | `1990-06-14` | `1990-06-14` | yes |
| `1990-06-14` | `1990-06-14` | `1990-07` | no |
| `1990-06-14` | `1991` | `1990-07` | yes |
| `1990-06-14` | `1991` | `1991-06-02` | yes |
| `1990-06-14` | `1991` | `1991-06` | yes |
| `-` | `1991-03` | `1990` | yes |
| `-` | `1991-03` | `1991-03-31` | yes |
| `-` | `1991-03` | `1991-04` | no |
| `1991-03` | `-` | `1990-12` | no |
| `1991-03` | `-` | `1991-03` | yes |
| `1991-03` | `-` | `1991-04` | yes |

A dash means the bound is not given.

### Know when a range finds nothing

A range finds nothing, and reports no error, only when its first bound sorts after the last
day of the period of its second bound. Anything else finds the rows from the first bound to
that last day.

| After | Before | Row | Found |
|---|---|---|---|
| `1991-04` | `1991-03` | `1991-03-31` | no |
| `1991-04` | `1991-03` | `1991-04` | no |
| `1991-03-31` | `1991-03` | `1991-03-15` | no |
| `1991-03-31` | `1991-03` | `1991-03-31` | yes |
| `1991-03-15` | `1991-03` | `1991-03` | no |
| `1991-03-15` | `1991-03` | `1991-03-15` | yes |
| `1991-03-15` | `1991-03` | `1991-03-31` | yes |
| `1991-03-15` | `1991-03` | `1991-04` | no |
| `1991-06` | `1991` | `1991` | no |
| `1991-06` | `1991` | `1991-06` | yes |
| `1991-06` | `1991` | `1991-06-02` | yes |
| `1991-06` | `1991` | `1991-04` | no |

### Compare the filter with the range lookup

The `range` lookup of the [querying guide](querying.md#filter-by-a-range) treats its second
bound as a position, and finds nothing whenever the first bound sorts after the second. The
range filter takes in the whole of the period the second bound names, and finds nothing only
after the last day of that period. So `1991-03-15` to `1991-03` finds nothing with the lookup
and the rest of March with the filter. A filter declared with `PartialDateFilter` and
`lookup_expr="lte"` is the plain lookup and keeps its position.

```python
>>> show(Sample.objects.filter(collected__range=("1991-03-15", "1991-03")))
[]
>>> apply(RangeFilter, {"collected_after": "1991-03-15", "collected_before": "1991-03"})
['1991-03-15', '1991-03-31']
```

## Filter on a year, month or day

Give `PartialDateFilter` the lookup `year`, `month` or `day`, alone or followed by `exact`,
`gt`, `gte`, `lt` or `lte`. The entry is a whole number, and the filter finds the rows whose
recorded part satisfies it. A date whose part is unknown is never found, so `month=6` leaves
out `1990`. A number no date can hold, such as `0` or `13` for a month, finds nothing and
raises nothing.

```python
>>> class MonthFilter(django_filters.FilterSet):
...     month = PartialDateFilter(field_name="collected", lookup_expr="month")
...     from_month = PartialDateFilter(field_name="collected", lookup_expr="month__gte")
...
...     class Meta:
...         model = Sample
...         fields = []
>>> apply(MonthFilter, {"month": "6"})
['1990-06', '1990-06-01', '1990-06-14', '1991-06', '1991-06-02']
>>> apply(MonthFilter, {"from_month": "12"})
['1990-12']
```

| Lookup | Entry | Row | Found |
|---|---|---|---|
| `year` | `1990` | `1990` | yes |
| `year` | `1990` | `1990-06` | yes |
| `year` | `1990` | `1991` | no |
| `month` | `6` | `1990` | no |
| `month` | `6` | `1990-06` | yes |
| `month` | `6` | `1990-06-14` | yes |
| `month` | `6` | `1990-07` | no |
| `day` | `14` | `1990-06` | no |
| `day` | `14` | `1990-06-01` | no |
| `day` | `14` | `1990-06-14` | yes |
| `month__gte` | `6` | `1990-05` | no |
| `month__gte` | `6` | `1990-06` | yes |
| `month__gte` | `6` | `1990-12` | yes |
| `month__gte` | `6` | `1990` | no |

An entry that is not a whole number, such as `1990.5` or `June`, is reported as an error on
the filter. Any other lookup raises `ImproperlyConfigured` when the filter is created.

## Name the field in Meta.fields

django-filter cannot map a `PartialDateField` to a filter, and refuses a `Meta.fields` that
names one. Map it to `PartialDateFilter` with `Meta.filter_overrides`, and `Meta.fields` can
name `exact`, `gt`, `gte`, `lt`, `lte`, `year`, `month`, `day` and `isnull`.

```python
>>> class GeneratedFilter(django_filters.FilterSet):
...     class Meta:
...         model = Sample
...         fields = {"collected": ["exact", "gte", "month", "isnull"]}
...         filter_overrides = {
...             PartialDateField: {"filter_class": PartialDateFilter}
...         }
>>> {name: type(f).__name__ for name, f in GeneratedFilter.base_filters.items()}
{'collected': 'PartialDateFilter', 'collected__gte': 'PartialDateFilter',
 'collected__month': 'NumberFilter', 'collected__isnull': 'BooleanFilter'}
```

Two things differ from a filter you declare:

- `year`, `month` and `day` become django-filter's own `NumberFilter`, which accepts a decimal
  and rounds it down. `collected__month=6.5` finds June. Declare a `PartialDateFilter` with
  the lookup, as above, to refuse a decimal.
- `range` and `in` cannot be named. Naming either raises `ImproperlyConfigured` when the
  class is defined. Declare a `PartialDateRangeFilter` for a range, and see
  [Filter on a list of dates](#filter-on-a-list-of-dates) for `in`.

```python
>>> apply(GeneratedFilter, {"collected__month": "6.5"})
['1990-06', '1990-06-01', '1990-06-14', '1991-06', '1991-06-02']
>>> class Refused(django_filters.FilterSet):
...     class Meta:
...         model = Sample
...         fields = {"collected": ["range"]}
...         filter_overrides = {
...             PartialDateField: {"filter_class": PartialDateFilter}
...         }
Traceback (most recent call last):
    ...
ImproperlyConfigured: PartialDateFilter does not support the lookup 'range'.
```

## Filter across a relation

Name the field through the relation with `field_name`. When one record holds many dates, the
range filter applies both bounds to the same date, so a record with one date before the range
and another after it is not found, and a record with one date inside is.

The examples use a `Record` that has many `Note` rows, each with a `drafted` date.

```python title="models.py"
class Record(models.Model):
    pass


class Note(models.Model):
    record = models.ForeignKey(Record, on_delete=models.CASCADE)
    drafted = PartialDateField()
```

```python
>>> straddling = Record.objects.create()
>>> inside = Record.objects.create()
>>> for record, drafted in [
...     (straddling, "1989"), (straddling, "1992"), (inside, "1990-09"),
...     (inside, "1991-01"),
... ]:
...     _ = Note.objects.create(record=record, drafted=drafted)
>>> class RecordFilter(django_filters.FilterSet):
...     drafted = PartialDateRangeFilter(field_name="note__drafted", distinct=True)
...
...     class Meta:
...         model = Record
...         fields = []
>>> data = {"drafted_after": "1990", "drafted_before": "1991"}
>>> [record.pk for record in RecordFilter(data, queryset=Record.objects.all()).qs] == [
...     inside.pk
... ]
True
```

`distinct=True` returns a record once, however many of its dates are inside the range. Without
it a record appears once for each. `exclude=True` returns the records with no date inside the
range, as it does on any django-filter filter.

For a model whose related `dates` each hold a `value`, which is the shape a project with a
table of dates uses, the declaration is the same with another path.

```python title="filters.py"
class DatedFilter(django_filters.FilterSet):
    value = PartialDateRangeFilter(field_name="dates__value", distinct=True)
```

## Offer other years

Both filters show a year select that lists the years from the current year down to 1900. Name
the years to offer with `years`, and a range offers them for both bounds.

```python
>>> class RecentFilter(django_filters.FilterSet):
...     collected = PartialDateRangeFilter(years=range(2000, 1989, -1))
...
...     class Meta:
...         model = Sample
...         fields = []
```

The years limit nothing. A date outside the list is still accepted when it is sent as text or
as parts.

## Read what a person sends

A filter shows the year, month and day selects of the form field, named after the filter:
`collected_year`, `collected_month` and `collected_day`. A range shows one set for each bound,
named `collected_after_year` and so on. A person gives as much of a date as they know and
leaves the rest empty.

An API client has no selects to fill in, so the filter also reads the ISO form under its own
name: `?collected=1990-06` for a date, or `?collected_after=1990-06&collected_before=1991-03`
for a range. When both arrive, the ISO form is used. An empty `?collected=` is no entry.

An entry that is not a partial date is an error on that filter, with the codes of the form
field. It is never taken for no entry and never reaches the database. Text such as `1990-6`,
`1990-02-30`, `" 1990"`, digits outside ASCII and text longer than any ISO form gets `invalid`,
and a day without a month gets `incomplete`.

```python
>>> applied = SampleFilter({"collected": "1990-6"}, queryset=Sample.objects.all())
>>> applied.is_valid()
False
>>> applied.form.errors.as_data()["collected"][0].code
'invalid'
>>> applied = SampleFilter({"collected_year": "1990", "collected_day": "5"})
>>> applied.form.errors.as_data()["collected"][0].code
'incomplete'
```

A filter set drops an invalid filter and returns the rest when you read `qs`, so check
`is_valid()` first, or use a view that does. django-filter's view and Django REST framework's
filter backend both report the error to the client.

## Use the form field on its own

Each filter builds its form field from the class in its `field_class`, and you can use that
class in a form of your own. `PartialDateFilterField` is the field of `PartialDateFilter`. It
is the [form field](forms.md) that also reads ISO text, and `PartialDateFilterWidget` is its
widget, which reads the text under the field's name before it reads the three selects.
`PartialDateRangeField` is the field of `PartialDateRangeFilter`. It holds two of those fields
and gives a `slice` of the two dates, or `None` when neither is given, and
`PartialDateRangeWidget` is its widget, which names its parts `<name>_after` and `<name>_before`.
Each takes `years`, as the filters do.

## Find precision with isnull

No filter selects by the precision of a date. Ask for the rows whose month is not recorded
with django-filter's own `BooleanFilter` on `month__isnull`, as the
[querying guide](querying.md) does.

```python
>>> class PrecisionFilter(django_filters.FilterSet):
...     year_only = django_filters.BooleanFilter(
...         field_name="collected__month", lookup_expr="isnull"
...     )
...
...     class Meta:
...         model = Sample
...         fields = []
>>> apply(PrecisionFilter, {"year_only": "true"})
['1990', '1991', None]
```

## Filter by another rule

Every comparison follows the order of the ISO form. When you need another rule, use
django-filter's `method`, which hands you the validated entry as a `PartialDate`, and write
the rule with the recipes of the [querying guide](querying.md). This one adds the dates that
enclose the first bound, which `gte` leaves out.

```python
>>> class UncertainFilter(django_filters.FilterSet):
...     since = PartialDateFilter(method="from_or_enclosing")
...
...     class Meta:
...         model = Sample
...         fields = []
...
...     def from_or_enclosing(self, queryset, name, value):
...         periods = [PartialDate(value.year)] if value.month else []
...         if value.day:
...             periods.append(PartialDate(value.year, value.month))
...         return queryset.filter(Q(collected__gte=value) | Q(collected__in=periods))
>>> apply(UncertainFilter, {"since": "1991-06-02"})
['1991', '1991-06', '1991-06-02']
```

### Filter on a list of dates

There is no ready-made `in` filter. Declare one with a field that validates each item with
`PartialDate.fromisoformat`, so a bad value is an error on the filter and never reaches the
database.

```python
>>> from django import forms
>>> from django.core.exceptions import ValidationError
>>> class PartialDateListField(forms.CharField):
...     def clean(self, value):
...         text = super().clean(value)
...         try:
...             return [PartialDate.fromisoformat(item) for item in text.split(",") if item]
...         except ValueError:
...             raise ValidationError("Enter dates as YYYY, YYYY-MM or YYYY-MM-DD.", code="invalid") from None
>>> class PartialDateInFilter(django_filters.Filter):
...     field_class = PartialDateListField
...
...     def filter(self, qs, value):
...         return qs.filter(**{f"{self.field_name}__in": value}) if value else qs
>>> class InFilter(django_filters.FilterSet):
...     collected = PartialDateInFilter()
...
...     class Meta:
...         model = Sample
...         fields = []
>>> apply(InFilter, {"collected": "1990,1990-06"})
['1990', '1990-06']
>>> InFilter({"collected": "1990,1990-6"}).form.errors.as_data()["collected"][0].code
'invalid'
```

## Why a range takes in the whole of its last period

A person asking for a range up to March means all of March. The `range` lookup takes a
position instead, so a range up to `1991-03` leaves out `1991-03-15`, which sorts after it.
The range filter compares the second bound with the last day of the period it names. That
gives one rule that a table can show and that an index on the column still serves.

## Why the uncertain matches follow the sort order

A filter could make its uncertain matches symmetrical, including `1990` in a range from
`1990-06` because some day of 1990 might fall inside it. That would be a second rule beside the
order every lookup and every sort already agree on, and an index could not serve it. The
filters keep the one rule, and `method` is there for the developer who needs another.
