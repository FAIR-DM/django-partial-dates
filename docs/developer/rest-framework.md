# Django REST framework

You expose a partial date through an API with `PartialDateField`, a serializer field for Django
REST framework. A client reads the date as its ISO form, `1990`, `1990-06` or `1990-06-14`, or as
`null` when a record has none, and writes the same text. Anything else is reported as an ordinary
validation error with the code `invalid`. The field lives in `partial_dates.rest_framework`, and
the core package never imports Django REST framework.

## Set up the examples

The examples use these models, the ones from the [querying guide](querying.md) and the
[installation page](installation.md), with one more whose date is required.

```python title="models.py"
from django.db import models

from partial_dates import PartialDateField


class Sample(models.Model):
    collected = PartialDateField(null=True, blank=True, db_index=True)


class Event(models.Model):
    occurred = PartialDateField(unique=True)
```

Every example imports what it uses from these lines.

```python
>>> from types import SimpleNamespace
>>> from rest_framework import serializers
>>> from partial_dates import PartialDate
>>> from partial_dates.rest_framework import PartialDateField
```

## Install the extra

Install the package with the `djangorestframework` extra, in the environment your project runs in.

```console
$ pip install "django-partial-dates[djangorestframework]"
```

The extra adds Django REST framework and nothing else. Your project needs no entry in
`INSTALLED_APPS` for this field. Installing it does not install django-filter, and the field never
imports it.

## Declare the field

Declare `PartialDateField` on a serializer as you would any other field.

```python
>>> class SampleSerializer(serializers.Serializer):
...     collected = PartialDateField()
```

The field takes the options every Django REST framework field takes, such as `required`,
`read_only`, `source`, `allow_null` and `validators`, and they behave as they do on any other
field.

## Read a date

Give the serializer an object and read `data`. A date is written at the precision it was
recorded at, with nothing added, and a record with no date is written as `None`, which a JSON
renderer turns into `null`.

```python
>>> SampleSerializer(SimpleNamespace(collected=PartialDate(1990))).data["collected"]
'1990'
>>> SampleSerializer(SimpleNamespace(collected=PartialDate(1990, 6))).data["collected"]
'1990-06'
>>> SampleSerializer(SimpleNamespace(collected=PartialDate(1990, 6, 14))).data["collected"]
'1990-06-14'
>>> SampleSerializer(SimpleNamespace(collected=None)).data["collected"] is None
True
```

An object that still holds ISO text, such as a model instance you built in Python and have not
read back from the database, is written as that same text.

```python
>>> SampleSerializer(SimpleNamespace(collected="1990-06")).data["collected"]
'1990-06'
```

## Write a date

Give the serializer incoming data and call `is_valid()`. Text in one of the three ISO forms, or a
`PartialDate`, is validated to the `PartialDate` it names.

```python
>>> serializer = SampleSerializer(data={"collected": "1990-06"})
>>> serializer.is_valid()
True
>>> serializer.validated_data["collected"]
PartialDate(year=1990, month=6, day=None)
```

A `ModelSerializer` that declares the field saves the value.

```python
>>> class SampleModelSerializer(serializers.ModelSerializer):
...     collected = PartialDateField(allow_null=True)
...
...     class Meta:
...         model = Sample
...         fields = ["collected"]
>>> serializer = SampleModelSerializer(data={"collected": "1990-06-14"})
>>> serializer.is_valid()
True
>>> serializer.save().collected
PartialDate(year=1990, month=6, day=14)
```

## Accept no date

Declare the field with `allow_null=True` and a client may send `null`. The validated value is
`None`. Without it, Django REST framework reports its own `null` error. A form posted to the API
with an empty entry gives `None` on a field that allows `null`, as it does on any other field.

```python
>>> serializer = SampleModelSerializer(data={"collected": None})
>>> serializer.is_valid()
True
>>> serializer.validated_data["collected"] is None
True
>>> serializer = SampleSerializer(data={"collected": None})
>>> serializer.is_valid()
False
>>> serializer.errors["collected"][0].code
'null'
```

## Handle a refused entry

An entry that is not a partial date is reported as an error on the field, with the code
`invalid`, and nothing is written. That covers text such as `1990-6` or `1990-02-30`, an empty
string, the number `1990`, a list, an object and `true`.

```python
>>> for entry in ["1990-6", "1990-02-30", "", 1990, [], {}, True]:
...     serializer = SampleSerializer(data={"collected": entry})
...     print(serializer.is_valid(), serializer.errors["collected"][0].code)
False invalid
False invalid
False invalid
False invalid
False invalid
False invalid
False invalid
```

## Require a date

A required date should declare this field. Without it, a `ModelSerializer` falls back to a field
that passes an empty string through to the database, which refuses it with a database error. With
it, the client gets a validation error and nothing is written.

```python
>>> class EventSerializer(serializers.ModelSerializer):
...     occurred = PartialDateField()
...
...     class Meta:
...         model = Event
...         fields = ["occurred"]
>>> serializer = EventSerializer(data={"occurred": ""})
>>> serializer.is_valid()
False
>>> serializer.errors["occurred"][0].code
'invalid'
>>> Event.objects.count()
0
```

To use the field on every serializer in your project, name it in your own
`serializer_field_mapping`, and derive your serializers from that class.

```python
>>> import partial_dates
>>> class ProjectModelSerializer(serializers.ModelSerializer):
...     serializer_field_mapping = {
...         **serializers.ModelSerializer.serializer_field_mapping,
...         partial_dates.PartialDateField: PartialDateField,
...     }
>>> class MappedEventSerializer(ProjectModelSerializer):
...     class Meta:
...         model = Event
...         fields = ["occurred"]
>>> serializer = MappedEventSerializer(data={"occurred": ""})
>>> serializer.is_valid()
False
>>> serializer.errors["occurred"][0].code
'invalid'
```

## Leave a ModelSerializer alone

A `ModelSerializer` that declares nothing needs no change for a date that may be empty. Django
REST framework's fallback reads and writes the same ISO form as this field.

```python
>>> class FallbackSerializer(serializers.ModelSerializer):
...     class Meta:
...         model = Sample
...         fields = ["collected"]
>>> serializer = FallbackSerializer(data={"collected": "1990-06"})
>>> serializer.is_valid()
True
>>> FallbackSerializer(serializer.save()).data["collected"]
'1990-06'
```

## Why an empty string is refused

The model field stores `""` as no date, which suits a form. On an API the wire format is the ISO
form or `null`, and Django REST framework's own `DateField` refuses `""` in the same way.
Accepting it would hand a required date the empty string, and the database would refuse it
instead of the serializer. A client that has no date sends `null`.

To filter a list of records by a partial date or a range of dates, use the filters in the
[filtering guide](filtering.md), which also covers django-filter's filter backend.
