

import dotenv
import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv

load_dotenv()
server_ip = os.getenv("server_ip")
server_password = os.getenv("server_password")
DATABASE_NAME = "load_consolidation"

DB_CONFIG = {
    "host": server_ip,
    "user": "ubuntu",
    "password": server_password,
    "database":DATABASE_NAME
}




def execute_schema(cursor):
    with open("schema.sql", "r") as file:
        schema_sql = file.read()

    #split statements so it is executed properly 
    for statement in schema_sql.split(";"):
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
            except mysql.connector.Error as err:
                print(f"Error executing statement: {err}")

def main():
    try:
        # Connect WITHOUT specifying database first
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # create_database(cursor)

        # # Now connect to the specific database
        # connection.database = DATABASE_NAME

        execute_schema(cursor)

        connection.commit()
        print("Schema executed successfully.")

    except mysql.connector.Error as err:
        print(f"Connection error: {err}")

    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    main()