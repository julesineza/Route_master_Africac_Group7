import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()


def _get_connection():
    return mysql.connector.connect(
        host=os.getenv("server_ip"),
        user="ubuntu",
        database="load_consolidation",
        password=os.getenv("server_password"),
    )


def getRoutes():
    connection = None
    cursor = None
    try:
        connection = _get_connection()

        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT origin_city, destination_city
            FROM routes
            ORDER BY origin_city, destination_city
            """
        )
        
        result = cursor.fetchall()
        return result

    except mysql.connector.Error as err:
        if connection:
            connection.rollback()
        return False, f"Error {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



def getCarriers(origin, destination):
    connection = None
    cursor = None
    try:
        connection = _get_connection()

        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                c.id AS container_id,
                c.container_type,
                c.max_weight_kg,
                c.max_cbm,
                c.price_weight,
                c.price_cbm,
                c.departure_date,
                c.status,
                r.origin_city,
                r.destination_city,
                r.distance_km,
                cr.company_name
            FROM containers c
            JOIN routes r ON c.route_id = r.id
            JOIN carriers cr ON c.carrier_id = cr.id
            WHERE r.origin_city = %s
            AND r.destination_city = %s
            AND c.status = 'open'
            ORDER BY c.departure_date ASC
            """,
            (origin, destination),
        )
        
        result = cursor.fetchall()
        return result
        
    except mysql.connector.Error as err:
        if connection:
            connection.rollback()
        return False, f"Error {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def getContainerById(container_id):
    connection = None
    cursor = None
    try:
        connection = _get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                c.id AS container_id,
                c.container_type,
                c.max_weight_kg,
                c.max_cbm,
                c.price_weight,
                c.price_cbm,
                c.departure_date,
                c.status,
                r.origin_city,
                r.destination_city,
                r.distance_km,
                cr.company_name,
                u.full_name AS carrier_name,
                u.email AS carrier_email,
                u.phone AS carrier_phone
            FROM containers c
            JOIN routes r ON c.route_id = r.id
            JOIN carriers cr ON c.carrier_id = cr.id
            JOIN users u ON u.id = cr.user_id
            WHERE c.id = %s
            LIMIT 1
            """,
            (container_id,),
        )
        return cursor.fetchone()
    except mysql.connector.Error:
        return None
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def book_container(user_email, container_id, product_names, product_types, weights, cbms):
    connection = None
    cursor = None
    try:
        connection = _get_connection()
        cursor = connection.cursor()
        connection.start_transaction()

        if not product_names or not weights or not cbms:
            connection.rollback()
            return False, "Please add at least one shipment item", 400

        if not (len(product_names) == len(product_types) == len(weights) == len(cbms)):
            connection.rollback()
            return False, "Invalid shipment items submitted", 400

        normalized_items = []
        total_weight = 0.0
        total_cbm = 0.0

        for index in range(len(product_names)):
            product_name = (product_names[index] or "").strip()
            product_type = (product_types[index] or "").strip()

            try:
                weight_value = float(weights[index])
                cbm_value = float(cbms[index])
            except (TypeError, ValueError):
                connection.rollback()
                return False, "Weight and CBM must be valid numbers", 400

            if not product_name:
                connection.rollback()
                return False, "Product name is required for all items", 400

            if weight_value <= 0 or cbm_value <= 0:
                connection.rollback()
                return False, "Weight and CBM must be greater than zero", 400

            total_weight += weight_value
            total_cbm += cbm_value
            normalized_items.append((product_name, product_type, weight_value, cbm_value))

        # get trader user ID
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        user_result = cursor.fetchone()
        if not user_result:
            connection.rollback()
            return False, "User not found"
        user_id = user_result[0]

        # Check if container is still open and capacity constraints
        cursor.execute(
            """
            SELECT status, max_weight_kg, max_cbm, price_weight, price_cbm
            FROM containers
            WHERE id = %s
            """,
            (container_id,),
        )
        container_result = cursor.fetchone()
        if not container_result:
            connection.rollback()
            return False, "Container not found"

        if container_result[0] != "open":
            connection.rollback()
            return False, "Container is no longer available"

        max_weight = float(container_result[1])
        max_cbm = float(container_result[2])
        price_weight = float(container_result[3])
        price_cbm = float(container_result[4])

        if total_weight > max_weight:
            connection.rollback()
            return False, "Total weight exceeds container max weight", 400

        if total_cbm > max_cbm:
            connection.rollback()
            return False, "Total CBM exceeds container max CBM", 400

        
        weight_cost = total_weight * price_weight
        volume_cost = total_cbm * price_cbm

        calculated_price= max(weight_cost, volume_cost)

        cursor.execute(
            """
            INSERT INTO shipments (container_id, trader_id, total_weight_kg, total_cbm, calculated_price)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (container_id, user_id, total_weight, total_cbm, calculated_price),
        )
        shipment_id = cursor.lastrowid

        for product_name, product_type, weight_value, cbm_value in normalized_items:
            cursor.execute(
                """
                INSERT INTO shipment_items (shipment_id, product_name, product_type, weight_kg, cbm)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (shipment_id, product_name, product_type, weight_value, cbm_value),
            )

        connection.commit()
        return True, shipment_id, 201

    except mysql.connector.Error as err:
        if connection:
            connection.rollback()
        return False, f"Booking failed: {err}", 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def check_if_booked(user_email, container_id):
    connection = None
    cursor = None
    try:
        connection = _get_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT s.id
            FROM shipments s
            JOIN users u ON s.trader_id = u.id
            WHERE u.email = %s AND s.container_id = %s
            """,
            (user_email, container_id),
        )
        return True if cursor.fetchone() else False
    except mysql.connector.Error:
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def submit_rating(user_email, container_id, rating_value, review):
    connection = None
    cursor = None
    if len(review).strip() == 0:
        review = None
    try:
        connection = _get_connection()
        cursor = connection.cursor()
        connection.start_transaction()

        cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        trader_row = cursor.fetchone()
        if not trader_row:
            connection.rollback()
            return False, "Trader not found", 404
        trader_id = trader_row[0]

        cursor.execute(
            """
            SELECT s.id, c.carrier_id
            FROM shipments s
            JOIN containers c ON c.id = s.container_id
            WHERE s.container_id = %s AND s.trader_id = %s
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (container_id, trader_id),
        )
        shipment_row = cursor.fetchone()
        if not shipment_row:
            connection.rollback()
            return False, "You can only rate a carrier after booking this container", 403

        shipment_id = shipment_row[0]
        carrier_id = shipment_row[1]

        cursor.execute(
            "SELECT id FROM ratings WHERE shipment_id = %s AND trader_id = %s LIMIT 1",
            (shipment_id, trader_id),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "UPDATE ratings SET rating = %s, review = %s WHERE id = %s",
                (rating_value, review, existing[0]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO ratings (shipment_id, carrier_id, trader_id, rating, review)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (shipment_id, carrier_id, trader_id, rating_value, review),
            )

        connection.commit()
        return True, "Rating submitted", 200
    except mysql.connector.Error as err:
        if connection:
            connection.rollback()
        return False, f"Failed to submit rating: {err}", 500
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()