import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    cash = db.execute("SELECT cash FROM users WHERE id=:user_id", user_id=session["user_id"])
    rows = db.execute("SELECT symbol, SUM(shares) FROM transactions JOIN users ON users.id = transactions.user_id GROUP BY transactions.symbol HAVING users.id=:user_id", user_id=session["user_id"])
    grandtotal = cash[0]["cash"]
    for row in rows:
        row["name"] = lookup(row["symbol"])["name"]
        row["curr_price"] = usd(lookup(row["symbol"])["price"])
        row["total"] = usd(lookup(row["symbol"])["price"] * row["SUM(shares)"])
        grandtotal += lookup(row["symbol"])["price"] * row["SUM(shares)"]
    return render_template("index.html", rows=rows, cash=usd(cash[0]["cash"]), grandtotal=usd(grandtotal))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        if not symbol:
            return apology("Invalid symbol")
        elif not lookup(symbol):
            return apology("Symbol doesn't exist")
        elif not shares.isdigit():
            return apology("Shares must be an integer")

        shares = int(shares)
        price = lookup(symbol)["price"]

        if shares < 1:
            return apology("Shares must be greater than or equal to 1")
        rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])
        cash = float(rows[0]["cash"]) - shares * price
        if cash < 0:
            return apology("Not enough cash for the transaction")
        else:
            db.execute("UPDATE users SET cash = :cash WHERE id = :user_id",
            cash=cash, user_id=session["user_id"])
            result = db.execute("INSERT INTO transactions (symbol, shares, price, user_id) VALUES(:symbol, :shares, :price, :user_id)", symbol=symbol, shares=shares, price=price, user_id=session["user_id"])
        return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    username = request.args.get("username")
    if len(username) >= 1:
        results = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        if results:
            return jsonify(False)
        else:
            return jsonify(True)
    return(False)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    results = db.execute("SELECT * FROM transactions JOIN users ON users.id = transactions.user_id WHERE users.id=:user_id", user_id=session["user_id"])
    return render_template("history.html", results=results)

@app.route("/password", methods=["GET", "POST"])
@login_required
def password():
    # User reached route via post
    if request.method == "POST":

        # Make sure user fills out all fields
        if not request.form.get("password"):
            return apology("must provide password", 403)
        elif not request.form.get("new-password"):
            return apology("must provide new password", 403)
        elif not request.form.get("confirmation"):
            return apology("must confirm password", 403)

        rows = db.execute("SELECT hash FROM users WHERE id = :user_id",user_id=session["user_id"])
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid  password", 403)
        else:
            if request.form.get("new-password") == request.form.get("confirmation"):
                db.execute("UPDATE users SET hash = :hashedpass WHERE id = :user_id", hashedpass=generate_password_hash(request.form.get("new-password")), user_id=session["user_id"])
                return redirect("/")
            else:
                return apology("new passwords don't match")
    # User reached route via get
    else:
        return render_template("password.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")

        # Error checking: if form gets submitted with blank symbol or user
        if not symbol:
            return apology("Invalid symbol")
        elif not lookup(symbol):
            return apology("Symbol doesn't exist")

        return render_template("quoted.html", name=lookup(symbol)["name"], price=usd(lookup(symbol)["price"]))
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        # Store inputs in variables for easier access
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Return relevant apology is user didn't input one variable
        if not username:
            return apology("Missing username!")
        if not password:
            return apology("Missing password!")
        if not confirmation:
            return apology("Missing password confirmation!")
        if password != confirmation:
            return apology("Passwords do not match")

        # If insertion returns null, then username must be taken
        result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hashed)",
        username=username, hashed=generate_password_hash(password))
        if not result:
            return apology("Username is taken")

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        price = lookup(symbol)["price"]

        if not symbol:
            return apology("Invalid symbol")
        elif shares < 1:
            return apology("Shares must be greater than or equal to 1")

        rows = db.execute("SELECT :symbol, SUM(shares) FROM transactions JOIN users ON users.id = :user_id GROUP BY transactions.symbol HAVING symbol = :symbol",
        user_id=session["user_id"], symbol=symbol)

        if not rows:
            return apology("You don't own that stock")
        elif rows[0]["SUM(shares)"] < shares:
            return apology("You don't own enough shares of the stock")

        curr_cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])
        cash = curr_cash[0]["cash"] + shares * price
        print()

        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id", cash=cash, user_id=session["user_id"])
        result = db.execute("INSERT INTO transactions (symbol, shares, price, user_id) VALUES(:symbol, :shares, :price, :user_id)",
        symbol=symbol, shares=-1*shares, price=price, user_id=session["user_id"])
        return redirect("/")
    else:
        rows = db.execute("SELECT symbol FROM transactions JOIN users ON users.id = :user_id GROUP BY transactions.symbol", user_id=session["user_id"])
        return render_template("sell.html", rows=rows)



@app.route("/userinfo", methods=["GET", "POST"])
@login_required
def userinfo():
    return render_template("userinfo.html", username = db.execute("SELECT username FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["username"], hash = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["hash"])


@app.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar():
    return render_template("calendar.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
