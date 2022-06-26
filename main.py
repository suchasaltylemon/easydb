from easydb import CryptoDB

EMAIL = "stevejobs@apple.com"
PASSWORD = "fortnite"


def main():
    with CryptoDB("C:/Users/Sam/PycharmProjects/dbmanager/db/Passwords.db") as password_db:
        if password_db.account_taken(EMAIL):
            print("Account taken")

            if password_db.password_is_correct(EMAIL, PASSWORD):
                print("Password is correct")

            else:
                print("Password is wrong")

        else:
            password_db.add_account(EMAIL, PASSWORD)
            print("Added account")


if __name__ == "__main__":
    main()
