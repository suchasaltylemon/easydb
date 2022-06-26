from .db import DB
from .data_type import DataType
from .modifier import Modifier

from uuid import uuid4
from os import urandom
from hashlib import sha256

SALT_BYTE_LENGTH = 32
TEXT_ENCODING = "utf-8"


class CryptoDB:
    def __init__(self, path: str):
        self._db = DB(path)

        self._try_make_tables()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._db.commit()
        self._db.close_connection()

    def _get_account_id(self, email: str):
        account_info = self._db.b64get("AccountInfo", {
            "Email": email.lower()
        }, ["AccountId"])

        return account_info[0].get("AccountId", None) if len(account_info) > 0 else None

    def _try_make_tables(self):
        if not self._db.table_exists("AccountInfo"):
            self._db.create_table("AccountInfo", {
                "AccountId": [DataType.String, [Modifier.Unique, Modifier.NotNull, Modifier.PrimaryKey]],
                "Email": [DataType.String, [Modifier.Unique, Modifier.NotNull]],
                "Password": [DataType.String, [Modifier.NotNull]]
            })

        if not self._db.table_exists("Salts"):
            self._db.create_table("Salts", {
                "AccountId": [DataType.String, [Modifier.Unique, Modifier.NotNull, Modifier.PrimaryKey]],
                "Salt": [DataType.String, [Modifier.NotNull]]
            })

    def account_taken(self, email: str):
        account_id = self._get_account_id(email)

        return account_id is not None

    def add_account(self, email: str, password: str):
        assert not self.account_taken(email), "Account already taken"

        account_id = uuid4().hex

        salt = urandom(SALT_BYTE_LENGTH).hex()
        salted_password = password + salt
        encrypted_password = sha256(salted_password.encode(TEXT_ENCODING)).hexdigest()

        self._db.b64set("Salts", data={
            "AccountId": account_id,
            "Salt": salt
        })

        self._db.b64set("AccountInfo", data={
            "AccountId": account_id,
            "Email": email,
            "Password": encrypted_password
        })

    def delete_account(self, email: str):
        account_id = self._get_account_id(email)

        assert account_id is not None, "Account does not exist"

        self._db.b64remove("AccountInfo", {
            "AccountId": account_id
        })

        self._db.b64remove("Salts", {
            "AccountId": account_id
        })

    def password_is_correct(self, email: str, password: str):
        assert self.account_taken(email), "Account does not exist"

        account_id = self._get_account_id(email)

        correct_password = self._db.b64get("AccountInfo", {
            "AccountId": account_id
        }, ["Password"])[0].get("Password")

        salt = self._db.b64get("Salts", {
            "AccountId": account_id
        }, ["Salt"])[0].get("Salt")

        salted_password = password + salt
        encrypted_password = sha256(salted_password.encode(TEXT_ENCODING)).hexdigest()

        return encrypted_password == correct_password

    def change_email(self, email: str):
        account_id = self._get_account_id(email)

        assert account_id is not None, "Account does not exist"

        self._db.b64set("AccountInfo", {
            "AccountId": account_id
        }, {
                            "Email": email
                        })

    def change_password(self, email: str, password: str):
        account_id = self._get_account_id(email)

        assert account_id is not None, "Account does not exist"

        salt = urandom(SALT_BYTE_LENGTH).hex()
        salted_password = password + salt
        encrypted_password = sha256(salted_password)

        self._db.b64set("AccountInfo", {
            "AccountId": account_id
        }, {
                            "Password": encrypted_password
                        })

        self._db.b64set("Salts", {
            "AccountId": account_id
        }, {
                            "Salt": salt
                        })
