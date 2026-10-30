# Querying

You filter a partial date field in the database with its year, month and day, and with ranges
whose bounds are partial dates. A partial date is uncertain, so a filter can meet a date that
might or might not be what you asked for. This page says which dates each filter includes, so you
can check a query before you rely on it, and it gives recipes for the other rules.

## Set up the examples

The examples use this model, with `collected` indexed.

```python
from django.db import models

from partial_dates import PartialDateField


class Sample(models.Model):
    collected = PartialDateField(null=True, blank=True, db_index=True)
```

They run against these rows, one sample for each value, and one sample holding no date.

```python
from partial_dates import PartialDate

for text in [
    "1990", "1990-05", "1990-05-31", "1990-06", "1990-06-01", "1990-06-14",
    "1990-07", "1990-12", "1991", "1991-03", "1991-03-15", "1991-04",
    "1991-06", "1991-06-02", None,
]:
    Sample.objects.create(collected=text)
```

Every result below is shown as the dates in it, in order, by this function. It names
`nulls_last`, so the sample holding no date comes last on both PostgreSQL and SQLite.

```python
>>> from django.db.models import F, Q
>>> def show(queryset):
...     ordered = queryset.order_by(F("collected").asc(nulls_last=True))
...     return [
...         None if sample.collected is None else str(sample.collected)
...         for sample in ordered
...     ]
```

## Filter by year, month or day

`year`, `month` and `day` read the recorded parts of a date. Each takes a whole number and finds
the rows whose part equals it. A date whose part is unknown is never found.

```python
>>> show(Sample.objects.filter(collected__year=1990))
['1990', '1990-05', '1990-05-31', '1990-06', '1990-06-01', '1990-06-14',
 '1990-07', '1990-12']
>>> show(Sample.objects.filter(collected__month=6))
['1990-06', '1990-06-01', '1990-06-14', '1991-06', '1991-06-02']
>>> show(Sample.objects.filter(collected__day=14))
['1990-06-14']
```

The field registers these as the transforms `Year`, `Month` and `Day` from
`partial_dates.lookups`, so you never import them. Every date has a year, so `year` finds a date
at every precision. `1990` has no month, so
`month=6` leaves it out. `1990-06` has no day, so `day=14` leaves it out, and `day=1` finds
`1990-06-01` and not `1990-06`.

The table shows what each filter does with a date at each precision.

| Row | `year=1990` | `month=6` | `day=14` | `month__isnull=True` | `day__isnull=True` |
|---|---|---|---|---|---|
| `1990` | yes | no | no | yes | yes |
| `1990-06` | yes | yes | no | no | yes |
| `1990-06-14` | yes | yes | yes | no | no |
| `1991` | no | no | no | yes | yes |
| no date | no | no | no | yes | yes |

Each part compares as a number, so Django's comparisons work on it.

```python
>>> show(Sample.objects.filter(collected__month__gte=6, collected__year=1990))
['1990-06', '1990-06-01', '1990-06-14', '1990-07', '1990-12']
>>> show(Sample.objects.filter(collected__month__in=[3, 4]))
['1991-03', '1991-03-15', '1991-04']
>>> show(Sample.objects.filter(collected__year__range=(1991, 1991), collected__day=2))
['1991-06-02']
```

A number that no date can hold finds nothing and raises nothing.

```python
>>> Sample.objects.filter(collected__month=13).exists()
False
>>> Sample.objects.filter(collected__year=10000).exists()
False
```

### Exclude a part

A date whose part is unknown is in neither `filter(month=6)` nor `exclude(month=6)`. Saying that
a year-only date is not in June would claim something nobody recorded. `day` works the same
way.

```python
>>> show(Sample.objects.exclude(collected__month=6))
['1990-05', '1990-05-31', '1990-07', '1990-12', '1991-03', '1991-03-15',
 '1991-04', None]
```

The result holds no `1990` and no `1991`. It holds the sample with no date, as `exclude` does on
any Django field that allows `NULL`. To ask for the dates whose month is unknown, say so with
`month__isnull`.

## Find dates by precision

`month__isnull` and `day__isnull` select by precision. `month__isnull=True` finds the dates
recorded to the year, and the samples holding no date.

