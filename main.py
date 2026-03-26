from flask import Flask,redirect,render_template,request,url_for,session,flash
import mysql.connector
from mysql.connector import errorcode
from mysql.connector.errors import PoolError
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from db_pool import get_connection_with_retry
from carrier import create_container ,show_carrier_containers,get_shipment_items,get_carrier_container_details_payload,get_carrier_analytics_payload,update_container_status,update_shipment_status,ALLOWED_CONTAINER_STATUSES,ALLOWED_SHIPMENT_STATUSES
from trader import getRoutes,getCarriers,getContainerById,book_container,submit_rating,get_latest_shipment_for_container,mark_shipment_as_paid,display_booked_containers
from functools import wraps
import os
import requests
import secrets
import hashlib
from datetime import datetime, timedelta



#app initialization
app = Flask(__name__)
bycrypt=Bcrypt(app)


load_dotenv()

#keys 
app.secret_key = os.getenv("app_secret_key", "dev-secret-key")


def _hash_reset_token(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _send_reset_email(to_email, reset_link):
    print(f"[PASSWORD RESET LINK] {to_email}: {reset_link}")


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_email"):
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


def carrier_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("user_role") != "carrier":
            return "Forbidden", 403
        return view_func(*args, **kwargs)
    return wrapped_view

#for alerts
def _default_alert_redirect_target():
    role = session.get("user_role")
    if role == "carrier":
        return url_for("carrier")
    if role == "trader":
        return url_for("trader")
    return url_for("home")


#for allowing flash messages to be sent from any route without worrying about the response type or status code
@app.after_request
def centralize_alerts(response):
    if request.path.startswith("/api/"):
        return response

    if response.status_code < 400 or response.status_code >= 600:
        return response

    if response.mimetype != "text/html":
        return response

    body = response.get_data(as_text=True).strip()
    lower_body = body.lower()
    if not body or "<html" in lower_body or "<!doctype" in lower_body:
        return response

    flash(body, "error")
    return redirect(request.referrer or _default_alert_redirect_target())

#home route returns index.html
@app.route('/')
def home():
    return render_template("index.html")

#login route for both get and post requests 
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email=request.form.get("email", "").strip().lower()
        password=request.form.get("password")

        if not email or not password:
            return "Please fill the fields",400
        
        connection = None
        mycursor = None
        try:
            connection=get_connection_with_retry()
            mycursor =connection.cursor()
            mycursor.execute("select email,password_hash,role from users where email = %s", (email,))
            user=mycursor.fetchone()
            if user and bycrypt.check_password_hash(user[1],password):
                print("Login successful")
                session["user_email"] = user[0]
                session["user_role"] = user[2]
                flash("Welcome back.", "success")
                if user[2] =="carrier":
                    flash("You have successfully logged in as a carrier.", "success")
                    return redirect(url_for("carrier"))
                
                elif user[2] == "trader":
                    flash("You have successfully logged in as a trader.", "success")
                    return redirect(url_for("trader"))
            else:
                flash("Invalid email or password. Please try again.", "error")
                return "Invalid email or password",401
            
        except mysql.connector.Error as err:
            print(f"Login DB error: {err}")
            return "An error occurred during login",500
        finally:
            if mycursor:
                mycursor.close()
            if connection:
                connection.close()    


        
    return render_template("login.html")

#forgot password 
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            return "Please provide your email", 400

        last_attempt = session.get("forgot_password_last_attempt")
        now_ts = datetime.utcnow().timestamp()
        if last_attempt and (now_ts - float(last_attempt)) < 30:
            flash("Please wait a few seconds before trying again.", "info")
            return redirect(url_for("forgot_password"))
        session["forgot_password_last_attempt"] = now_ts

        connection = None
        cursor = None
        try:
            connection = get_connection_with_retry()
            cursor = connection.cursor()

            cursor.execute(
                "DELETE FROM password_reset_tokens WHERE used = 1 OR expires_at < UTC_TIMESTAMP()"
            )

            cursor.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (email,))
            user_row = cursor.fetchone()

            if user_row:
                user_id = user_row[0]
                raw_token = secrets.token_urlsafe(32)
                token_hash = _hash_reset_token(raw_token)
                expires_at = datetime.utcnow() + timedelta(minutes=30)

                cursor.execute(
                    """
                    INSERT INTO password_reset_tokens (user_id, token_hash, expires_at, used)
                    VALUES (%s, %s, %s, 0)
                    """,
                    (user_id, token_hash, expires_at),
                )

                reset_link = url_for("reset_password", token=raw_token, _external=True)
                _send_reset_email(email, reset_link)

            connection.commit()
        except (mysql.connector.Error, PoolError) as err:
            print(f"Forgot password error: {err}")
            return "Unable to process reset request right now", 500
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

        flash("If the account exists, a reset link has been sent.", "info")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")

