from django.db import migrations

import partial_dates.fields
import tests.moving.fields
from partial_dates.conversion import ConvertPartialDateField


class Migration(migrations.Migration):
    dependencies = [("moving", "0003_add_note")]

    operations = [
        ConvertPartialDateField(
            model_name="sighting",
            name="observed",
            field=partial_dates.fields.PartialDateField(
                blank=True,
                db_column="seen_on",
                db_index=True,
                help_text="When the animal was observed.",
                null=True,
                verbose_name="observed",
            ),
        ),
        ConvertPartialDateField(
            model_name="survey",
            name="taken",
            field=tests.moving.fields.ProjectDateField(
                help_text="When the survey was taken.", verbose_name="taken"
            ),
        ),
    ]
