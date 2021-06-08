import os
import sys
import re
import pytz

from string import digits
from datetime import datetime, date, time, timedelta
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response



# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finalproject.db")

# Get the actual date
dtoday = datetime.now()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/bills")
@login_required
def bills():
        bills_rows = db.execute("SELECT * FROM bills WHERE id=:id", id=session["user_id"])
        total = db.execute("SELECT SUM(price) AS price FROM bills WHERE id=:id", id=session["user_id"])[0]["price"]
        return render_template("bills.html", bills_rows=bills_rows, total=total)

@app.route("/addbill", methods=["GET", "POST"])
@login_required
def addbill():
    if request.method == "POST":
        # Get what user inputed
        name = request.form.get("name")
        price = request.form.get("price")
        validade = request.form.get("validade")

        # Put validade in the pattern of date
        valid_validade = re.match("[0-9]{2}/[0-9]{2}/[0-9]{4}", validade)
        # Validates validade
        if not valid_validade:
            flash("Data inválida, use o formato Dia/Mês/Ano. Ex: 22/09/2020")
            return redirect("/addbill")

        especificação = request.form.get("especificação")
        # Define DD/MM/YYYY for date
        day,month,year = validade.split("/")
        # Check if user inputed a correct value for day, month or year
        if int(day) > 31 or int(month) > 12 or int(year) > 9999:
            flash("Valor inválido para dia, mês ou ano.")
            return redirect("/addbill")
        # Check for valid price format
        if not price.replace('.','', 1).isdigit():
            flash("Formato inválido de preço. Use ponto se tiver casas decimais.")
            return redirect("/addbill")

        # Convert the user input(validade) and convert it into a real date
        validity = datetime(int(year),int(month),int(day))

        # Get how many days remains to the bill expire
        daysDiff = validity - dtoday
        remaining_days = daysDiff.days


        # Check if the validity date is a valid date
        isValidDate = True
        try:
            datetime(int(year),int(month),int(day))
        except ValueError :
            isValidDate = False
            if True:
                flash("Data inválida, use o formato Dia/Mês/Ano. Ex: 22/09/2020")
                return redirect("/addbill")

        if not isValidDate:
            flash("Data de validade inválida, use o formato Dia/Mês/Ano. Ex: 22/09/2020")
            return redirect("/addbill")
        # If the date is valid insert into the table and update the bill remaining days to expire
        else:
            names = db.execute("SELECT name FROM bills WHERE id=:id", id=session["user_id"])
            already_name = []
            for i in range(len(names)):
                already_name.append(names[i]["name"])
            if name in already_name:
                name_counter = 1
                while (name in already_name):
                    name_counter += 1
                    new_name = str(name) + str(name_counter)
                    if new_name in already_name:
                        continue
                    else:
                        name = new_name
                        break

            db.execute("INSERT INTO bills (id, name, price, validade, especificação, type) VALUES (:id , :name, :price, :validade, :especificação, :type)",
                        id=session["user_id"],
                        name=name,
                        price=price,
                        validade=validade,
                        especificação=especificação,
                        type="topay")

            db.execute("UPDATE bills SET remainingDays=:rd WHERE id=:id AND name=:name AND price=:price AND especificação=:especificação",
                        rd=remaining_days,
                        id=session["user_id"],
                        name=name,
                        price=price,
                        especificação=especificação)
            # Redirect user to see the table
            return redirect("/bills")

    else:
        # Display addbill form to the user when he gets to /addbill
        return render_template("addbill.html")

@app.route("/paybill", methods=["GET", "POST"])
@login_required
def paybill():
    if request.method == "POST":
        name = request.form.get("name")
        bills = db.execute("SELECT name FROM bills WHERE id=:id", id=session["user_id"])

        bills_values = db.execute("SELECT price, especificação FROM bills WHERE id=:id AND name=:name",
                                        id=session["user_id"],
                                        name=name)

        bills_price = bills_values[0]["price"]
        bills_especificação = bills_values[0]["especificação"]

        payday = dtoday.strftime("%d/%m/%Y")

        db.execute("INSERT INTO paidbills (id, name, price, especificação, payday) VALUES (:id, :name, :price, :especificação, :payday)",
                    id=session["user_id"],
                    name=name,
                    price=bills_price,
                    especificação=bills_especificação,
                    payday=payday)

        db.execute("DELETE FROM bills WHERE id=:id AND name=:name",
                    id=session["user_id"],
                    name=name)
        return redirect("/paidbills")
    else:
        bills_rows = db.execute("SELECT * FROM bills WHERE id=:id", id=session["user_id"])
        return render_template("paybill.html", bills_rows=bills_rows)

@app.route("/paidbills")
@login_required
def paidbills():
    paidbills_rows = db.execute("SELECT * FROM paidbills WHERE id=:id",id=session["user_id"])
    total = db.execute("SELECT SUM(price) AS price FROM paidbills WHERE id=:id", id=session["user_id"])[0]["price"]
    return render_template("paidbills.html", paidbills_rows=paidbills_rows, total=total)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash("Você precisa digitar o seu nome de usuário.")
            return redirect("/login")

        # Ensure password was submitted
        if not request.form.get("password"):
            flash("Você precisa digitar a sua senha.")
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return redirect('/login')

        # Forget any user_id
        session.clear()

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Check if the user provided a username
        if not request.form.get("username"):
            flash("Você precisa digitar um nome de usuário.")
            return redirect("/register")

        # Check if the user provided a password
        elif not request.form.get("password"):
            flash("Você precisa digitar uma senha.")
            return redirect("/register")
        # Check if the user confirmed his/her password
        elif not request.form.get("confirmation"):
            flash("Você precisa confirmar sua senha.")
            return redirect("/register")
        # Check if the user passwords match
        elif request.form.get("confirmation") != request.form.get("password"):
            flash("Suas senhas não são iguais.")
            return redirect("/register")

        # Check if username already exist
        exists_username = db.execute("SELECT * FROM users WHERE username= :uname",
                                    uname=request.form.get("username"))

        if exists_username:
            flash("Falha ao registrar: o nome de usuário já existe, escolha outro por favor.")
            return redirect("/register")
        else:
            insert = db.execute("INSERT INTO users (username, hash) VALUES (:username, :password_hash)",
                                  username = request.form.get("username"),
                                  password_hash = generate_password_hash(request.form.get("password")))
        # Set session id to the new user id
        session["user_id"] = insert

        # Redirect user to homepage
        return redirect("/")

    # Open the register form to the user
    else:
        return render_template("register.html")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
