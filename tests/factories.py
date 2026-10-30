import factory

from tests.models import Event, Record


class RecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Record


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    occurred = factory.Sequence(lambda n: f"{n + 1:04d}")
