import mysql.connector
from db_pool import get_connection_with_retry
from datetime import date


def getRoutes():
    connection = None
    cursor = None
    try:
        connection = get_connection_with_retry()

        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT DISTINCT origin_city, destination_city
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



def getCarriers(origin=None, destination=None, limit=10):
    connection = None
    cursor = None
    try:
        connection = get_connection_with_retry()

        cursor = connection.cursor(dictionary=True)
        query = """
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
                cr.average_rating,
                COALESCE(SUM(s.total_weight_kg), 0) AS used_weight,
                COALESCE(SUM(s.total_cbm), 0) AS used_cbm,
                LEAST(
                    100,
                    GREATEST(
                        COALESCE((SUM(s.total_weight_kg) / NULLIF(c.max_weight_kg, 0)) * 100, 0),
                        COALESCE((SUM(s.total_cbm) / NULLIF(c.max_cbm, 0)) * 100, 0)
                    )
                ) AS fullness_percentage
            FROM containers c
            JOIN routes r ON c.route_id = r.id
            JOIN carriers cr ON c.carrier_id = cr.id
            LEFT JOIN shipments s
              ON s.container_id = c.id
             AND s.status <> 'cancelled'
            WHERE c.status = 'open'
                            AND c.departure_date >= CURDATE()
        """

        params = []
        if origin:
            query += " AND r.origin_city = %s"
            params.append(origin)
        if destination:
            query += " AND r.destination_city = %s"
            params.append(destination)

        query += """
            GROUP BY
                c.id,
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
                cr.average_rating
            ORDER BY c.departure_date ASC
        """
        if limit and limit > 0:
            query += " LIMIT %s"
            params.append(int(limit))

        cursor.execute(query, tuple(params))
        
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
        connection = get_connection_with_retry()
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
        connection = get_connection_with_retry()
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

        # Check if container is still open and lock it to avoid concurrent overbooking
        cursor.execute(
            """
            SELECT status, max_weight_kg, max_cbm, price_weight, price_cbm, departure_date
            FROM containers
            WHERE id = %s
            FOR UPDATE
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

        departure_date = container_result[5]
        if departure_date and departure_date < date.today():
            connection.rollback()
            return False, "Container departure date has passed", 400

        max_weight = float(container_result[1])
        max_cbm = float(container_result[2])
        price_weight = float(container_result[3])
        price_cbm = float(container_result[4])

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(total_weight_kg), 0),
                COALESCE(SUM(total_cbm), 0)
            FROM shipments
            WHERE container_id = %s
              AND status <> 'cancelled'
            """,
            (container_id,),
        )
        used_capacity = cursor.fetchone() or (0, 0)
        used_weight = float(used_capacity[0] or 0)
        used_cbm = float(used_capacity[1] or 0)

        remaining_weight = max_weight - used_weight
        remaining_cbm = max_cbm - used_cbm

        if total_weight > remaining_weight:
            connection.rollback()
            return (
                False,
                f"Booking exceeds remaining weight capacity ({remaining_weight:.2f} kg left)",
                400,
            )

        if total_cbm > remaining_cbm:
            connection.rollback()
            return (
                False,
                f"Booking exceeds remaining CBM capacity ({remaining_cbm:.2f} CBM left)",
                400,
            )

        
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

        updated_weight = used_weight + total_weight
        updated_cbm = used_cbm + total_cbm
        if updated_weight >= max_weight or updated_cbm >= max_cbm:
            cursor.execute(
                """
                UPDATE containers
                SET status = 'full'
                WHERE id = %s AND status = 'open'
                """,
                (container_id,),
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


def get_latest_shipment_for_container(user_email, container_id):
    connection = None
    cursor = None
    try:
        connection = get_connection_with_retry()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT s.id AS shipment_id, s.calculated_price, s.status
            FROM shipments s
            JOIN users u ON s.trader_id = u.id
            WHERE u.email = %s AND s.container_id = %s
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (user_email, container_id),
        )
        shipment = cursor.fetchone()
        if shipment:
            shipment_id = shipment.get("shipment_id")
            if shipment_id:
                cursor.execute(
                    """
                    SELECT product_name, product_type, weight_kg, cbm
                    FROM shipment_items
                    WHERE shipment_id = %s
                    ORDER BY id ASC
                    """,
                    (shipment_id,),
                )
                items = cursor.fetchall() or []
                shipment["booked_items"] = items
        return shipment
    except mysql.connector.Error:
        return None
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def mark_shipment_as_paid(shipment_id):
    connection = None
    cursor = None
    try:
        connection = get_connection_with_retry()
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE shipments
            SET status = 'confirmed'
            WHERE id = %s
              AND status IN ('pending', 'confirmed')
            """,
            (shipment_id,),
        )
        connection.commit()
        return cursor.rowcount > 0
    except mysql.connector.Error:
        if connection:
            connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def submit_rating(user_email, container_id, rating_value, review):
    connection = None
    cursor = None
    review = (review or "").strip()
    if len(review) == 0:
        review = None
    try:
        connection = get_connection_with_retry()
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
            WHERE s.container_id = %s
              AND s.trader_id = %s
              AND s.status IN ('confirmed', 'in_transit', 'delivered')
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (container_id, trader_id),
        )
        shipment_row = cursor.fetchone()
        if not shipment_row:
            connection.rollback()
            return False, "You can only rate a carrier after payment is confirmed", 403

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

        cursor.execute(
            """
            UPDATE carriers c
            SET c.average_rating = (
                SELECT ROUND(AVG(r.rating), 2)
                FROM ratings r
                WHERE r.carrier_id = %s
            )
            WHERE c.id = %s
            """,
            (carrier_id, carrier_id),
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

def display_booked_containers(user_email):
    connection = None 
    cursor = None
    try:
        connection = get_connection_with_retry()
        cursor = connection.cursor(dictionary=True) 

        cursor.execute(
            """
            SELECT DISTINCT
                c.id AS container_id,
                s.id AS shipment_id,
                r.origin_city,
                r.destination_city,
                r.distance_km,
                c.container_type,
                c.departure_date,
                c.status,
                cr.id AS carrier_id,
                cr.company_name,
                cr.average_rating
            FROM shipments s
            JOIN users u ON u.id = s.trader_id
            JOIN containers c ON c.id = s.container_id
            JOIN routes r ON r.id = c.route_id
            JOIN carriers cr ON cr.id = c.carrier_id
            WHERE u.email = %s
            ORDER BY c.departure_date DESC
            """,
            (user_email,),
        )
        booked_containers = cursor.fetchall() or []

        for container in booked_containers:
            container["booked_items"] = []
            shipment_id = container.get("shipment_id")
            if shipment_id:
                cursor.execute(
                    """
                    SELECT product_name, product_type, weight_kg, cbm
                    FROM shipment_items
                    WHERE shipment_id = %s
                    ORDER BY id ASC
                    """,
                    (shipment_id,),
                )
                items = cursor.fetchall() or []
                container["booked_items"] = items

        return booked_containers
    
    except mysql.connector.Error as err:
        return None, f"Error fetching booked containers: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
