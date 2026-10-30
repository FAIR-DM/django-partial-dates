# Querying

You filter, order, select and group a partial date field in the database with its year, month
and day, and with ranges whose bounds are partial dates. A partial date is uncertain, so a
filter can meet a date that might or might not be what you asked for. This page says which dates
each filter includes, so you can check a query before you rely on it, and it gives recipes for
the other rules, including a date axis and a drilldown. To offer these filters to the people
using a site, see [filtering with django-filter](filtering.md).

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
at every precision. `1990` has no month, so `month=6` leaves it out. `1990-06` has no day, so
`day=14` leaves it out, and `day=1` finds `1990-06-01` and not `1990-06`.

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

## Order by the date

Order by the field and the dates come in the order `sorted()` gives them: a year, then the months
in it, and each month before its days. Put a minus in front for the reverse.

```python
>>> def listed(queryset):
...     return [
...         None if sample.collected is None else str(sample.collected)
...         for sample in queryset
...     ]
>>> in_1991 = Sample.objects.filter(collected__year=1991)
>>> listed(in_1991.order_by("collected"))
['1991', '1991-03', '1991-03-15', '1991-04', '1991-06', '1991-06-02']
>>> listed(in_1991.order_by("-collected"))
['1991-06-02', '1991-06', '1991-04', '1991-03-15', '1991-03', '1991']
```

Ordering by the field uses the index on the column, on both databases.

### Say where a row holding no date goes

A sample holding no date has `NULL` in the column, and PostgreSQL and SQLite sort `NULL` in
opposite places. SQLite puts it first when ascending. PostgreSQL puts it last. A query that
meets such a row gives different results on the two databases, unless it names `nulls_first` or
`nulls_last`. Every example below that can meet one names it.

```python
>>> listed(Sample.objects.order_by(F("collected").asc(nulls_first=True)))[:3]
[None, '1990', '1990-05']
>>> listed(Sample.objects.order_by(F("collected").asc(nulls_last=True)))[-3:]
['1991-06', '1991-06-02', None]
>>> listed(Sample.objects.order_by(F("collected").desc(nulls_last=True)))[-3:]
['1990-05', '1990', None]
```

### Say where a date with an unknown part goes

Ordering by `year`, `month` or `day` is ordering by a number. A date whose part is unknown has
no number, so it is empty in the same way as a row holding no date, and it sorts where each
database sorts `NULL`. Name `nulls_first` or `nulls_last` here too.

```python
>>> listed(
...     Sample.objects.filter(collected__year=1991).order_by(
...         F("collected__month").asc(nulls_last=True), "collected"
...     )
... )
['1991-03', '1991-03-15', '1991-04', '1991-06', '1991-06-02', '1991']
```

## Count by year, month and day

Select a part with `values_list` and count each value with `annotate`. A date appears under the
part it has and under `None` for a part it lacks, so a year-only date is counted in its year and
in no month.

```python
>>> from django.db.models import Count
>>> list(
...     Sample.objects.values_list("collected__year")
...     .annotate(total=Count("pk"))
...     .order_by(F("collected__year").asc(nulls_last=True))
... )
[(1990, 8), (1991, 6), (None, 1)]
>>> list(
...     Sample.objects.filter(collected__year=1991)
...     .values_list("collected__month")
...     .annotate(total=Count("pk"))
...     .order_by(F("collected__month").asc(nulls_last=True))
... )
[(3, 2), (4, 1), (6, 2), (None, 1)]
>>> list(
...     Sample.objects.filter(collected__year=1990, collected__month=6)
...     .values_list("collected__day")
...     .annotate(total=Count("pk"))
...     .order_by(F("collected__day").asc(nulls_last=True))
... )
[(1, 1), (14, 1), (None, 1)]
```

The last group holds `1990-06`, which is in June of 1990 and has no day. Filter on
`day__isnull=False` to count only the dates recorded to the day.

## Put dates on a date axis

A chart axis needs real dates. The field registers the transform `Start` from
`partial_dates.lookups` as `start`, so you never import it. `start` gives each partial date as the
`datetime.date` its period starts on: `1990` is 1 January 1990, `1990-06` is 1 June 1990, and
`1990-06-14` is itself.

```python
>>> [
...     (day.isoformat(), total)
...     for day, total in Sample.objects.filter(collected__year=1991)
...     .values_list("collected__start")
...     .annotate(total=Count("pk"))
...     .order_by("collected__start")
... ]
[('1991-01-01', 1), ('1991-03-01', 1), ('1991-03-15', 1), ('1991-04-01', 1),
 ('1991-06-01', 1), ('1991-06-02', 1)]
```

