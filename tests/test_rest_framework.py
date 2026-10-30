from types import SimpleNamespace

import pytest
from rest_framework import serializers

from partial_dates.partial_date import PartialDate
from partial_dates.rest_framework import PartialDateField
from tests.models import Sample


class PlainSerializer(serializers.Serializer):
    collected = PartialDateField()


class TestReading:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (PartialDate(1990), "1990"),
            (PartialDate(1990, 6), "1990-06"),
            (PartialDate(1990, 6, 14), "1990-06-14"),
        ],
    )
    def test_each_precision_reads_as_its_iso_form(self, value, expected):
        data = PlainSerializer(SimpleNamespace(collected=value)).data

        assert data["collected"] == expected

    def test_no_date_reads_as_null(self):
        data = PlainSerializer(SimpleNamespace(collected=None)).data

        assert data["collected"] is None

    @pytest.mark.parametrize("text", ["1990", "1990-06", "1990-06-14"])
    def test_an_object_holding_iso_text_reads_as_that_form(self, text):
        data = PlainSerializer(Sample(collected=text)).data

        assert data["collected"] == text
