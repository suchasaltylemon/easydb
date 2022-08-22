from abc import ABC as _ABC, abstractmethod as _abstractmethod

from .data_type import DataType
from .db import DB
from .modifier import Modifier
from .raw_db import RawDB as _RawDB


class _DBFactory(_ABC):
    @staticmethod
    @_abstractmethod
    def create_db(path: str):
        pass


class StandardDBFactory(_DBFactory):
    @staticmethod
    def create_db(path: str):
        inner_db = _RawDB(path)

        return DB(inner_db, inner_db.alter, inner_db.get, inner_db.set, inner_db.has, inner_db.remove,
                  inner_db.create_table,
                  inner_db.delete_table,
                  inner_db.table_exists)


class B64DBFactory(_DBFactory):
    @staticmethod
    def create_db(path: str):
        inner_db = _RawDB(path)

        return DB(inner_db, inner_db.b64alter, inner_db.b64get, inner_db.b64set, inner_db.b64has, inner_db.b64remove,
                  inner_db.create_table,
                  inner_db.delete_table,
                  inner_db.table_exists)