A year-only date sits on 1 January of its year. That is the first day of its period and not a
claim that anything happened that day. To leave the year-only dates off a month axis, keep only
the dates with a month, and to leave off the month-only dates too, keep only the dates with a
day.

```python
>>> [
...     (day.isoformat(), total)
...     for day, total in Sample.objects.filter(collected__month__isnull=False)
...     .values_list("collected__start")
...     .annotate(total=Count("pk"))
...     .order_by("collected__start")
... ][:3]
[('1990-05-01', 1), ('1990-05-31', 1), ('1990-06-01', 2)]
>>> [
...     (day.isoformat(), total)
...     for day, total in Sample.objects.filter(collected__day__isnull=False)
...     .values_list("collected__start")
...     .annotate(total=Count("pk"))
...     .order_by("collected__start")
... ]
[('1990-05-31', 1), ('1990-06-01', 1), ('1990-06-14', 1), ('1991-03-15', 1),
 ('1991-06-02', 1)]
```

`1990-06` and `1990-06-01` share a start, so the first query counts them together. They stay
different values: `start` is for placing a date on an axis, and the field still tells them
apart.

`start` compares with real dates, so a window on the axis is an ordinary filter.

```python
>>> import datetime
>>> show(
...     Sample.objects.filter(
...         collected__start__gte=datetime.date(1990, 6, 1),
...         collected__start__lt=datetime.date(1990, 7, 1),
...     )
... )
['1990-06', '1990-06-01', '1990-06-14']
```

Order by `start` with the field as the second key, so dates that share a start have a fixed order.

```python
>>> listed(
...     Sample.objects.filter(collected__start=datetime.date(1990, 6, 1)).order_by(
...         "collected__start", "collected"
...     )
... )
['1990-06', '1990-06-01']
```

## Drill down from a year to a day

A drilldown counts by year, then by the months of the year the reader picks, then by the days of
the month they pick. Each step is the count above with the earlier choices as filters.

1. Count by year with `values_list("collected__year")`.
2. Filter on the chosen year and count by `collected__month`.
3. Filter on the chosen year and month and count by `collected__day`.

Each step has a `None` group for the dates that stop at the level above. Show it as "month
unknown" or "day unknown", or drop it with `month__isnull=False` or `day__isnull=False`.

## Check what each precision gives

The table shows what each part gives for a date at each precision.

| Date | `year` | `month` | `day` | `start` |
|---|---|---|---|---|
| `1990` | 1990 | none | none | 1990-01-01 |
| `1990-06` | 1990 | 6 | none | 1990-06-01 |
| `1990-06-14` | 1990 | 6 | 14 | 1990-06-14 |
| no date | none | none | none | none |

## Check which queries use an index

When the column has an index, a range filter such as `gte` with `lte`, a filter on one year
with `year=1990`, and ordering by the field itself use it on PostgreSQL and SQLite. Filters on
`month` and `day`, and comparisons of `year` other than equality, read the whole table. "June of
any year" is the usual example. Whether a column has an index stays your decision.

A filter on one year uses the index because `YearExact`, the `exact` lookup of `Year`, compares
the stored text with the year's first and last possible text, `1990` and `1990-99`, instead of
reading the year out of every row. Comparing the year with another field, as in
`year=F("other__year")`, takes Django's own comparison.
## Leave out Django's text lookups

Django gives every text-based field lookups such as `contains`, `startswith` and `regex`. They
stay as Django gives them and read the stored text. This page does not cover them. Use the
filters above to ask about a year, a month, a day or a range.

## Why a bound is a position in the sort order

A filter compares text, and partial dates are uncertain, so some matches are uncertain too. This
package gives every comparison one rule, the order of the ISO form, and states the result at
each bound. The order is the one `PartialDate` sorts in, so every filter and every sort agree. A
date whose period contains the bound sorts before it, so `gt` and `gte` leave it out and `lt` and
`lte` include it. [ADR 0001](../adr/0001-store-partial-dates-as-iso-8601-strings.md) records the
decision.

## Why a year sits on 1 January on a date axis

A chart axis holds real dates and a partial date is not one. `start` has to put a year somewhere,
and the first day of its period is the one place that is always inside it and never later than
anything the date could mean. It is a position on the axis, not a record of when the thing
happened. `end` is not offered, because a period's last day is no more a claim than its first,
and a date axis needs one end of the period.

## Why empty values sort where the database puts them

The package stores `NULL` for a row holding no date, and `year`, `month`, `day` and `start` give
`NULL` for a part that is not recorded. Which end of a sort `NULL` takes is the database's
decision: SQLite first, PostgreSQL last when ascending. The package does not override it, so
that ordering by a partial date behaves like ordering by any other nullable column in your
project. The cost is that you name `nulls_first` or `nulls_last` wherever the result must be the
same on both.
