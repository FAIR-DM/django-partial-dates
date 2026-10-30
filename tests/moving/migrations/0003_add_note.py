from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("moving", "0002_rename_and_alter")]

    operations = [
        migrations.AddField(
            model_name="sighting",
            name="note",
            field=models.CharField(blank=True, db_default="", max_length=20),
        ),
        migrations.AddField(
            model_name="survey",
            name="note",
            field=models.CharField(blank=True, db_default="", max_length=20),
        ),
    ]
