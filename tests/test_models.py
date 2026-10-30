import pytest
from django.apps import apps

TEST_MODEL_FIELDS = [
    pytest.param(field, id=f"{model.__name__}.{field.name}")
    for model in apps.get_app_config("tests").get_models()
    for field in model._meta.get_fields()
    if not field.auto_created
]


class TestTestModels:
    def test_the_test_app_defines_models(self):
        assert TEST_MODEL_FIELDS

    @pytest.mark.parametrize("field", TEST_MODEL_FIELDS)
    def test_every_field_has_a_verbose_name_and_help_text(self, field):
        assert str(field.verbose_name)
        assert str(field.help_text)
