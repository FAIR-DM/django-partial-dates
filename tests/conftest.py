import pytest

from tests.factories import EventFactory, RecordFactory, SampleFactory


@pytest.fixture
def record(db):
    return RecordFactory()


@pytest.fixture
def event(db):
    return EventFactory()


@pytest.fixture
def sample(db):
    return SampleFactory()


@pytest.fixture
def grid(db):
    """Rows at each precision around the bound 1990-06, then a row holding no date."""
    texts = [
        "1990",
        "1990-05",
        "1990-05-31",
        "1990-06",
        "1990-06-01",
        "1990-06-14",
        "1990-07",
        "1991",
        None,
    ]
    return [SampleFactory(collected=text) for text in texts]


@pytest.fixture
def found():
    """Return the ISO forms a queryset of samples holds, in the order of the rows."""

    def texts(queryset):
        return [
            None if sample.collected is None else str(sample.collected)
            for sample in queryset.order_by("pk")
        ]

    return texts
