import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.http import QueryDict
from rest_framework import serializers

from partial_dates.partial_date import PartialDate
from partial_dates.rest_framework import PartialDateField
from tests.models import Event, Note, Record, Sample


class PlainSerializer(serializers.Serializer):
    collected = PartialDateField()


class TestReading:
    def test_an_object_holding_empty_text_reads_as_no_date(self):
        data = PlainSerializer(SimpleNamespace(collected="")).data

        assert data["collected"] is None

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
    def test_an_iso_form_or_a_partial_date_validates_to_the_value(self, data, expected):
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


def before_1900(value):
    if value.year < 1900:
        raise serializers.ValidationError("Too early.", code="too_early")


class TestOptions:
    def test_required_reports_a_missing_entry(self):
        serializer = PlainSerializer(data={})

        assert not serializer.is_valid()
        assert serializer.errors["collected"][0].code == "required"

    def test_not_required_accepts_a_missing_entry(self):
        class OptionalSerializer(serializers.Serializer):
            collected = PartialDateField(required=False)

        serializer = OptionalSerializer(data={})

        assert serializer.is_valid()
        assert "collected" not in serializer.validated_data

    def test_read_only_reads_and_ignores_incoming_data(self):
        class ReadOnlySerializer(serializers.Serializer):
            collected = PartialDateField(read_only=True)

        read = ReadOnlySerializer(SimpleNamespace(collected=PartialDate(1990))).data
        written = ReadOnlySerializer(data={"collected": "1991"})

        assert read["collected"] == "1990"
        assert written.is_valid()
        assert written.validated_data == {}

    def test_source_reads_across_a_relation(self):
        class NoteSerializer(serializers.Serializer):
            recorded = PartialDateField(source="record.date")

        note = Note(record=Record(date="1990-06"))

        assert NoteSerializer(note).data["recorded"] == "1990-06"

    def test_source_writes_across_a_relation(self):
        class NoteSerializer(serializers.Serializer):
            recorded = PartialDateField(source="record.date")

        serializer = NoteSerializer(data={"recorded": "1990-06"})

        assert serializer.is_valid()
        assert serializer.validated_data == {"record": {"date": PartialDate(1990, 6)}}

    def test_a_validator_runs_on_the_value_and_reports_its_own_code(self):
        class CheckedSerializer(serializers.Serializer):
            collected = PartialDateField(validators=[before_1900])

        serializer = CheckedSerializer(data={"collected": "1850"})

        assert not serializer.is_valid()
        assert serializer.errors["collected"][0].code == "too_early"

    def test_a_validator_accepts_a_value_it_allows(self):
        class CheckedSerializer(serializers.Serializer):
            collected = PartialDateField(validators=[before_1900])

        serializer = CheckedSerializer(data={"collected": "1990"})

        assert serializer.is_valid()

    def test_an_empty_html_entry_is_none_when_the_field_allows_null(self):
        serializer = NullableSerializer(data=QueryDict("collected="))

        assert serializer.is_valid()
        assert serializer.validated_data["collected"] is None

    def test_an_empty_html_entry_is_refused_when_the_field_does_not_allow_null(self):
        serializer = PlainSerializer(data=QueryDict("collected="))

        assert not serializer.is_valid()


class FallbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sample
        fields = ["collected"]


class TestModelSerializer:
    @pytest.mark.django_db
    @pytest.mark.parametrize("text", ["1990", "1990-06", "1990-06-14"])
    @pytest.mark.parametrize("serializer_class", [FallbackSerializer, SampleSerializer])
    def test_a_write_then_a_read_gives_the_iso_form(self, serializer_class, text):
        written = serializer_class(data={"collected": text})
        assert written.is_valid()
        saved = written.save()
        saved.refresh_from_db()

        assert serializer_class(saved).data["collected"] == text

    @pytest.mark.django_db
    def test_with_nothing_declared_a_read_matches_the_declared_field(self):
        sample = Sample.objects.create(collected="1990-06")

        assert FallbackSerializer(sample).data == SampleSerializer(sample).data


SOURCE = """
import sys

sys.modules["django_filters"] = None
import django

django.setup()
from rest_framework import serializers

from partial_dates import PartialDate
from partial_dates.rest_framework import PartialDateField


class Plain(serializers.Serializer):
    collected = PartialDateField()


plain = Plain(data={"collected": "1990-06"})
assert plain.is_valid()
assert plain.validated_data["collected"] == PartialDate(1990, 6)
"""


class TestWithoutDjangoFilter:
    def test_a_fresh_interpreter_with_it_blocked_validates_a_value(self):
        env = {**os.environ, "DJANGO_SETTINGS_MODULE": "tests.settings"}
        root = Path(__file__).parent.parent

        result = subprocess.run(
            [sys.executable, "-c", SOURCE],
            env=env,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
