"""The pages of the example app."""

from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, ListView, UpdateView

from samples.forms import PlainForm, SampleForm
from samples.models import Sample


class SampleList(ListView):
    """List the samples."""

    model = Sample


class SampleCreate(CreateView):
    """Add a sample with a model form."""

    form_class = SampleForm
    template_name = "samples/sample_form.html"
    success_url = reverse_lazy("sample-list")


class SampleUpdate(UpdateView):
    """Change a sample with a model form."""

    model = Sample
    form_class = SampleForm
    template_name = "samples/sample_form.html"
    success_url = reverse_lazy("sample-list")


class PlainFormView(FormView):
    """Show what a form with no model cleaned the entry to."""

    form_class = PlainForm
    template_name = "samples/plain_form.html"

    def form_valid(self, form: PlainForm) -> HttpResponse:
        """Show the cleaned value on the same page.

        Args:
            form: The form that was submitted and cleaned.

        Returns:
            The page, with the cleaned value in its context.
        """
        return self.render_to_response(self.get_context_data(form=form, cleaned=True))
