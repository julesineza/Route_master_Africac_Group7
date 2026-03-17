import mysql.connector
from mysql.connector import pooling
from mysql.connector.errors import PoolError
from dotenv import load_dotenv
import os 
import time 

load_dotenv()
server_ip = os.getenv("server_ip")
server_password = os.getenv("server_password")


# def _get_connection():
#     return mysql.connector.connect(
#         host=os.getenv("server_ip"),
#         user="ubuntu",
#         database="load_consolidation",
#         password=os.getenv("server_password"),
#     )

# connection pooling for better performance. 
connection_pool = pooling.MySQLConnectionPool(
    pool_name="my_pool",
    pool_size=5,
    pool_reset_session=True,
    host=os.getenv("server_ip"),
    user="ubuntu",
    database="load_consolidation",
    password=os.getenv("server_password"),
)

def get_connection_with_retry(retries=3, delay=0.5):
    for attempt in range(retries):
        try:
            return connection_pool.get_connection()
        except PoolError:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise RuntimeError("All DB connections are busy")


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


def get_shipment_items(shipment_id):
    """Get all items in a specific shipment"""
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
            SELECT id, product_name, product_type, weight_kg, cbm
            FROM shipment_items
            WHERE shipment_id = %s
            ORDER BY id ASC
            """,
            (shipment_id,)
        )

        items = cursor.fetchall()
        return items
    except mysql.connector.Error as err:
        return f"Error fetching items: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_carrier_container_by_id(user_email, container_id):
    """Get a specific container owned by the carrier"""
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
            SELECT c.id AS container_id,
                   r.origin_city,
                   r.destination_city,
                   r.distance_km,
                   c.container_type,
                   c.max_weight_kg,
                   c.max_cbm,
                   c.price_weight,
                   c.price_cbm,
                   c.departure_date,
                   c.status,
                   cr.company_name,
                   u.full_name AS carrier_name,
                   u.email AS carrier_email,
                   u.phone AS carrier_phone
            FROM containers c
            JOIN carriers cr ON cr.id = c.carrier_id
            JOIN users u ON u.id = cr.user_id
            JOIN routes r ON r.id = c.route_id
            WHERE u.email = %s AND c.id = %s
            LIMIT 1
            """,
            (user_email, container_id),
        )

        return cursor.fetchone()
    except mysql.connector.Error as err:
        return f"Error fetching container details: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_carrier_container_details_payload(user_email, container_id):
    connection = None
    cursor = None
    try:
        connection = get_connection_with_retry()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT c.id AS container_id,
                   r.origin_city,
                   r.destination_city,
                   r.distance_km,
                   c.container_type,
                   c.max_weight_kg,
                   c.max_cbm,
                   c.price_weight,
                   c.price_cbm,
                   c.departure_date,
                   c.status,
                   cr.company_name,
                   u.full_name AS carrier_name,
                   u.email AS carrier_email,
                   u.phone AS carrier_phone
            FROM containers c
            JOIN carriers cr ON cr.id = c.carrier_id
            JOIN users u ON u.id = cr.user_id
            JOIN routes r ON r.id = c.route_id
            WHERE u.email = %s AND c.id = %s
            LIMIT 1
            """,
            (user_email, container_id),
        )
        container = cursor.fetchone()
        if not container:
            return None, None

        max_weight = float(container["max_weight_kg"])
        max_cbm = float(container["max_cbm"])

        cursor.execute(
            """
            SELECT s.id AS shipment_id,
                   s.trader_id,
                   u.full_name,
                   u.email,
                   u.phone,
                   s.total_weight_kg,
                   s.total_cbm,
                   s.status,
                   s.created_at
            FROM shipments s
            JOIN users u ON s.trader_id = u.id
            WHERE s.container_id = %s
            ORDER BY s.created_at ASC
            """,
            (container_id,),
        )
        bookings = cursor.fetchall() or []

        total_booked_weight = 0.0
        total_booked_cbm = 0.0
        for booking in bookings:
            weight_value = float(booking["total_weight_kg"])
            cbm_value = float(booking["total_cbm"])
            booking["weight_percentage"] = round((weight_value / max_weight) * 100, 2) if max_weight > 0 else 0
            booking["cbm_percentage"] = round((cbm_value / max_cbm) * 100, 2) if max_cbm > 0 else 0
            total_booked_weight += weight_value
            total_booked_cbm += cbm_value

        cursor.execute(
            """
            SELECT si.shipment_id,
                   si.product_name,
                   si.product_type,
                   si.weight_kg,
                   si.cbm
            FROM shipment_items si
            JOIN shipments s ON s.id = si.shipment_id
            WHERE s.container_id = %s
            ORDER BY si.shipment_id, si.id
            """,
            (container_id,),
        )
        items_rows = cursor.fetchall() or []

        items_by_shipment = {}
        for item in items_rows:
            shipment_id = str(item["shipment_id"])
            items_by_shipment.setdefault(shipment_id, []).append(
                {
                    "product_name": item["product_name"],
                    "product_type": item["product_type"],
                    "weight_kg": float(item["weight_kg"]),
                    "cbm": float(item["cbm"]),
                }
            )

        payload = {
            "container": container,
            "bookings": bookings,
            "max_weight": max_weight,
            "max_cbm": max_cbm,
            "total_booked_weight": total_booked_weight,
            "total_booked_cbm": total_booked_cbm,
            "remaining_weight": max(0, max_weight - total_booked_weight),
            "remaining_cbm": max(0, max_cbm - total_booked_cbm),
            "items_by_shipment": items_by_shipment,
        }
        return payload, None
    except (mysql.connector.Error, RuntimeError) as err:
        return None, f"Error fetching container details: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



def kpi_summary():
    connection=None
    cursor=None
    
    try : 
        #connection initilization
        connection = get_connection_with_retry()
        cursor = connection.cursor(dictionary=True)

        #get active shipments
        cursor.execute("select count(container_id) as Active shipments from shipments where status != %s or status !=%s",("delivered","canceled"),)
        active_shipments=cursor.fetchone()
       
        #get total revenue
        cursor.execute("select sum(calculated_price) as Total revenue from shipments")
        total_revenue=cursor.fetchone()

        #get avg_rating
        cursor.execute("select average_rating from carrier")
        avg_rating =cursor.fetchone()

        #get pending shipments
        cursor.execute("select count(container_id) as Pending shipments from shipments where status != %s ",("pending",),)
        pending_shipments=cursor.fetchone()

        if not active_shipments or not total_revenue or not avg_rating or not pending_shipments:
            active_shipments,total_revenue,avg_rating,pending_shipments = []

        return active_shipments , total_revenue , avg_rating , pending_shipments

    except mysql.connector.Error as err:
        return f"Error fetching container details: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

#pie chart data
def shipments_status():
    connection = get_connection_with_retry()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM shipments
            GROUP BY status
            """
        )
        shipments_status = cursor.fetchall()
        if not shipments_status:
            shipments_status = []
        return shipments_status
    except mysql.connector.Error as err:
        return f"Error fetching shipment status: {err}"
    finally:    
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


