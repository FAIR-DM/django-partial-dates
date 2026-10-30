# ADR 0003 — A range filter takes in the whole of its last period

**Status:** accepted

## Decision

`PartialDateRangeFilter` finds a row when it sorts at or after the first bound and at or before the
last day of the period of the second bound. `1991-03` as the second bound compares as `1991-03-31`,
and `1991` as `1991-12-31`.

A range filter therefore finds nothing only when its first bound sorts after that last day.
`1991-03-15` to `1991-03` finds the rest of March, and `1991-04` to `1991-03` finds nothing.

The `range` lookup on the model field does not change. Its second bound is a position in the sort
order, so `collected__range=("1991-03-15", "1991-03")` finds nothing. These are the two public
things in this package called range, and they answer differently on purpose. A filter declared with
`PartialDateFilter(lookup_expr="lte")` is the plain lookup and keeps its position.

## Why

A lookup is written by a developer who can read its rules. A range filter is filled in by a person
on a page, who takes "to March 1991" to include the middle of March. With the lookup's rule,
`1991-03-15` would be dropped from that list. That is a wrong answer and not an uncertain one,
because the date is certainly inside what the person asked for.

| Option | Result |
|---|---|
| Follow the lookup exactly | Rejected. Every project would either show the wrong list or write the same correction, and saving that is what the filter is for. |
| Change the lookup to match | Rejected. A bound as a position is what makes `gte`, `lte`, `range` and `order_by` one rule that an index serves, and FS-003 documents it filter by filter. |
| **Widen the second bound in the filter** | Chosen. It uses the `end` the value already gives, and the result is still one comparison on the column. |

The lower bound needs no change. Every date in `1990-06` already sorts at or after it.

Uncertain matches stay where the sort order puts them, as they do for every lookup: `1990` is outside
a range from `1990-06`, and `1991` is inside a range to `1991-03`. A rule that included or left out
every uncertain date would be a second rule, and django-filter's `method` is there for a developer
who needs one.

## Revisit if

Projects keep declaring the lookup's position for their range filters, which would mean people on
those sites read a bound as a position after all.
