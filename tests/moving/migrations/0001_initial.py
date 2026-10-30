from django.db import migrations, models

import partial_dates.conversion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Sighting",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "seen",
                    partial_dates.conversion.OldPartialDateField(
                        blank=True,
                        db_column="seen_on",
                        db_index=True,
                        help_text="When it was seen.",
                        null=True,
                        verbose_name="seen",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Survey",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "taken",
                    partial_dates.conversion.OldPartialDateField(
                        help_text="When the survey was taken.", verbose_name="taken"
                    ),
                ),
            ],
            options={"abstract": False},
        ),
    ]