#line chart data
def earnings_over_time():
    connection = get_connection_with_retry()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT DATE(created_at) AS date, SUM(calculated_price) AS total_earnings
            FROM shipments
            WHERE status = 'delivered'
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at) ASC
            """
        )
        earnings_data = cursor.fetchall()
        if not earnings_data:
            earnings_data = []
        return earnings_data
    except mysql.connector.Error as err:
        return f"Error fetching earnings data: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

def recent_shipments(user_email):
    connection = get_connection_with_retry()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT s.id AS shipment_id, s.calculated_price, s.status, s.created_at,
                   u.full_name AS trader_name, u.email AS trader_email
            FROM shipments s
            JOIN users u ON s.trader_id = u.id
            where s.carrier_id = (select c.id from carriers c join users u on c.user_id = u.id where u.email = %s)
            ORDER BY s.created_at DESC
            LIMIT 5

            """
        )
        recent_shipments = cursor.fetchall()
        if not recent_shipments:
            recent_shipments = []
        return recent_shipments
    except mysql.connector.Error as err:
        return f"Error fetching recent shipments: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def get_carrier_analytics_payload(user_email):
    connection = None
    cursor = None
    try:
        connection = get_connection_with_retry()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN s.status IN ('pending', 'confirmed', 'in_transit') THEN 1 ELSE 0 END), 0) AS active_shipments,
                COALESCE(SUM(CASE WHEN s.status = 'delivered' THEN s.calculated_price ELSE 0 END), 0) AS total_earnings,
                COALESCE(SUM(CASE WHEN s.status = 'pending' THEN 1 ELSE 0 END), 0) AS pending_jobs,
                COALESCE(c.average_rating, 0) AS rating
            FROM carriers c
            JOIN users u ON u.id = c.user_id
            LEFT JOIN containers ct ON ct.carrier_id = c.id
            LEFT JOIN shipments s ON s.container_id = ct.id
            WHERE u.email = %s
            GROUP BY c.average_rating
            """,
            (user_email,),
        )
        kpi = cursor.fetchone() or {
            "active_shipments": 0,
            "total_earnings": 0,
            "pending_jobs": 0,
            "rating": 0,
        }

        cursor.execute(
            """
            SELECT s.status, COUNT(*) AS count
            FROM shipments s
            JOIN containers ct ON ct.id = s.container_id
            JOIN carriers c ON c.id = ct.carrier_id
            JOIN users u ON u.id = c.user_id
            WHERE u.email = %s
            GROUP BY s.status
            """,
            (user_email,),
        )
        status_data = cursor.fetchall() or []

        cursor.execute(
            """
            SELECT DATE(s.created_at) AS date, COALESCE(SUM(s.calculated_price), 0) AS total_earnings
            FROM shipments s
            JOIN containers ct ON ct.id = s.container_id
            JOIN carriers c ON c.id = ct.carrier_id
            JOIN users u ON u.id = c.user_id
            WHERE u.email = %s AND s.status = 'delivered'
            GROUP BY DATE(s.created_at)
            ORDER BY DATE(s.created_at) ASC
            """,
            (user_email,),
        )
        earnings_data = cursor.fetchall() or []

        cursor.execute(
            """
            SELECT s.id AS shipment_id,
                   s.calculated_price,
                   s.status,
                   s.created_at,
                   tu.full_name AS trader_name,
                   tu.email AS trader_email
            FROM shipments s
            JOIN users tu ON tu.id = s.trader_id
            JOIN containers ct ON ct.id = s.container_id
            JOIN carriers c ON c.id = ct.carrier_id
            JOIN users u ON u.id = c.user_id
            WHERE u.email = %s
            ORDER BY s.created_at DESC
            LIMIT 5
            """,
            (user_email,),
        )
        recent_data = cursor.fetchall() or []

        cursor.execute(
            """
            SELECT
                CONCAT(r.origin_city, ' → ', r.destination_city) AS route_label,
                COUNT(s.id) AS shipment_count
            FROM shipments s
            JOIN containers ct ON ct.id = s.container_id
            JOIN routes r ON r.id = ct.route_id
            JOIN carriers c ON c.id = ct.carrier_id
            JOIN users u ON u.id = c.user_id
            WHERE u.email = %s
            GROUP BY r.origin_city, r.destination_city
            ORDER BY shipment_count DESC
            LIMIT 8
            """,
            (user_email,),
        )
        route_performance_data = cursor.fetchall() or []

        return {
            "kpi_summary": kpi,
            "shipment_status_data": status_data,
            "earnings_data": earnings_data,
            "recent_shipments": recent_data,
            "route_performance_data": route_performance_data,
        }, None
    except (mysql.connector.Error, RuntimeError) as err:
        return None, f"Error fetching analytics: {err}"
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()






        

     