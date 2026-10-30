# Partial date values

A `PartialDate` is a date in Python code, known to the year, the month or the day. It holds a year
and, when they were recorded, a month and a day. It is immutable, so a value never changes once it
is built. This page shows how to build one, read its parts, compare it with another and ask which
period it covers.

## Build a value

Give the parts you know. A part that was not recorded is `None`.

```python
>>> from partial_dates import PartialDate, Precision
>>> PartialDate(1990)
PartialDate(year=1990, month=None, day=None)
>>> PartialDate(1990, 6, 14)
PartialDate(year=1990, month=6, day=14)
```

## Read and write the ISO form

`PartialDate.fromisoformat` reads the three ISO forms, `YYYY`, `YYYY-MM` and `YYYY-MM-DD`, and
nothing else. `isoformat()` writes the form back, and reading it gives an equal value.

```python
>>> value = PartialDate.fromisoformat("1990-06")
>>> value == PartialDate(1990, 6)
True
>>> value.isoformat()
'1990-06'
>>> str(PartialDate(990))
'0990'
```

To show a date to a reader, use `display_form()`. [Showing a partial date](showing.md) covers it.

## Find out how much was recorded

The `precision` of a value says how much of it was recorded, and the parts are attributes.

```python
>>> value.year, value.month, value.day
(1990, 6, None)
>>> value.precision is Precision.MONTH
True
```

## Handle an invalid date

Building or reading something that is not a date, such as a day without a month, `1990-02-30` or a
year outside 0001 to 9999, raises `ValueError`.

```python
>>> PartialDate.fromisoformat("1990-6")
Traceback (most recent call last):
    ...
ValueError: Not a partial date in ISO form: '1990-6'
```

## Sort and compare values

Values sort in the order of their ISO forms, so a year comes before its months and a month before
its days. Two values are equal when all their parts are equal: `1990` is not `1990-01-01`.

```python
>>> values = [
...     PartialDate(1991),
...     PartialDate(1990, 6, 14),
...     PartialDate(1990),
...     PartialDate(1990, 6),
... ]
>>> [value.isoformat() for value in sorted(values)]
['1990', '1990-06', '1990-06-14', '1991']
>>> PartialDate(1990) == PartialDate(1990, 1, 1)
False
```

A value is never equal to a `datetime.date`, a string or an integer, and ordering against one
raises `TypeError`.

## Use a value as a key

Values are hashable, so they work as set members and dictionary keys.

```python
>>> len({PartialDate(1990, 6), PartialDate.fromisoformat("1990-06")})
1
>>> counts = {PartialDate(1990, 6): 3}
>>> counts[PartialDate.fromisoformat("1990-06")]
3
```

## Get the period a value covers

`start` and `end` give the first and last day of the period as `datetime.date` objects, with the
last day of February worked out for the year.

```python
>>> PartialDate(1990).start, PartialDate(1990).end
(datetime.date(1990, 1, 1), datetime.date(1990, 12, 31))
>>> PartialDate(2000, 2).end
datetime.date(2000, 2, 29)
>>> PartialDate(1990, 6, 14).start == PartialDate(1990, 6, 14).end
True
```

## Find out whether one value is earlier than another

`relation_to` says whether the period of one value is `Relation.BEFORE`, `Relation.AFTER` or
`Relation.OVERLAPPING` the period of another. Passing anything but a `PartialDate` raises
`TypeError`.

```python
>>> from partial_dates import Relation
>>> PartialDate(1990, 6).relation_to(PartialDate(1991)) is Relation.BEFORE
True
>>> PartialDate(1991).relation_to(PartialDate(1990, 6)) is Relation.AFTER
True
>>> PartialDate(1990).relation_to(PartialDate(1990, 6)) is Relation.OVERLAPPING
True
>>> PartialDate(1990) < PartialDate(1990, 6)
True
```

## Why sorting does not say which date is earlier

Sorting and "is this one earlier?" are different questions. `1990` sorts before `1990-06`, but the
two overlap, so neither is earlier. The last example above shows both answers side by side.