#reset password
@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_hash = _hash_reset_token(token)

    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not password or not confirm_password:
            return "Please fill in all fields", 400
        if password != confirm_password:
            return "Passwords do not match", 400
        

        connection = None
        cursor = None
        try:
            connection = get_connection_with_retry()
            cursor = connection.cursor()
            connection.start_transaction()

            cursor.execute(
                """
                SELECT id, user_id, expires_at, used
                FROM password_reset_tokens
                WHERE token_hash = %s
                LIMIT 1
                FOR UPDATE
                """,
                (token_hash,),
            )
            token_row = cursor.fetchone()

            if not token_row:
                connection.rollback()
                return "Invalid reset link", 400

            token_id, user_id, expires_at, used = token_row
            if used:
                connection.rollback()
                return "Reset link already used", 400
            if datetime.utcnow() > expires_at:
                connection.rollback()
                return "Reset link has expired", 400

            password_hash = bycrypt.generate_password_hash(password).decode("utf-8")
            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
            cursor.execute("UPDATE password_reset_tokens SET used = 1 WHERE id = %s", (token_id,))
            cursor.execute(
                "UPDATE password_reset_tokens SET used = 1 WHERE user_id = %s AND used = 0",
                (user_id,),
            )

            connection.commit()
            flash("Password reset successful. Please sign in.", "success")
            return redirect(url_for("login"))
        except (mysql.connector.Error, PoolError) as err:
            if connection:
                connection.rollback()
            print(f"Reset password error: {err}")
            return "Unable to reset password right now", 500
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()

    return render_template("reset_password.html", token=token)

#register user route carrier and trader 
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name=request.form.get("name")
        email=request.form.get("email", "").strip().lower()
        phone_number=request.form.get("phone_number")
        password=request.form.get("password")
        role=request.form.get("role")
        company_name = request.form.get("company_name")
        licence_number = request.form.get("licence_number")


        if not name or not email or not phone_number or not password or not role:
            return "Please fill in all fields",400

        if role == "carrier" and (not company_name or not licence_number):
            return "Carrier fields are required",400

        hashed_password=bycrypt.generate_password_hash(password).decode("utf-8")
        connection = None
        mycursor = None
        try:
            #setting up the connection to the database
            connection = get_connection_with_retry()
            mycursor = connection.cursor()
            connection.start_transaction()
            mycursor.execute(
                "INSERT INTO users (full_name,email,phone,password_hash,role) VALUES (%s,%s,%s,%s,%s)",
                (name,email,phone_number,hashed_password,role)
            )
            user_id = mycursor.lastrowid

            if role == "carrier":
                mycursor.execute(
                    "INSERT INTO carriers (user_id,company_name,license_number) VALUES (%s,%s,%s)",
                    (user_id,company_name,licence_number)
                )

            connection.commit()
            flash("Registration successful. Please log in.", "success")
        except mysql.connector.Error as err:
            if connection:
                connection.rollback()
            if err.errno == errorcode.ER_DUP_ENTRY:
                return "Email already exists. Please use another email or login.", 409
            print(f"Registration DB error: {err}")
            return "An error occurred during registration",500
        finally:
            if mycursor:
                mycursor.close()
            if connection:
                connection.close()


        return redirect("/login")

    return render_template("register.html")

#main carrier page for creating containers and also viwing existing ones 
@app.route("/carrier" , methods=["GET","POST"])
@login_required
@carrier_required
def carrier():
    if request.method == "POST":
        cont_type=request.form.get("cont_type")
        origin=request.form.get("origin")
        destination=request.form.get("destination") 
        max_weight=request.form.get("max_weight")
        max_cbm=request.form.get("max_cbm")
        departure_date=request.form.get("departure_date")   
        price_weight=request.form.get("price_weight")
        price_cbm=request.form.get("price_cbm")
        distance=request.form.get("distance")

        required_values = [
            cont_type,
            origin,
            destination,
            max_weight,
            max_cbm,
            departure_date,
            price_weight,
            price_cbm,
            distance,
        ]
        if any(not value for value in required_values):
            return "Please fill in all fields", 400

        ok, result = create_container(
            user_email=session.get("user_email"),
            origin=origin,
            destination=destination,
            distance=distance,
            cont_type=cont_type,
            departure_date=departure_date,
            max_weight=max_weight,
            max_cbm=max_cbm,
            price_weight=price_weight,
            price_cbm=price_cbm,
        )

        if not ok:
            return result, 500

        flash("Container created successfully.", "success")

        return redirect(url_for("carrier"))



    return render_template("carrier.html", containers=show_carrier_containers(session.get("user_email")))


