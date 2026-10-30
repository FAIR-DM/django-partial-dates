"""Moving a column from django-partial-date to a `PartialDateField`."""

from typing import Any, cast

from django.db import migrations, models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.utils import truncate_name
from django.db.migrations.state import ProjectState

FORWARD = (
    "CASE SUBSTR({t}, 19, 1) WHEN '0' THEN SUBSTR({t}, 1, 4) "
    "WHEN '1' THEN SUBSTR({t}, 1, 7) ELSE SUBSTR({t}, 1, 10) END"
)


class OldPartialDateField(models.Field):
    """A field describing the column django-partial-date created.

    Historical migrations point at this field instead of the old package's, so a
    project can uninstall that package while every database keeps the schema its
    migrations describe. It writes values through unchanged. Pass it any option of
    `django.db.models.Field`; it takes no `max_length`.
    """

    def get_internal_type(self) -> str:
        """Return the type family Django compares when it alters the column.

        Returns:
            `"CharField"`, which is deliberately not the type of the column.
        """
        # Django picks an alteration's USING clause by comparing these families. Naming
        # the text family stops an AlterField to PartialDateField casting the old
        # timestamps to varchar(10), which would truncate them silently (FS-005).
        return "CharField"

    def db_type(self, connection: BaseDatabaseWrapper) -> str | None:
        """Return the type of the old column.

        Args:
            connection: The database the column is created on.

        Returns:
            The timestamp type of the database.
        """
        return connection.data_types["DateTimeField"]

    def db_check(self, connection: BaseDatabaseWrapper) -> None:
        """Return no check, because the old column had none.

        Args:
            connection: The database the column is created on.

        Returns:
            `None`.
        """
        return None


class ConvertPartialDateField(migrations.AlterField):
    """Change a django-partial-date column to a `PartialDateField` in place.

    It takes the arguments of `django.db.migrations.AlterField`, so the only edit to
    a generated migration is the operation's name.
    """

    def database_forwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> None:
        """Convert the column, keeping every value.

        Args:
            app_label: The label of the app the model belongs to.
            schema_editor: The editor of the database being migrated.
            from_state: The state holding the old field.
            to_state: The state holding the new field.
        """
        from_model = from_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, from_model):
            return
        to_model = to_state.apps.get_model(app_label, self.model_name)
        old = from_model._meta.get_field(self.name)
        new = to_model._meta.get_field(self.name)
        if schema_editor.connection.vendor == "postgresql":
            self.convert_postgresql(schema_editor, from_model, old, new)
        else:
            self.convert_sqlite(schema_editor, from_model, old, new)

    def convert_postgresql(
        self,
        schema_editor: BaseDatabaseSchemaEditor,
        model: type[models.Model],
        old: models.Field,
        new: models.Field,
    ) -> None:
        """Convert the column with one `ALTER TABLE` between two index changes.

        Args:
            schema_editor: The editor of the database being migrated.
            model: The model, in the state holding the old field.
            old: The old field.
            new: The new field.
        """
        connection = schema_editor.connection
        quote = connection.ops.quote_name
        table = model._meta.db_table
        column_name = old.db_column or old.attname
        column = quote(column_name)
        parameters = new.db_parameters(connection)
        name = truncate_name(
            f"{table}_{column_name}_check", connection.ops.max_name_length()
        )
        unindexed_old = self.without_indexes(old)
        unindexed_new = self.without_indexes(new, null=old.null)
        schema_editor.alter_field(model, old, unindexed_old)
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} ALTER COLUMN {column} "
            f"TYPE {parameters['type']} COLLATE {quote(cast(str, parameters['collation']))} "
            f"USING {FORWARD.format(t=f'{column}::timestamp::text')}, "
            f"ADD CONSTRAINT {quote(name)} CHECK ({new.db_check(connection)})",
            None,
        )
        schema_editor.alter_field(model, unindexed_new, new)

    def convert_sqlite(
        self,
        schema_editor: BaseDatabaseSchemaEditor,
        model: type[models.Model],
        old: models.Field,
        new: models.Field,
    ) -> None:
        """Convert the column through a plain text column, rebuilding the table twice.

        Args:
            schema_editor: The editor of the database being migrated.
            model: The model, in the state holding the old field.
            old: The old field.
            new: The new field.
        """
        quote = schema_editor.connection.ops.quote_name
        column = quote(old.db_column or old.attname)
        plain = self.plain_text_field(old)
        schema_editor.alter_field(model, old, plain)
        schema_editor.execute(
            f"UPDATE {quote(model._meta.db_table)} "  # noqa: S608
            f"SET {column} = {FORWARD.format(t=column)}",  # names are quoted
            None,
        )
        schema_editor.alter_field(model, plain, new)

    def without_indexes(self, field: models.Field, **options: Any) -> models.Field:
        """Clone a field with no index and no unique constraint of its own.

        Args:
            field: The field to clone.
            **options: Options of the clone that replace the field's.

        Returns:
            A field of the same class and column, attached to the same model.
        """
        _, _, args, kwargs = field.deconstruct()
        kwargs.pop("db_index", None)
        kwargs.pop("unique", None)
        return self.attached(field, field.__class__(*args, **{**kwargs, **options}))

    def plain_text_field(self, field: models.Field) -> models.Field:
        """Build the text column the rows are rewritten in, with no check.

        Args:
            field: The old field.

        Returns:
            A `CharField` of ten characters with the old field's nullability.
        """
        return self.attached(
            field,
            models.CharField(max_length=10, null=field.null, db_column=field.db_column),
        )

    @staticmethod
    def attached(field: models.Field, clone: models.Field) -> models.Field:
        """Give a clone the name and model of the field it stands in for.

        Args:
            field: The field being cloned.
            clone: The clone.

        Returns:
            The clone.
        """
        clone.set_attributes_from_name(field.name)
        clone.model = field.model
        return clone
