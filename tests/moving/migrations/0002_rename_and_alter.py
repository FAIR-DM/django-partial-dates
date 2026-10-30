from django.db import migrations

import partial_dates.conversion


class Migration(migrations.Migration):
    dependencies = [("moving", "0001_initial")]

    operations = [
        migrations.RenameField(
            model_name="sighting", old_name="seen", new_name="observed"
        ),
        migrations.AlterField(
            model_name="sighting",
            name="observed",
            field=partial_dates.conversion.OldPartialDateField(
                blank=True,
                db_column="seen_on",
                db_index=True,
                help_text="When the animal was observed.",
                null=True,
                verbose_name="observed",
            ),
        ),
    ]