#main trader page for viewing default available containers
@app.route("/trader", methods=["GET", "POST"])
@login_required
def trader():
    if request.method == "POST":
        destination = (request.form.get("destination") or "").strip()
        origin = (request.form.get("origin") or "").strip()
        return redirect(url_for("trader_search", origin=origin, destination=destination))

    containers = getCarriers(limit=10)
    if isinstance(containers, tuple) and containers and containers[0] is False:
        return containers[1], 500
    carriers = containers or []

    return render_template(
        "trader.html",
        routes=getRoutes(),
        carriers=carriers,
        search_active=False,
        selected_origin="",
        selected_destination="",
    )


@app.route("/trader/search", methods=["GET", "POST"])
@login_required
def trader_search():
    data = request.form if request.method == "POST" else request.args
    destination = (data.get("destination") or "").strip()
    origin = (data.get("origin") or "").strip()

    if not origin or not destination:
        return "Please provide both origin and destination", 400

    containers = getCarriers(origin=origin, destination=destination, limit=100)
    if isinstance(containers, tuple) and containers and containers[0] is False:
        return containers[1], 500

    return render_template(
        "trader.html",
        routes=getRoutes(),
        carriers=containers or [],
        search_active=True,
        selected_origin=origin,
        selected_destination=destination,
    )

#route to view booked containers 
@app.route("/trader/shipments")
@login_required
def trader_shipments():
    booked_containers = display_booked_containers(session.get("user_email"))
    if isinstance(booked_containers, tuple) and booked_containers and booked_containers[0] is None:
        return booked_containers[1], 500

    return render_template(
        "trader_shipments.html",
        containers=booked_containers or [],
    )


@app.route("/trader/container/<int:container_id>")
@login_required
def trader_container_detail(container_id):
    container = getContainerById(container_id)
    if not container:
        return "Container not found", 404

    departure_date = container.get("departure_date")
    today = datetime.utcnow().date()
    can_book = bool(
        container.get("status") == "open"
        and departure_date
        and departure_date >= today
    )

    latest_shipment = get_latest_shipment_for_container(session.get("user_email"), container_id)
    has_booked = latest_shipment is not None
    has_paid = bool(
        latest_shipment
        and latest_shipment.get("status") in ("confirmed", "in_transit", "delivered")
    )
    return render_template(
        "container_detail.html",
        container=container,
        has_booked=has_booked,
        has_paid=has_paid,
        latest_shipment=latest_shipment,
        can_book=can_book,
    )
#route for booking a container as a trader 
@app.route("/trader/book/<int:container_id>", methods=["POST"])
@login_required
def trader_book_container(container_id):
    product_names = request.form.getlist("product_name[]")
    product_types = request.form.getlist("product_type[]")
    weights = request.form.getlist("weight[]")
    cbms = request.form.getlist("cbm[]")

    ok, result, status_code = book_container(
        session.get("user_email"),
        container_id,
        product_names,
        product_types,
        weights,
        cbms,
    )

    if not ok:
        return result, status_code
    flash("Booking submitted successfully.", "success")
    return redirect(url_for("trader_container_detail", container_id=container_id))

#route to allow traders to rate carriers. 
@app.route("/trader/rate/<int:container_id>", methods=["POST"])
@login_required
def trader_rate_carrier(container_id):
    rating = request.form.get("rating")
    review = request.form.get("review")

    try:
        rating_value = int(rating)
        if rating_value < 1 or rating_value > 5:
            return "Rating must be between 1 and 5", 400
    except ValueError:
        return "Invalid rating value", 400

    ok, message, status_code = submit_rating(
        session.get("user_email"),
        container_id,
        rating_value,
        review,
    )

    if not ok:
        return message, status_code

    flash("Rating submitted successfully.", "success")
    return redirect(url_for("trader_container_detail", container_id=container_id))

# route for carriers to also view details of a container
@app.route("/carrier/container_details")
@login_required
@carrier_required
def carrier_container_details():
    container_id = request.args.get("container_id", type=int)
    if not container_id:
        return "Container id is required", 400

    payload, error = get_carrier_container_details_payload(session.get("user_email"), container_id)
    if error:
        return error, 500
    if not payload:
        return "Container not found", 404

    return render_template(
        "carrier_container_details.html",
        container=payload["container"],
        bookings=payload["bookings"],
        max_weight=payload["max_weight"],
        max_cbm=payload["max_cbm"],
        total_booked_weight=payload["total_booked_weight"],
        total_booked_cbm=payload["total_booked_cbm"],
        remaining_weight=payload["remaining_weight"],
        remaining_cbm=payload["remaining_cbm"],
        items_by_shipment=payload["items_by_shipment"],
        allowed_container_statuses=ALLOWED_CONTAINER_STATUSES,
        allowed_shipment_statuses=ALLOWED_SHIPMENT_STATUSES,
    )

