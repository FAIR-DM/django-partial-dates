import re

import pytest
from django.db import connection

from tests.factories import EventFactory, RecordFactory, SampleFactory

SEEK = re.compile(r"SEARCH .* USING|Index (Only )?Scan")
WALK = re.compile(r"USING (COVERING )?INDEX|Index (Only )?Scan")


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
def spread(db):
    texts = [
        "9999-12-31",
        "1990-06-14",
        "1991",
        "0001",
        "1990",
        "1990-06",
        "2000-02-29",
        "1990-06-01",
        "0990",
        None,
    ]
    return [SampleFactory(collected=text) for text in texts]


@pytest.fixture
def starts(db):
    texts = [
        "0001",
        "1990",
        "1990-01",
        "1990-01-01",
        "1990-06",
        "1990-06-01",
        "1990-06-14",
        "2000-02-29",
        "9999-12-31",
        None,
    ]
    return [SampleFactory(collected=text) for text in texts]


@pytest.fixture
def found():
    def texts(queryset, *ordering):
        return [
            None if sample.collected is None else str(sample.collected)
            for sample in queryset.order_by(*(ordering or ("pk",)))
        ]

    return texts


@pytest.fixture
def query_plan(db):
    def plan(queryset):
        if connection.vendor == "postgresql":
            # A small table would otherwise hide a query that has no index path.
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL enable_seqscan = off")
        return queryset.explain()

    return plan


@pytest.fixture
def seeks_index(query_plan):
    def check(queryset):
        return bool(SEEK.search(query_plan(queryset)))

    return check


@pytest.fixture
def walks_index(query_plan):
    def check(queryset):
        return bool(WALK.search(query_plan(queryset)))

    return check


@pytest.fixture
def guide_samples(db):
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