```python
>>> show(Sample.objects.filter(collected__month__isnull=True))
['1990', '1991', None]
>>> show(
...     Sample.objects.filter(
...         collected__month__isnull=False, collected__day__isnull=True
...     )
... )
['1990-05', '1990-06', '1990-07', '1990-12', '1991-03', '1991-04', '1991-06']
```

## Filter by a range

`gt`, `gte`, `lt`, `lte` and `range` take a partial date as the bound, written as a `PartialDate`
or as its ISO form, at any precision. Each row is compared by the order of its ISO form, which is
the order `sorted()` gives the values: a year sorts before the months in it, and a month before
the days in it.

```python
>>> show(Sample.objects.filter(collected__gte="1990-06", collected__lt="1990-12"))
['1990-06', '1990-06-01', '1990-06-14', '1990-07']
>>> show(Sample.objects.filter(collected__gte=PartialDate(1991, 3), collected__lte="1991-04"))
['1991-03', '1991-03-15', '1991-04']
```

A bound names a position in that order and not a period. `lte="1990-06"` finds `1990` and
`1990-06` and leaves out `1990-06-14`, which sorts after it.

```python
>>> show(Sample.objects.filter(collected__lte="1990-06"))
['1990', '1990-05', '1990-05-31', '1990-06']
```

`range` takes two bounds and finds the same rows as `gte` of the first with `lte` of the second.
The bounds can differ in precision and in form. A range whose first bound sorts after its second
finds nothing.

```python
>>> show(Sample.objects.filter(collected__range=("1990-06", PartialDate(1990, 6, 14))))
['1990-06', '1990-06-01', '1990-06-14']
>>> show(Sample.objects.filter(collected__range=("1991", "1990")))
[]
```

`in` finds the rows equal to one of the values and nothing else, so `1990` does not find
`1990-06`.

```python
>>> show(Sample.objects.filter(collected__in=["1990", PartialDate(1990, 6)]))
['1990', '1990-06']
```

A sample holding no date is never found by a bound, and `exclude` of a bound returns it.

```python
>>> show(Sample.objects.exclude(collected__gte="1990-06"))
['1990', '1990-05', '1990-05-31', None]
```

A bound that is not a partial date is refused before any query runs, with the same error the
value gives. That covers text such as `1990-6`, a `datetime.date` and a number. A real date is
refused because it carries a day that may never have been recorded.

```python
>>> Sample.objects.filter(collected__gte="1990-6")
Traceback (most recent call last):
    ...
ValueError: Not a partial date in ISO form: '1990-6'
>>> import datetime
>>> Sample.objects.filter(collected__gte=datetime.date(1990, 6, 1))
Traceback (most recent call last):
    ...
ValueError: Not a partial date in ISO form: datetime.date(1990, 6, 1)
```

## Check a bound at month precision

The table shows what each comparison does with a row at each precision, for a bound of
`1990-06`. The rows are in sort order. `1990` is the uncertain match: its period is partly inside
and partly outside what each comparison asks for, and it sorts before the bound. So `gt` and
`gte` leave it out, and `lt` and `lte` include it.

| Bound | Row | `gt` | `gte` | `lt` | `lte` |
|---|---|---|---|---|---|
| `1990-06` | `1990` | no | no | yes | yes |
| `1990-06` | `1990-05` | no | no | yes | yes |
| `1990-06` | `1990-05-31` | no | no | yes | yes |
| `1990-06` | `1990-06` | no | yes | no | yes |
| `1990-06` | `1990-06-01` | yes | yes | no | no |
| `1990-06` | `1990-06-14` | yes | yes | no | no |
| `1990-06` | `1990-07` | yes | yes | no | no |
| `1990-06` | `1991` | yes | yes | no | no |

## Check a bound at year or day precision

The same rule holds at the other two precisions of bound.

| Bound | Row | `gte` | `lte` |
|---|---|---|---|
| `1990` | `1990` | yes | yes |
| `1990` | `1990-06` | yes | no |
| `1990` | `1990-06-14` | yes | no |
| `1990-06-14` | `1990` | no | yes |
| `1990-06-14` | `1990-06` | no | yes |
| `1990-06-14` | `1990-06-14` | yes | yes |

## Take in the whole of a month or year

