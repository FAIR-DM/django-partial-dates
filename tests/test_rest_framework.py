from types import SimpleNamespace

import pytest
from rest_framework import serializers

from partial_dates.partial_date import PartialDate
from partial_dates.rest_framework import PartialDateField
from tests.models import Event, Sample


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


class SampleSerializer(serializers.ModelSerializer):
    collected = PartialDateField()

    class Meta:
        model = Sample
        fields = ["collected"]


class NullableSerializer(serializers.Serializer):
    collected = PartialDateField(allow_null=True)


class EventSerializer(serializers.ModelSerializer):
    occurred = PartialDateField()

    class Meta:
        model = Event
        fields = ["occurred"]


class TestWriting:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            ("1990", PartialDate(1990)),
            ("1990-06", PartialDate(1990, 6)),
            ("1990-06-14", PartialDate(1990, 6, 14)),
            (PartialDate(1990, 6), PartialDate(1990, 6)),
        ],
    )
    def test_an_iso_form_or_a_partial_date_validates_to_the_value(
        self, data, expected
    ):
        serializer = PlainSerializer(data={"collected": data})

        assert serializer.is_valid()
        assert serializer.validated_data["collected"] == expected

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("1990", PartialDate(1990)),
            ("1990-06", PartialDate(1990, 6)),
            ("1990-06-14", PartialDate(1990, 6, 14)),
        ],
    )
    def test_a_model_serializer_saves_the_value(self, text, expected):
        serializer = SampleSerializer(data={"collected": text})

        assert serializer.is_valid()
        saved = serializer.save()
        saved.refresh_from_db()
        assert saved.collected == expected

    def test_null_validates_to_none_when_the_field_allows_it(self):
        serializer = NullableSerializer(data={"collected": None})

        assert serializer.is_valid()
        assert serializer.validated_data["collected"] is None

    def test_null_is_refused_when_the_field_does_not_allow_it(self):
        serializer = PlainSerializer(data={"collected": None})

        assert not serializer.is_valid()
        assert serializer.errors["collected"][0].code == "null"

    @pytest.mark.parametrize(
        "data",
        ["1990-6", "1990-02-30", "", 1990, [], {}, True, "1990\x00", "9" * 200],
    )
    def test_anything_else_is_refused_with_the_code_invalid(self, data):
        serializer = PlainSerializer(data={"collected": data})

        assert not serializer.is_valid()
        assert [error.code for error in serializer.errors["collected"]] == ["invalid"]

    @pytest.mark.django_db
    def test_an_empty_string_for_a_required_date_writes_nothing(self):
        serializer = EventSerializer(data={"occurred": ""})

        assert not serializer.is_valid()
        assert serializer.errors["occurred"][0].code == "invalid"
        assert Event.objects.count() == 0
