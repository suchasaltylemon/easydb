from easydb import CryptoDB

PATH = "./db/AccountsDB.db"


def main():
    with CryptoDB(PATH) as password_db:
        email = input("Email: ").lower().strip()
        password = input("Password: ").strip()

        if password_db.account_taken(email):
            print("Account taken")

            if password_db.password_is_correct(email, password):
                print("Password is correct")

            else:
                print("Password is wrong")

        else:
            password_db.add_account(email, password)
            print("Added account")


if __name__ == "__main__":
    main()
