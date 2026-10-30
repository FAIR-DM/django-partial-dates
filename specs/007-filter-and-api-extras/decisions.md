# Decisions — FS-007: Ready-made django-filter filters and a Django REST framework field

Decisions made while specifying, where the issue and the roadmap were silent. Each one came from
the goals, the constitution, FS-003, FS-004, FairDM's filters as prior art, and the behaviour of
django-filter 26.2 and Django REST framework 3.18.3, run against this package's field.

## Who can newly do what

A developer can add a validated partial date filter to a django-filter `FilterSet`, and declare a
partial date serializer field in Django REST framework, without writing either. A user of their
site can narrow a list by a date, giving as much of it as they know.

## The reading of the issue that the spec is written from

Two optional extras, one for each library, each usable without the other. The django-filter extra
gives a filter for one date, a filter for a range, and filters on the year, month or day. The Django
REST framework extra gives a serializer field for the ISO form. The core never imports either. It
serves G10 and depends on #14, which is delivered. It also builds on the form field from #19, which
is delivered. Display (#28) and the move of FAIR-DM itself are out of scope. The roadmap names this
item as a deliverable and the maintainer asked for it, so its Aspirational standing is no bar.

## What running the two libraries against the field showed

- Naming a `PartialDateField` in `Meta.fields` raises `AssertionError` in django-filter, because
  the field has no mapping. `Meta.filter_overrides` is django-filter's documented way to add one.
- With that mapping, `exact`, `gte` and `lte` become the mapped filter, and `year`, `month` and
  `day` become django-filter's own `NumberFilter`, because they resolve to the transform's integer
  field. `isnull` becomes its `BooleanFilter`. `range` and `in` build classes from the mapped filter
  that expect comma-separated text.
- A `CharFilter` on the field given `1990-6` raises `ValueError` when the queryset is evaluated.
  This is the failure FairDM's own filter class exists to prevent.
- `NumberFilter` with `lookup_expr="year"` accepts `1990.5` and treats it as `1990`.
- The form field reused from FS-004 works as a filter's `field_class`. Its widget reads
  `<name>_year`, `<name>_month` and `<name>_day` and ignores `<name>`, and its `decompress` gives
  three `None`s for text that is not an ISO form, so a plain reuse would treat `?collected=1990-6`
  as no entry. FR-008 rules that out.
- A `ModelSerializer` with nothing declared uses Django REST framework's `ModelField` and already
  reads and writes the ISO form. On a required date it accepts `""`, turns it into `None`, and the
  save raises `IntegrityError`, which is a server error. Declaring this feature's field prevents it.

## D1 — Three stories

Adding filters is what a developer does, narrowing a list is what a user does, and exposing a date
through an API is a second thing a developer sets out to do. A developer's and a user's stories are
never merged. Each extra's independence, the Meta.fields route and the API client's query string
are scenarios and not stories, because nobody sets out to do them on their own.

**ADR:** none. This is how the specification is divided.

## D2 — A filter reads both the selects and the ISO form

FS-004's form field is the thing to reuse, because a user choosing how much of a date they know is
the point of it. But R8 pairs filters with an API, and FairDM's filters serve both. A client that sends
`?collected=1990-06` has no selects to fill in. So one filter takes both, under the query parameters
each would naturally use. When both arrive the ISO form is used, because a client that names it
asked for exactly that.

**ADR:** none. It is the public behaviour of the filter, and the spec records it.

## D3 — The range's upper bound takes in the whole of its period

This is the decision a reader is most likely to want to look at. FS-003's bound is a position in
the sort order, and its guide says so, with `lte="1991-03"` leaving out `1991-03-15`. That is right
for a lookup, whose rules a developer reads. A range on a form is read by a person, who takes "to
March 1991" to include the middle of March. Dropping those records is a wrong answer and not an
uncertain one: `1991-03-15` is certainly inside. So the upper bound compares with the last day of
the period, using the `end` the value already gives. The lower bound needs nothing, because every
date in `1990-06` already sorts at or after it.

Keeping the plain lookup semantics was the alternative, and FS-003's guide already has a recipe for
it. Every project would then get the trap on its filter page or write the correction itself, which
is the thing this feature exists to save. `PartialDateFilter(lookup_expr="lte")` stays available for
a position.

The rule for an empty range follows from this. A range finds nothing only when its first bound sorts
after the last day of the second bound's period, so `1991-03-15` to `1991-03` sorts backwards and
still finds the rest of March, where FS-003's `range` finds nothing. The guide states the difference,
and tests pin both sides of the rule.

**ADR:** yes. This is the one place two public things called range answer differently on purpose,
and someone will read it as a bug. An ADR is written in the build, on the same terms as ADR 0002,
with its number claimed at merge. FS-003 is unchanged.

## D4 — Uncertain matches follow the sort order and are not made symmetrical

`1990` is out of a range from `1990-06`, and `1991` is in a range to `1991-03`. Both are uncertain
matches, treated differently, because each falls where it sorts. A filter with an `uncertain=`
option could include or exclude them all, but the roadmap does not ask for it, the guide's recipes
already cover both with `Q` objects, django-filter's `method` is the place for them, and a second
rule would have to be documented, tested and maintained for a need nobody has shown. Article II
settles it.

**ADR:** none.

## D5 — A range's parameters are `_after` and `_before`

They are django-filter's names for `DateFromToRangeFilter`, so a developer knows them already, and
FairDM's `date_after` and `date_before` already use them. A FairDM filter declared as `date` keeps
the parameters its users have.

**ADR:** none.

## D6 — Year, month and day stay on `PartialDateFilter`

One class with `lookup_expr` is how django-filter developers already work, so there is no separate
class for parts. Its value is a whole number and never a partial date. `1990.5` is refused, which
`NumberFilter` would have rounded. Through `Meta.fields` django-filter makes its own `NumberFilter`,
which gives the same rows for a whole number, and that is left alone rather than overriding the
mapping of every integer. It is a behaviour of a dependency on every integer field in a project.

**ADR:** none.

## D7 — Filtering by precision gets no filter of its own

"Precision lookups" in the roadmap is read as the year, month and day lookups, which R3 calls the
same. Asking for dates recorded only to the year is `month__isnull`, reached with `isnull` in
`Meta.fields` or django-filter's `BooleanFilter`, and the guide says so.

**ADR:** none.

## D8 — The serializer refuses an empty string in JSON

The model field stores `""` as no date, which suits a form. On an API the wire format is the ISO form
or `null`, and Django REST framework's `DateField` refuses `""` the same way. Accepting it is what
gives a required date its database error. HTML form input is different: Django REST framework itself
turns an empty entry into `None` on a field that allows it.

**ADR:** none.

## D9 — `ModelSerializer` is left alone

The core cannot change `ModelSerializer.serializer_field_mapping` without importing Django REST
framework, and changing a global mapping from the extra would depend on import order. A project
declares the field, or names it in its own mapping, and the guide shows both. Nothing needs to
happen for a nullable date, because the fallback writes the same ISO form.

**ADR:** none.

## D10 — The extras are named after the packages they install

`django-filter` and `djangorestframework`, so the install line reads for itself and there is no
vocabulary to learn. There is no combined extra: a project asks for both by naming both.

**ADR:** none.

## D11 — No sketch

The feature adds no page. A filter shows the selects FS-004 already built, and the example project
uses them on a list that exists. Everything can be tested.

**ADR:** none.

## D12 — Nothing added for API schemas

Generated schemas see the field as text. FairDM has its own schema code and no need for this package
to integrate with a generator. Adding one would be a third optional dependency.

**ADR:** none.

## D13 — The first task was done directly

Adding two lines to the dev group has no design in it, so T001 was not dispatched. Each extra is
declared by the task that adds the module importing it, because `deptry` is red on an extra nothing
uses.

**ADR:** none — a packaging edit that nothing else inherits.

## D14 — The filter refuses lookups it cannot serve

The spec leaves `range` and `in` out of `Meta.fields`. Left alone, django-filter builds a
comma-separated class from the mapped filter, and `in` then validates and finds nothing, which is a
quiet wrong answer. `PartialDateFilter` raises `ImproperlyConfigured` when it is built with a lookup
outside its list, so the mistake shows up when the class is defined.

**ADR:** none — local to one class, and the guide states the list.

## D15 — The extras' lowest versions are the ones the tests run

`django-filter>=26.2` and `djangorestframework>=3.18` name Django 5.2, 6.0 and 6.1 in their metadata.
An older lower bound would claim support for a pair nobody has run.

**ADR:** none — a packaging choice that a later release can loosen.

## D16 — `PartialDateFilter` takes `years`, and a filter's widget is its own

A filter's selects also have to read the ISO form, so `PartialDateWidget` passed in by hand would
lose that. `years` on the filter reaches the right widget and states what the developer means. Adding
the reading to `PartialDateWidget` itself would change a core form for an extra's sake.

**ADR:** none — local to the filter module.

## D17 — The non-whole-number rule covers this package's filters

The design review showed that `Meta.fields` naming `year`, `month` or `day` gives django-filter's own
`NumberFilter`, which rounds `1990.5`, as D6 already accepted. FR-008 and US-1 scenario 7 now say
which filters they cover, and the guide states the difference. No behaviour changes from what D6
recorded.

**ADR:** none — a precision of wording in the specification, and D6 already settles the behaviour.