#route for carriers to update container status and also shipment status
@app.route("/carrier/container/<int:container_id>/status", methods=["POST"])
@login_required
@carrier_required
def carrier_update_container_status(container_id):
    new_status = (request.form.get("status") or "").strip()
    ok, message = update_container_status(session.get("user_email"), container_id, new_status)
    flash(message, "success" if ok else "error")
    return redirect(url_for("carrier_container_details", container_id=container_id))


@app.route("/carrier/shipment/<int:shipment_id>/status", methods=["POST"])
@login_required
@carrier_required
def carrier_update_shipment_status(shipment_id):
    container_id = request.form.get("container_id", type=int)
    new_status = (request.form.get("status") or "").strip()

    ok, message = update_shipment_status(session.get("user_email"), shipment_id, new_status)
    flash(message, "success" if ok else "error")

    if container_id:
        return redirect(url_for("carrier_container_details", container_id=container_id))
    return redirect(url_for("carrier"))


@app.route("/api/shipment/<int:shipment_id>/items")
@login_required
def get_shipment_items_api(shipment_id):
    items = get_shipment_items(shipment_id)
    if isinstance(items, str):
        return {"error": items}, 500
    return {"items": items}

#carrier analytics dashboard  
@app.route("/carrier/analytics")
@login_required
@carrier_required
def analytics():
    analytics_payload, error = get_carrier_analytics_payload(session.get("user_email"))
    if error:
        return error, 500

    return render_template(
        "carrier_dashboard.html",
        kpi_summary=analytics_payload.get("kpi_summary", {}),
        shipment_status_data=analytics_payload.get("shipment_status_data", []),
        earnings_data=analytics_payload.get("earnings_data", []),
        recent_shipments=analytics_payload.get("recent_shipments", []),
        route_performance_data=analytics_payload.get("route_performance_data", []),
    )

@app.route("/trader/pay")
@login_required
def pay():
    return "Please start payment from a specific container details page.", 400


@app.route("/trader/pay/<int:container_id>")
@login_required
def pay_for_container(container_id):
    latest_shipment = get_latest_shipment_for_container(session.get("user_email"), container_id)
    if not latest_shipment:
        return "No booking found for this container.", 404

    if latest_shipment.get("status") in ("confirmed", "in_transit", "delivered"):
        return redirect(url_for("trader_container_detail", container_id=container_id))

    shipment_id = latest_shipment.get("shipment_id")
    amount = latest_shipment.get("calculated_price")
    if amount is None:
        return "Unable to initialize payment: invalid shipment amount.", 400
    return render_template(
        "pay.html",
        container_id=container_id,
        shipment_id=shipment_id,
        amount=float(amount),
    )


@app.route("/trader/pay/<int:container_id>/complete", methods=["POST"])
@login_required
def complete_demo_payment(container_id):
    latest_shipment = get_latest_shipment_for_container(session.get("user_email"), container_id)
    if not latest_shipment:
        return "No booking found for this container.", 404

    shipment_id = latest_shipment.get("shipment_id")
    if not shipment_id:
        return "Invalid shipment details.", 400

    paid = mark_shipment_as_paid(shipment_id)
    if not paid:
        return "Unable to complete payment for this shipment.", 400

    flash("Payment successful (demo). You can now review this carrier.", "success")
    return redirect(url_for("trader_container_detail", container_id=container_id))

 

@app.route('/callback')
def callback():
    status = request.args.get("status")
    transaction_id = request.args.get("transaction_id")
    container_id = request.args.get("container_id", type=int)
    shipment_id = request.args.get("shipment_id", type=int)

    if status == "successful" and transaction_id and shipment_id and container_id:
        # Always verify server-side — never trust the redirect alone
        try:
            verify_response = requests.get(
                f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
                headers={"Authorization": f"Bearer {os.getenv('FLW_SECRET_KEY')}"},
                timeout=20,
            )
            verify_response.raise_for_status()
            verify_payload = verify_response.json() or {}
        except (requests.RequestException, ValueError):
            return redirect(url_for("trader_container_detail", container_id=container_id))

        data = verify_payload.get("data") or {}
        tx_ref = data.get("tx_ref") or ""
        expected_prefix = f"shipment-{shipment_id}-"
        if (
            data.get("status") == "successful"
            and data.get("currency") == "NGN"
            and tx_ref.startswith(expected_prefix)
        ):
            mark_shipment_as_paid(shipment_id)
            flash("Payment confirmed successfully.", "success")

    if container_id:
        return redirect(url_for("trader_container_detail", container_id=container_id))
    return redirect(url_for("trader"))

@app.route('/logout')
def logout():
    session.pop('user_email',None)
    session.pop('user_role',None)
    flash("You have been logged out.", "info")

    return redirect(url_for('home'))
if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5001")))