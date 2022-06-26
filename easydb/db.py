from base64 import b64encode, b64decode
from sqlite3 import connect
from typing import Union, List

STRING_ENCODING = "utf-8"


def to_b64(data: any):
    return b64encode(bytes(data) if type(data) != str else data.encode(STRING_ENCODING)).hex()


def from_b64(hex_str: str):
    return b64decode(bytes.fromhex(hex_str)).decode(STRING_ENCODING)


class DB:
    def __init__(self, path: str):
        self.path = path

        self._connection = connect(path)
        self._cursor = self._connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.commit()
        self.close_connection()

    def _fetch(self, query: str):
        self._cursor.execute(query)
        return self._cursor.fetchall()

    def _get_column_names(self, table_name: str):
        return [info[1] for info in self._fetch(f"PRAGMA table_info('{table_name}')")]

    def _column_exists(self, table_name: str, column_name: str):
        return column_name in self._get_column_names(table_name)

    def table_exists(self, table_name: str):
        table_names = self._fetch(f"SELECT true FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        return len(table_names) > 0

    def create_table(self, table_name: str, shape: dict):
        assert self.table_exists(table_name) is False, "Table already exists"

        headers = []

        for column_name, (data_type, modifiers) in shape.items():
            assert hasattr(data_type, "value"), "Invalid data type"
            assert all([hasattr(modifier, "value") for modifier in modifiers]), "Invalid modifiers"

            data_type_name = data_type.value
            modifier_names = [modifier.value for modifier in modifiers]

            headers.append(f"{column_name} {data_type_name} {' '.join(modifier_names)}")

        self._cursor.execute(f"CREATE TABLE {table_name} ({', '.join(headers)})")

    def delete_table(self, table_name: str):
        assert self.table_exists(table_name), "Table does not exist"

        self._cursor.execute(f"DROP TABLE {table_name}")

    def set(self, table_name: str, conditions: dict = None, data: dict = None):
        assert self.table_exists(table_name), "Table does not exist"
        conditions = conditions or {}
        data = data or {}

        if len(conditions) > 0 and self.has(table_name, conditions):
            set_string = ", ".join([f"{k}=" + f"'{v}'" if type(v) == str else str(v) for k, v in data.items()])
            condition_string = " AND ".join(
                f"{k}=" + (f"'{v}'" if type(v) == str else str(v)) for k, v in conditions.items())

            self._cursor.execute(f"UPDATE {table_name}  SET {set_string} WHERE {condition_string}")

        else:
            keys_string = ", ".join(data.keys())
            values_string = ", ".join([f"'{value}'" if type(value) == str else value for value in data.values()])

            self._cursor.execute(f"INSERT INTO {table_name} ({keys_string}) VALUES ({values_string})")

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

        return [{k: v for k, v in zip(columns, data) if k in columns} for data in res]

    def remove(self, table_name: str, conditions: dict):
        assert self.table_exists(table_name), "Table does not exist"
        assert self.has(table_name, conditions), "Row does not exist"  # Fix Filter stuff

        condition_string = " AND ".join(
            [f"{k}=" + f"'{v}'" if type(v) == str else str(v) for k, v in conditions.items()])

        self._cursor.execute(f"DELETE FROM {table_name} WHERE {condition_string}")

    def has(self, table_name: str, conditions: dict):
        assert len(conditions) > 0, "Must have some conditions"

        condition_string = " OR ".join(
            f"{k}=" + (f"'{v}'" if type(v) == str else str(v)) for k, v in conditions.items())

        rows = self._fetch(f"SELECT TRUE FROM {table_name} WHERE {condition_string}")
        return len(rows) > 0

    def b64set(self, table_name: str, conditions: dict = None, data: dict = None):
        conditions = conditions or {}
        data = data or {}

        encoded_data = {k: to_b64(v) for k, v in data.items()}

        self.set(table_name, {k: to_b64(v) for k, v in conditions.items()}, encoded_data)

    def b64get(self, table_name: str, conditions: dict, columns: Union[List[str], str] = None):
        res = self.get(table_name, {k: to_b64(v) for k, v in conditions.items()}, columns)

        return [{k: from_b64(v) for k, v in data.items()} for data in res]

    def b64remove(self, table_name: str, conditions: dict):
        self.remove(table_name, {k: to_b64(v) for k, v in conditions.items()})

    def b64has(self, table_name: str, conditions: dict):
        return self.has(table_name, {k: to_b64(v) for k, v in conditions.items()})

    def commit(self):
        self._connection.commit()

    def close_connection(self):
        self._connection.close()
