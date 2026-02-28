from flask import Flask,redirect,render_template,request,url_for,session
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from carrier import create_container ,show_carrier_containers
from functools import wraps
import os 


#app initialization
app = Flask(__name__)
bycrypt=Bcrypt(app)


load_dotenv()
app.secret_key = os.getenv("app_secret_key", "dev-secret-key")
server_ip = "44.201.180.250"
DATABASE_NAME = "load_consolidation"

DB_CONFIG = {
    "host": server_ip,
    "user": "ubuntu",
    "password": "group_password",
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
        email=request.form.get("email")
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
                    return "Trader dashboard coming soon"
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
        email=request.form.get("email")
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
@app.route('/logout')
def logout():
    session.pop('user_email',None)
    session.pop('user_role',None)

    return redirect(url_for('home'))
if __name__ == "__main__":
    app.run(debug=True,port=5001)