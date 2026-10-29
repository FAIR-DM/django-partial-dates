import pytest

from tests.factories import EventFactory, RecordFactory


@pytest.fixture
def record(db):
    return RecordFactory()


@pytest.fixture
def event(db):
    return EventFactory()
