import mysql.connector
from dotenv import load_dotenv
import os 

load_dotenv()
server_ip = os.getenv("server_ip")
server_password = os.getenv("server_password")


# mydb = mysql.connector.connect(
#     host=server_ip,
#     user="ubuntu",
#     database="load_consolidation",
#     password="group_password"

# )


def create_container(
    *,
    user_email,
    origin,
    destination,
    distance,
    cont_type,
    departure_date,
    max_weight,
    max_cbm,
    price_weight,
    price_cbm,
):
    # global mydb

    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=server_ip,
            user="ubuntu",
            database="load_consolidation",
            password=server_password,
        )
        cursor = connection.cursor()
        connection.start_transaction()

        cursor.execute(
            """
            SELECT c.id
            FROM carriers c
            JOIN users u ON u.id = c.user_id
            WHERE u.email = %s
            """,
            (user_email,),
        )
        carrier_row = cursor.fetchone()
        if not carrier_row:
            connection.rollback()
            return False, "Carrier profile not found for this user"

        carrier_id = carrier_row[0]

        cursor.execute(
            """
            SELECT id
            FROM routes
            WHERE origin_city = %s AND destination_city = %s
            LIMIT 1
            """,
            (origin, destination),
        )
        route_row = cursor.fetchone()

        if route_row:
            route_id = route_row[0]
            cursor.execute(
                "UPDATE routes SET distance_km = %s WHERE id = %s",
                (distance, route_id),
            )
        else:
            cursor.execute(
                "INSERT INTO routes (origin_city, destination_city, distance_km) VALUES (%s, %s, %s)",
                (origin, destination, distance),
            )
            route_id = cursor.lastrowid

        price = max(float(price_weight), float(price_cbm))

        cursor.execute(
            """
            INSERT INTO containers (
                carrier_id,
                route_id,
                container_type,
                max_weight_kg,
                max_cbm,
                price_weight,
                price_cbm,
                departure_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                carrier_id,
                route_id,
                cont_type,
                max_weight,
                max_cbm,
                price_weight,
                price_cbm,
                departure_date,
            ),
        )

        container_id = cursor.lastrowid
        connection.commit()
        return True, container_id
    except mysql.connector.Error as err:
        if connection:
            connection.rollback()
        return False, f"Container creation failed: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def show_carrier_containers(user_email):
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=server_ip,
            user="ubuntu",
            database="load_consolidation",
            password=server_password,
        )
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT c.id AS container_id, r.origin_city, r.destination_city, r.distance_km,
                   c.container_type, c.max_weight_kg, c.max_cbm, c.price_weight, c.price_cbm, c.departure_date
            FROM containers c
            JOIN carriers cr ON cr.id = c.carrier_id
            JOIN users u ON u.id = cr.user_id
            JOIN routes r ON r.id = c.route_id
            WHERE u.email = %s
            """,
            (user_email,),
        )

        containers = cursor.fetchall()
        return containers
    except mysql.connector.Error as err:
        return f"Error fetching containers: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()