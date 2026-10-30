"""The forms of the example app."""

from django import forms

from partial_dates.forms import PartialDateField
from samples.models import Sample


class SampleForm(forms.ModelForm):
    """A model form that declares nothing about the partial date fields."""

    class Meta:
        model = Sample
        fields = ["collected", "published", "catalogued"]


class PlainForm(forms.Form):
    """A form with no model, declaring the form field itself."""

    when = PartialDateField(required=False, help_text="Leave it empty for no date.")
