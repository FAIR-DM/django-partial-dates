import pytest
from django.db import connection

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


@pytest.fixture
def query_plan(db):
    """Return the database's plan for a queryset, as text.

    On PostgreSQL it first forbids a sequential scan inside the test's transaction, so
    a small table cannot hide a filter that has no index path.
    """

    def plan(queryset):
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL enable_seqscan = off")
        return queryset.explain()

    return plan


@pytest.fixture
def guide_samples(db):
    """The rows the developer guide's examples run against."""
    texts = [
        "1990",
        "1990-05",
        "1990-05-31",
        "1990-06",
        "1990-06-01",
        "1990-06-14",
        "1990-07",
        "1990-12",
        "1991",
        "1991-03",
        "1991-03-15",
        "1991-04",
        "1991-06",
        "1991-06-02",
        None,
    ]
    return [SampleFactory(collected=text) for text in texts]
