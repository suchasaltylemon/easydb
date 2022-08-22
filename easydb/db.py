from typing import Union, List


class DB:
    def __init__(self, db, alter_fn, get_fn, set_fn, has_fn, remove_fn, tbl_create_fn, tbl_delete_fn, tbl_exists_fn):
        self._db = db

        self._get = get_fn
        self._set = set_fn
        self._has = has_fn
        self._remove = remove_fn
        self._alter = alter_fn

        self._tbl_create = tbl_create_fn
        self._tbl_delete = tbl_delete_fn
        self._tbl_exists = tbl_exists_fn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._db.__exit__(exc_type, exc_val, exc_tb)

    def commit(self):
        self._db.commit()

    def close_connection(self):
        self._db.close_connection()

    def get(self, table_name: str, conditions: dict, columns: Union[List[str], str] = None):
        return self._get(table_name, conditions, columns)

    def alter(self, table_name: str, new_shape: dict):
        self._alter(table_name, new_shape)

    def set(self, table_name: str, conditions: dict = None, data: dict = None):
        return self._set(table_name, conditions, data)

    def has(self, table_name: str, conditions: dict):
        return self._has(table_name, conditions)

    def remove(self, table_name: str, conditions: dict):
        self._remove(table_name, conditions)

    def create_table(self, table_name: str, shape: dict):
        self._tbl_create(table_name, shape)

    def delete_table(self, table_name: str):
        self._tbl_delete(table_name)

    def table_exists(self, table_name: str):
        return self._tbl_exists(table_name)
