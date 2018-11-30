from __future__ import print_function
import datetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import os
import math
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import random
import datetime
import time


from helpers import apology, login_required, lookup, parse, rejoin

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
db = SQL("sqlite:///ClubPub.db")


@app.route("/")
@login_required
def index():
    # events = club_db.execute("SELECT * FROM events")
    # now = datetime.datetime.now()
    # currentdate = now.strftime("%m %d, %Y")
    # currentdate = time.strptime(currentdate, "%m %d, %Y")
    # for event in events:
        # event_id = event["event_id"]
        # eventdate = time.strptime(event["date"], "%m %d, %Y")
        # if eventdate < currentdate:
            # club_db.execute("DELETE FROM events WHERE event_id=:event_id", event_id=event_id)
    events = db.execute("SELECT * FROM events")
    return render_template("index.html", events=events)


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

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
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
        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id = session["user_id"])[0]
        return render_template("settings.html", username = user["username"])

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
        email = request.form.get("email")
        name = request.form.get("name")

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
        result = db.execute("INSERT INTO users (username, hash, name, email) VALUES(:username, :hashed, :name, :email)",
        username=username, hashed=generate_password_hash(password), name=name, email=email)
        if not result:
            return apology("Username is taken")

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        session["user_id"] = rows[0]["id"]
        return redirect("/")

    else:
        return render_template("register.html")



@app.route("/userinfo", methods=["GET", "POST"])
@login_required
def userinfo():
    return render_template("userinfo.html", username = db.execute("SELECT username FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["username"], hash = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id = session["user_id"])[0]["hash"])

@app.route("/clubs", methods=["GET", "POST"])
@login_required
def clubs():
    if request.method == "GET":
        clubs = db.execute("SELECT * FROM clubs")
        return render_template("clubs.html", clubs=clubs)

@app.route("/search")
def search():
    q = request.args.get("q")
    results = db.execute("SELECT * FROM clubs WHERE name LIKE '%:query%", query=q)
    return jsonify(results)

@app.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar():
    return render_template("calendar.html")


@app.route("/createevent", methods=["GET", "POST"])
@login_required
def createevent():
    if request.method == "POST":
        # Store inputs in variables for easier access
        eventname = request.form.get("eventname")
        club = request.form.get("club")
        description = request.form.get("description")
        picture = request.form.get("picture")
        tags = request.form.get("tags")

        club_id = db.execute("SELECT club_id FROM clubs WHERE name=:club", club=club)

        # Return relevant apology is user didn't input one variable
        title = request.form.get("eventname")
        if not title:
            return apology("Missing event name!")
        club = request.form.get("club")
        if not club:
            return apology("Missing club!")
        description = request.form.get("description")
        try:
            picture = request.files["picture"].read().decode("utf-8")
        except Exception:
            apology("Invalid Picture")
        filesplit = picture.split(".")
        fileend = filesplit[1]
        nospaces = eventname.replace(" ", "")
        filename = nospaces + "." + fileend
        picturefile = open(filename, "w")
        picturefile.write(picture)
        picturefile.close()

        art = request.form.get("art")
        business = request.form.get("business")

        location = request.form.get("location")
        if not location:
            return apology("You must provide a location!")
        startmonth = request.form.get("startmonth")
        if not startmonth:
            return apology("You must provide a starting date (month)!")
        startday = request.form.get("startday")
        if not startday:
            return apology("You must provide a starting date (day)!")
        startyear = request.form.get("startyear")
        if not startyear:
            return apology("You must provide a starting date (year)!")
        endmonth = request.form.get("endmonth")
        if not endmonth:
            return apology("You must provide an ending date (month)!")
        endday = request.form.get("endday")
        if not endday:
            return apology("You must provide an ending date (day)!")
        endyear = request.form.get("endyear")
        if not endyear:
            return apology("You must provide an ending date (year)!")
        starthour = request.form.get("starthour")
        if not starthour:
            return apology("You must provide a starting time (hour)!")
        startminutes = request.form.get("startminutes")
        if not startminutes:
            return apology("You must provide a starting time (minutes)!")
        startampm = request.form.get("startampm")
        if not startampm:
            return apology("You must provide a starting time (am/pm)!")
        endhour = request.form.get("endhour")
        if not endhour:
            return apology("You must provide an ending time (hour)!")
        endminutes = request.form.get("endminutes")
        if not endminutes:
            return apology("You must provide an ending time (minutes)!")
        endampm = request.form.get("endampm")
        if not endampm:
            return apology("You must provide an ending time (am/pm)!")
        if startampm == "AM":
            starthourmilitary = int(starthour) + 12
            starthour = str(starthourmilitary)
        if endampm == "AM":
            endhourmilitary = int(endhour) + 12
            endhour = str(endhourmilitary)
        startdateandtime = startyear + "-" + startmonth + "-" + startday + "T" + starthour + ":" + startminutes + ":00-04:00"
        enddateandtime = endyear + "-" + endmonth + "-" + endday + "T" + endhour + ":" + endminutes + ":00-04:00"
        date = startdateandtime + "-" + enddateandtime
        if art == None:
            art = ""
        if business == None:
            business = ""
        tags = art + ", " + business

        club_id = db.execute("SELECT club_id FROM clubs WHERE name=:club", club=club)

        db.execute("INSERT INTO events (club_id, title, description, picture, tags, date, time, location) VALUES(:club_id, :title, :description, :picture, :tags, :date, :time, :location)",
        club_id=club_id[0]["club_id"], title=title, description=description, picture=filename, tags=tags, date=date, time=time, location=location)

        SCOPES = 'https://www.googleapis.com/auth/calendar'
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('calendar', 'v3', http=creds.authorize(Http()))

        event = {
            'summary': title,
            'location': location,
            'description': club,
            'start': {
                'dateTime': startdateandtime,
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': enddateandtime,
                'timeZone': 'America/New_York',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 10},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))
        return render_template("calendar.html")
    else:
        # userpermissions = club_db.execute("SELECT permissions FROM users WHERE id=:id", session["user_id"])
        # if userpermissions = True:
            # clubs = club_db.execute("SELECT name FROM clubs")
            # return render_template("createevent.html", clubs=clubs)
        # else:
            # return apology("You can not access this page!")
        clubs = db.execute("SELECT name FROM clubs")
        return render_template("createevent.html", clubs=clubs)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
