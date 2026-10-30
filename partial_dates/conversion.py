"""Moving a column from django-partial-date to a `PartialDateField`."""

import re
from collections.abc import Iterator
from typing import Any, cast

from django.db import NotSupportedError, migrations, models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.utils import truncate_name
from django.db.migrations.state import ProjectState

from partial_dates.partial_date import PartialDate

FORWARD = (
    "CASE SUBSTR({t}, 19, 1) WHEN '0' THEN SUBSTR({t}, 1, 4) "
    "WHEN '1' THEN SUBSTR({t}, 1, 7) ELSE SUBSTR({t}, 1, 10) END"
)
STORED = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2}) 00:00:0([012])")
SHOWN = 20
BATCH = 1000
BACKWARD = (
    "CASE LENGTH({c}) WHEN 4 THEN {c} || '-01-01 00:00:00' "
    "WHEN 7 THEN {c} || '-01 00:00:01' ELSE {c} || ' 00:00:02' END"
)


class RefusedValuesError(Exception):
    """Values in an old column that cannot be converted, so nothing was changed.

    Args:
        model: The label of the model, such as `"sightings.Sighting"`.
        field: The name of the field.
        count: The number of refused values in the column.
        rows: The primary key and stored value of the first refused values, lowest
            primary key first.

    Attributes:
        model: The label of the model, such as `"sightings.Sighting"`.
        field: The name of the field.
        count: The number of refused values in the column.
        rows: The primary key and stored value of the first 20 refused values, lowest
            primary key first.
    """

    def __init__(
        self, model: str, field: str, count: int, rows: list[tuple[Any, str]]
    ) -> None:
        super().__init__(model, field, count, rows)
        self.model = model
        self.field = field
        self.count = count
        self.rows = rows


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

    def describe(self) -> str:
        """Describe the operation for `sqlmigrate` and the migration's summary.

        Returns:
            A sentence naming the field and the conversion.
        """
        return (
            f"Convert field {self.name} on {self.model_name} from django-partial-date"
        )

    @property
    def migration_name_fragment(self) -> str:
        """Name the part of a generated migration's file this operation adds.

        Returns:
            The fragment, made of the model's and the field's names.
        """
        return f"convert_{self.model_name_lower}_{self.name_lower}"

    def reduce(
        self, operation: migrations.operations.base.Operation, app_label: str
    ) -> bool:
        """Stop the optimiser folding a later operation into the conversion.

        Args:
            operation: The operation after this one.
            app_label: The label of the app the migration belongs to.

        Returns:
            `False`, so a squashed migration keeps the conversion.
        """
        return False

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
        self.check_vendor(schema_editor)
        if not schema_editor.collect_sql:
            self.refuse(schema_editor, from_model, old)
        if schema_editor.connection.vendor == "postgresql":
            self.convert_postgresql(schema_editor, from_model, old, new)
        else:
            self.convert_sqlite(schema_editor, from_model, old, new)

    def database_backwards(
        self,
        app_label: str,
        schema_editor: BaseDatabaseSchemaEditor,
        from_state: ProjectState,
        to_state: ProjectState,
    ) -> None:
        """Restore the old column and the timestamp each value was converted from.

        Args:
            app_label: The label of the app the model belongs to.
            schema_editor: The editor of the database being migrated.
            from_state: The state holding the new field.
            to_state: The state holding the old field.
        """
        from_model = from_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, from_model):
            return
        to_model = to_state.apps.get_model(app_label, self.model_name)
        new = from_model._meta.get_field(self.name)
        old = to_model._meta.get_field(self.name)
        self.check_vendor(schema_editor)
        if schema_editor.connection.vendor == "postgresql":
            self.restore_postgresql(schema_editor, from_model, old, new)
        else:
            self.restore_sqlite(schema_editor, from_model, old, new)

    def check_vendor(self, schema_editor: BaseDatabaseSchemaEditor) -> None:
        """Refuse a database other than PostgreSQL and SQLite.

        Args:
            schema_editor: The editor of the database being migrated.

        Raises:
            NotSupportedError: The database is neither PostgreSQL nor SQLite.
        """
        vendor = schema_editor.connection.vendor
        if vendor not in ("postgresql", "sqlite"):
            raise NotSupportedError(
                f"Converting a django-partial-date column needs PostgreSQL or "
                f"SQLite, not {vendor}."
            )

    def refuse(
        self,
        schema_editor: BaseDatabaseSchemaEditor,
        model: type[models.Model],
        old: models.Field,
    ) -> None:
        """Stop the migration if any value in the column cannot be converted.

        Args:
            schema_editor: The editor of the database being migrated.
            model: The model, in the state holding the old field.
            old: The old field.

        Raises:
            RefusedValuesError: A value is not one the old field writes.
        """
        count, rows = 0, []
        for key, stored in self.refused_values(schema_editor, model, old):
            count += 1
            if count <= SHOWN:
                rows.append((key, stored))
        if count:
            raise RefusedValuesError(model._meta.label, self.name, count, rows)

    def refused_values(
        self,
        schema_editor: BaseDatabaseSchemaEditor,
        model: type[models.Model],
        old: models.Field,
    ) -> Iterator[tuple[Any, str]]:
        """Read the column as stored and yield each value that cannot be converted.

        Args:
            schema_editor: The editor of the database being migrated.
            model: The model, in the state holding the old field.
            old: The old field.

        Yields:
            The primary key and stored text of each refused value, in primary key
            order. A `NULL` is never refused.
        """
        connection = schema_editor.connection
        quote = connection.ops.quote_name
        column = quote(old.db_column or old.attname)
        stored = (
            f"{column}::timestamp::text"
            if connection.vendor == "postgresql"
            else f"CAST({column} AS TEXT)"
        )
        key = quote(cast(str, model._meta.pk.column))
        table = quote(model._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {key}, {stored} FROM {table} "  # noqa: S608
                f"WHERE {column} IS NOT NULL ORDER BY {key}"
            )
            while batch := cursor.fetchmany(BATCH):
                for pk, text in batch:
                    if not self.converts(text):
                        yield pk, text

    @staticmethod
    def converts(text: str) -> bool:
        """Say whether a stored timestamp is exactly what the old field writes.

        Args:
            text: The stored timestamp as text.

        Returns:
            `True` when the time is 00:00:00, 00:00:01 or 00:00:02, the date exists
            in the years 1 to 9999, and the time agrees with the date's precision.
        """
        match = STORED.fullmatch(text)
        if match is None:
            return False
        year, month, day, precision = (int(part) for part in match.groups())
        if precision == 0 and (month, day) != (1, 1):
            return False
        if precision == 1 and day != 1:
            return False
        try:
            PartialDate(year, month, day)
        except ValueError:
            return False
        return True

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
        collation = quote(cast(str, parameters["collation"]))
        name = self.check_name(connection, table, column_name)
        unindexed_old = self.without_indexes(old)
        unindexed_new = self.without_indexes(new, null=old.null)
        schema_editor.alter_field(model, old, unindexed_old)
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} ALTER COLUMN {column} "
            f"TYPE {parameters['type']} COLLATE {collation} "
            f"USING {FORWARD.format(t=f'{column}::timestamp::text')}, "
            f"ADD CONSTRAINT {quote(name)} CHECK ({new.db_check(connection)})",
            None,
        )
        schema_editor.alter_field(model, unindexed_new, new)

    def restore_postgresql(
        self,
        schema_editor: BaseDatabaseSchemaEditor,
        model: type[models.Model],
        old: models.Field,
        new: models.Field,
    ) -> None:
        """Restore the column with one `ALTER TABLE` between two index changes.

        Args:
            schema_editor: The editor of the database being migrated.
            model: The model, in the state holding the new field.
            old: The old field.
            new: The new field.
        """
        connection = schema_editor.connection
        quote = connection.ops.quote_name
        table = model._meta.db_table
        column_name = new.db_column or new.attname
        column = quote(column_name)
        kind = old.db_parameters(connection)["type"]
        name = self.check_name(connection, table, column_name)
        unindexed_new = self.without_indexes(new)
        unindexed_old = self.without_indexes(old, null=new.null)
        schema_editor.alter_field(model, new, unindexed_new)
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} DROP CONSTRAINT {quote(name)}, "
            f"ALTER COLUMN {column} TYPE {kind} "
            f"USING ({BACKWARD.format(c=column)})::{kind}",
            None,
        )
        schema_editor.alter_field(model, unindexed_old, old)

    def restore_sqlite(
        self,
        schema_editor: BaseDatabaseSchemaEditor,
        model: type[models.Model],
        old: models.Field,
        new: models.Field,
    ) -> None:
        """Restore the column through a plain text column, rebuilding the table.

        Args:
            schema_editor: The editor of the database being migrated.
            model: The model, in the state holding the new field.
            old: The old field.
            new: The new field.
        """
        quote = schema_editor.connection.ops.quote_name
        column = quote(new.db_column or new.attname)
        plain = self.plain_text_field(new)
        unindexed_old = self.without_indexes(old, null=new.null)
        schema_editor.alter_field(model, new, plain)
        schema_editor.execute(
            f"UPDATE {quote(model._meta.db_table)} "  # noqa: S608
            f"SET {column} = {BACKWARD.format(c=column)}",  # names are quoted
            None,
        )
        schema_editor.alter_field(model, plain, unindexed_old)
        schema_editor.alter_field(model, unindexed_old, old)

    @staticmethod
    def check_name(connection: BaseDatabaseWrapper, table: str, column: str) -> str:
        """Name the check constraint the conversion adds to a column.

        Args:
            connection: The database being migrated.
            table: The table holding the column.
            column: The name of the column.

        Returns:
            The name, cut to the length the database allows.
        """
        return truncate_name(
            f"{table}_{column}_check", connection.ops.max_name_length()
        )

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
            field: The field whose column is rewritten.

        Returns:
            A `CharField` of ten characters with the field's nullability.
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