Because a bound is a position, `lte="1991-03"` leaves out `1991-03-15`. To take in the whole of
the month or year that an upper bound names, bound it by the position that follows it.

- For a month, use `lt` with the next month, or `lte` with its last day.
- For a year, use `lt` with the next year, or `lte` with its last day. Or filter on the part:
  `year__lte=2020` finds every date in 2020 or before, at any precision.

```python
>>> show(Sample.objects.filter(collected__gte="1991-03", collected__lt="1991-04"))
['1991-03', '1991-03-15']
>>> show(Sample.objects.filter(collected__gte="1991-03", collected__lte="1991-03-31"))
['1991-03', '1991-03-15']
>>> show(Sample.objects.filter(collected__year__lte=1990))
['1990', '1990-05', '1990-05-31', '1990-06', '1990-06-01', '1990-06-14',
 '1990-07', '1990-12']
```

## Add every uncertain date to a range

A range from `1990-06-14` to `1991-03` leaves out `1990` and `1990-06`, because both sort before
the lower bound, though each might hold a day in the range. To add them, add the lower bound's
enclosing periods with `in`: `1990` for a bound of `1990-06`, and `1990` and `1990-06` for a bound
of `1990-06-14`.

```python
>>> low, high = "1990-06-14", "1991-03"
>>> show(Sample.objects.filter(collected__range=(low, high)))
['1990-06-14', '1990-07', '1990-12', '1991', '1991-03']
>>> show(
...     Sample.objects.filter(
...         Q(collected__range=(low, high)) | Q(collected__in=["1990", "1990-06"])
...     )
... )
['1990', '1990-06', '1990-06-14', '1990-07', '1990-12', '1991', '1991-03']
```

## Leave every uncertain date out of a range

The same range includes `1991`, because it sorts before the upper bound, though its days might
all fall after March. To leave it out, exclude the upper bound's enclosing periods with `in`:
`1991` for a bound of `1991-03`, and `1991` and `1991-03` for a bound of `1991-03-15`.

```python
>>> show(
...     Sample.objects.filter(collected__range=(low, high)).exclude(
...         collected__in=["1991"]
...     )
... )
['1990-06-14', '1990-07', '1990-12', '1991-03']
```

## Find June of any year

Filter on the month. It finds every date recorded to the month or the day in a June, in any
year.

```python
>>> show(Sample.objects.filter(collected__month=6))
['1990-06', '1990-06-01', '1990-06-14', '1991-06', '1991-06-02']
```

Dates recorded to the year only are left out, because their month is unknown. `1990` might have
been a June, and the filter does not claim it was. To list them next to the June dates, ask for
them with `month__isnull`.

```python
>>> show(Sample.objects.filter(Q(collected__month=6) | Q(collected__month__isnull=True)))
['1990', '1990-06', '1990-06-01', '1990-06-14', '1991', '1991-06', '1991-06-02', None]
```

## Why a bound is a position in the sort order

A filter compares text, and partial dates are uncertain, so some matches are uncertain too. This
package gives every comparison one rule, the order of the ISO form, and states the result at
each bound. The order is the one `PartialDate` sorts in, so every filter and every sort agree. A
date whose period contains the bound sorts before it, so `gt` and `gte` leave it out and `lt` and
`lte` include it. [ADR 0001](../adr/0001-store-partial-dates-as-iso-8601-strings.md) records the
decision.

## Which of Django's lookups this page does not cover

Django gives every text-based field lookups such as `contains`, `startswith` and `regex`. They
stay as Django gives them and read the stored text. This page does not cover them. Use the
filters above to ask about a year, a month, a day or a range.

## Which queries use an index

When the column has an index, a range filter such as `gte` with `lte`, and a filter on one year
with `year=1990`, use it on PostgreSQL and SQLite. Filters on `month` and `day`, and comparisons
of `year` other than equality, read the whole table. "June of any year" is the usual example.
Whether a column has an index stays your decision.

A filter on one year uses the index because `YearExact`, the `exact` lookup of `Year`, compares
the stored text with the year's first and last possible text, `1990` and `1990-99`, instead of
reading the year out of every row. Comparing the year with another field, as in
`year=F("other__year")`, takes Django's own comparison.
