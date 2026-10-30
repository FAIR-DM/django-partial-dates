import pytest

from tests.factories import EventFactory, RecordFactory
from tests.models import Event, Record


@pytest.mark.django_db
class TestRecordFactory:
    def test_it_saves_a_record(self):
        record = RecordFactory()

        assert Record.objects.filter(pk=record.pk).exists()

    def test_the_fixture_wraps_the_factory(self, record):
        assert Record.objects.filter(pk=record.pk).exists()


@pytest.mark.django_db
class TestEventFactory:
    def test_it_saves_an_event(self):
        event = EventFactory()

        assert Event.objects.filter(pk=event.pk).exists()

    def test_each_event_occurs_on_a_distinct_date(self):
        events = EventFactory.create_batch(3)

        assert len({event.occurred for event in events}) == 3

    def test_the_fixture_wraps_the_factory(self, event):
        assert Event.objects.filter(pk=event.pk).exists()
