from flask import Flask,redirect,render_template,request,url_for,session
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from carrier import create_container ,show_carrier_containers
from trader import getRoutes,getCarriers,getContainerById,book_container
from functools import wraps
import os 


#app initialization
app = Flask(__name__)
bycrypt=Bcrypt(app)


load_dotenv()
app.secret_key = os.getenv("app_secret_key", "dev-secret-key")
server_ip = os.getenv("server_ip")
server_password = os.getenv("server_password")
DATABASE_NAME = "load_consolidation"

DB_CONFIG = {
    "host": server_ip,
    "user": "ubuntu",
    "password": server_password,
    "database":DATABASE_NAME
}


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

@app.route('/')
def home():
    return render_template("index.html")

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
            connection=mysql.connector.connect(**DB_CONFIG)
            mycursor =connection.cursor()
            mycursor.execute("select email,password_hash,role from users where email = %s", (email,))
            user=mycursor.fetchone()
            if user and bycrypt.check_password_hash(user[1],password):
                print("Login successful")
                session["user_email"] = user[0]
                session["user_role"] = user[2]
                if user[2] =="carrier":
                    return redirect(url_for("carrier"))
                
                elif user[2] == "trader":
                    return redirect(url_for("trader"))
            else:
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


@app.route("/register", methods=["GET","POST"])
def register():
    global DB_CONFIG
    
    
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
            connection = mysql.connector.connect(**DB_CONFIG)
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

        return redirect(url_for("carrier"))



    return render_template("carrier.html", containers=show_carrier_containers(session.get("user_email")))


@app.route("/trader", methods=["GET","POST"])
@login_required
def trader():
    carriers = []
    if request.method == "POST":
        destination = request.form.get("destination")
        origin = request.form.get("origin")

        if not origin or not destination:
            return "Please provide both origin and destination", 400

        containers = getCarriers(origin, destination)
        if isinstance(containers, tuple) and containers and containers[0] is False:
            return containers[1], 500
        carriers = containers or []

    return render_template("trader.html", routes=getRoutes(), carriers=carriers)


@app.route("/trader/container/<int:container_id>")
@login_required
def trader_container_detail(container_id):
    container = getContainerById(container_id)
    if not container:
        return "Container not found", 404
    return render_template("container_detail.html", container=container)

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
    return redirect(url_for("trader_container_detail", container_id=container_id))

@app.route('/logout')
def logout():
    session.pop('user_email',None)
    session.pop('user_role',None)

    return redirect(url_for('home'))
if __name__ == "__main__":
    app.run(debug=True,port=5001)