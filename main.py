from uuid import uuid4

from easydb import StandardDBFactory, DataType, Modifier

PATH = "./db/Customers.db"


def main():
    with StandardDBFactory.create_db(PATH) as customer_db:
        if not customer_db.table_exists("Customers"):
            customer_db.create_table("Customers", {
                "AccountId": [DataType.String, [Modifier.Unique, Modifier.NotNull, Modifier.PrimaryKey]],
                "Name": [DataType.String, [Modifier.NotNull]],
                "Age": [DataType.Integer, [Modifier.NotNull]]
            })

        add_new_customer = input("Add new customer? y/n\n > ").strip().lower() == "y"

        if add_new_customer:
            account_id = uuid4().hex

            name = input("Name: ").strip()
            age = int(input("Age: ").strip())

            customer_db.set("Customers", data={
                "AccountId": account_id,
                "Name": name,
                "Age": age
            })

        else:
            customer_name = input("Customer name: ").strip()
            print(customer_db.get("Customers", {"Name": customer_name}))


if __name__ == "__main__":
    main()
