import factory

from tests.models import Event, Note, Record, Sample


class RecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Record


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    occurred = factory.Sequence(lambda n: f"{n + 1:04d}")


class SampleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sample


class NoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Note

    record = factory.SubFactory(RecordFactory)
