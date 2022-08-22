from base64 import b64encode, b64decode
from typing import Union, List
from uuid import uuid4

from .data_type import DataType
from .modifier import Modifier
from .queue_db import QueueDB

STRING_ENCODING = "utf-8"


def to_b64(data):
    return b64encode(data.encode(STRING_ENCODING)).hex() if type(data) == str else data


def from_b64(hex_str: str):
    return b64decode(bytes.fromhex(hex_str)).decode(STRING_ENCODING)


class RawDB:
    def __init__(self, path: str):
        self.path = path

        self._queue_db = QueueDB(path)
        self._queue_db.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.commit()
        self.close_connection()

    def _fetch(self, query: str):
        return self._queue_db.fetch(query)

    def _get_column_names(self, table_name: str):
        return [info[1] for info in self._fetch(f"PRAGMA table_info('{table_name}')")]

    def _column_exists(self, table_name: str, column_name: str):
        return column_name in self._get_column_names(table_name)

    def _add_column(self, table_name: str, column_name: str, data_type: DataType, modifiers: List[Modifier],
                    default_value):
        modifier_string = " ".join([modifier.value for modifier in modifiers])
        default_value = default_value if type(default_value) != str else f"'{default_value}'"

        self._queue_db.execute(
            f"ALTER TABLE '{table_name}' ADD COLUMN {column_name} {data_type.value} {modifier_string}" + (
                f" DEFAULT {default_value}" if default_value is not None else ""))

    def table_exists(self, table_name: str):
        table_names = self._fetch(f"SELECT true FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        return len(table_names) > 0

    def rename_table(self, current_table_name: str, new_table_name):
        assert self.table_exists(current_table_name), "Table does not exist"

        self._queue_db.execute(f"ALTER TABLE {current_table_name} RENAME TO {new_table_name}")

    def create_table(self, table_name: str, shape: dict):
        assert self.table_exists(table_name) is False, "Table already exists"

        headers = []

        for column_name, (data_type, modifiers) in shape.items():
            assert hasattr(data_type, "value"), "Invalid data type"
            assert all([hasattr(modifier, "value") for modifier in modifiers]), "Invalid modifiers"

            data_type_name = data_type.value
            modifier_names = [modifier.value for modifier in modifiers]

            headers.append(f"{column_name} {data_type_name} {' '.join(modifier_names)}")

        self._queue_db.execute(f"CREATE TABLE {table_name} ({', '.join(headers)})")

    def delete_table(self, table_name: str):
        assert self.table_exists(table_name), "Table does not exist"

        self._queue_db.execute(f"DROP TABLE '{table_name}'")

    def set(self, table_name: str, conditions: dict = None, data: dict = None):
        assert self.table_exists(table_name), "Table does not exist"
        conditions = conditions or {}
        data = data or {}

        if len(conditions) > 0 and self.has(table_name, conditions):
            set_string = ", ".join([f"{k}=" + (f"'{v}'" if type(v) == str else str(v)) for k, v in data.items()])
            condition_string = " AND ".join(
                f"{k}=" + (f"'{v}'" if type(v) == str else str(v)) for k, v in conditions.items())

            self._queue_db.execute(f"UPDATE {table_name}  SET {set_string} WHERE {condition_string}")

        else:
            keys_string = ", ".join(data.keys())
            values_string = ", ".join(
                [f"'{value}'" if type(value) == str else str(value) for value in data.values()])

            self._queue_db.execute(f"INSERT INTO {table_name} ({keys_string}) VALUES ({values_string})")

    def get(self, table_name: str, conditions: dict, columns: Union[List[str], str] = None):
        assert self.table_exists(table_name), "Table does not exist"

        columns = columns or "*"

        if columns != "*":
            assert all([self._column_exists(table_name, column) for column in columns]), "Invalid column name"
            column_string = ", ".join(columns)

        else:
            column_string = columns

        condition_string = " AND ".join(
            [f"{k}=" + f"'{v}'" if type(v) == str else str(v) for k, v in conditions.items()])

        res = self._fetch(f"SELECT {column_string} FROM {table_name} WHERE {condition_string}")
        column_names = self._get_column_names(table_name)

        return [{k: v for k, v in zip(columns if columns != "*" else column_names, data) if
                 k in columns or columns == "*"} for data in res]

    def remove(self, table_name: str, conditions: dict):
        assert self.table_exists(table_name), "Table does not exist"
        assert self.has(table_name, conditions), "Row does not exist"

        condition_string = " AND ".join(
            [f"{k}=" + f"'{v}'" if type(v) == str else str(v) for k, v in conditions.items()])

        self._queue_db.execute(f"DELETE FROM {table_name} WHERE {condition_string}")

    def has(self, table_name: str, conditions: dict):
        assert len(conditions) > 0, "Must have some conditions"

        condition_string = " OR ".join(
            f"{k}=" + (f"'{v}'" if type(v) == str else str(v)) for k, v in conditions.items())

        rows = self._fetch(f"SELECT TRUE FROM {table_name} WHERE {condition_string}")
        return len(rows) > 0

    def alter(self, table_name: str, new_shape: dict):
        deleted_columns = [column for column, value in new_shape.items() if value is None]
        current_column_names = self._get_column_names(table_name)
        altered_columns = {k: v for k, v in new_shape.items() if k in current_column_names and v is not None}

        if len(deleted_columns) > 0 or len(altered_columns) > 0:
            # Sqlite does not support deleting column so a temporary clone is used instead
            temp_table_name = uuid4().hex

            selected_columns = [column for column in self._get_column_names(table_name) if
                                column not in deleted_columns and column not in altered_columns]
            column_string = ", ".join(selected_columns)

            self._queue_db.execute(f"CREATE TABLE '{temp_table_name}' AS SELECT {column_string} FROM {table_name}")
            for column_name, (data_type, modifiers, default_value) in altered_columns.items():
                self._add_column(temp_table_name, column_name, data_type, modifiers, default_value)

            self.commit()

            self.delete_table(table_name)
            self._queue_db.execute(f"CREATE TABLE '{table_name}' AS SELECT * FROM '{temp_table_name}'")
            self.commit()
            self.delete_table(temp_table_name)

        new_columns = [(column_name, value) for column_name, value in new_shape.items() if
                       column_name not in current_column_names and value is not None]
        for column_name, (data_type, modifiers, default_value) in new_columns:
            self._add_column(table_name, column_name, data_type, modifiers, default_value)

    def b64set(self, table_name: str, conditions: dict = None, data: dict = None):
        conditions = conditions or {}
        data = data or {}

        encoded_data = {k: to_b64(v) for k, v in data.items()}

        self.set(table_name, {k: to_b64(v) for k, v in conditions.items()}, encoded_data)

    def b64get(self, table_name: str, conditions: dict, columns: Union[List[str], str] = None):
        res = self.get(table_name, {k: to_b64(v) for k, v in conditions.items()}, columns)

        return [{k: (from_b64(v) if type(v) == str else v) for k, v in data.items()} for data in res]

    def b64remove(self, table_name: str, conditions: dict):
        self.remove(table_name, {k: to_b64(v) for k, v in conditions.items()})

    def b64has(self, table_name: str, conditions: dict):
        return self.has(table_name, {k: to_b64(v) for k, v in conditions.items()})

    def b64alter(self, table_name: str, new_shape: dict):
        encoded_shape = {}

        for k, v in new_shape.items():
            new_value = None
            if v is not None:
                new_value = [*v[:-1], to_b64(v[-1]) if v is not None else None]

            encoded_shape[k] = new_value

        self.alter(table_name, encoded_shape)

    def commit(self):
        self._queue_db.commit()

    def close_connection(self):
        self._queue_db.close_connection()
        self._queue_db.join()
