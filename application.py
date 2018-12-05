from __future__ import print_function
import datetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import os
import math
import smtplib
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
import random
import datetime
import time
import googleapiclient.discovery
from googleapiclient.discovery import build
from google.oauth2 import service_account

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from helpers import login_required, parse, rejoin, send_email

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

UPLOAD_FOLDER = "static/images/"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    # get the username the user input from the form
    username = request.args.get("username")
    # get all of the current usernames of users
    currentUsernames = db.execute("SELECT username FROM users")
    # iterate through each user
    for user in currentUsernames:
        # if the username the current user is trying to use already exists, return false and notify them, via the javascript, that the username is taken
        if user["username"] == username:
            return jsonify(False)
    # the username is not taken, the user can use it and return true
    return jsonify(True)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    # User reached route via post
    if request.method == "POST":

        # Make sure user fills out all fields
        if not request.form.get("password"):
            return render_template("error.html", message="Must provide password")
        elif not request.form.get("new-password"):
            return render_template("error.html", message="Must provide new password")
        elif not request.form.get("confirmation"):
            return render_template("error.html", message="Must confirm password")

        rows = db.execute("SELECT hash FROM users WHERE id = :user_id",user_id=session["user_id"])
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("error.html", message="Invalid password")
        else:
            if request.form.get("new-password") == request.form.get("confirmation"):
                db.execute("UPDATE users SET hash = :hashedpass WHERE id = :user_id", hashedpass=generate_password_hash(request.form.get("new-password")), user_id=session["user_id"])
                return redirect("/")
            else:
                return render_template("error.html", message="New passwords do not match")
    # User reached route via get
    else:
        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id = session["user_id"])[0]
        permissions = db.execute("SELECT permissions FROM users WHERE id = :user_id", user_id = session["user_id"])
        return render_template("settings.html", username = user["username"], permissions = permissions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="Must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="Must provide passowrd")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("error.html", message="Invalid username and/or password")

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
    if request.method == "POST":
        # Store inputs in variables for easier access
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        email = request.form.get("email")
        name = request.form.get("name")
        preferences = request.form.getlist("preferences")
        permissions = request.form.getlist("permissions")

        # Return relevant error is user didn't input one variable
        if not username:
            return render_template("error.html", message="Missing username")
        if not password:
            return render_template("error.html", message="Missing password")
        if not confirmation:
            return render_template("error.html", message="Missing password confirmation")
        if password != confirmation:
            return render_template("error.html", message="Passwords do not match")


        # Sends permission email to club
        if permissions != None:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login("cs50projectchi@gmail.com", "carissahunterife")

            # Create message container - the correct MIME type is multipart/alternative.
            msg = MIMEMultipart('alternative')

            # Create the body of the message (a plain-text and an HTML version).
            text = "Hi!\nHow are you?\nHere is the link you wanted:\nhttp://www.python.org"
            html = """\
            <html>
              <head></head>
              <body>
                <p>Hi!<br>
                   How are you?<br>
                   Here is the <a href="http://www.python.org">link</a> you wanted.
                </p>
              </body>
            </html>
            """
            # Record the MIME types of both parts - text/plain and text/html.
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')

            # Attach parts into message container.
            # According to RFC 2046, the last part of a multipart message, in this case
            # the HTML message, is best and preferred.
            msg.attach(part1)
            msg.attach(part2)

            server.sendmail("cs50projectchi@gmail.com", "carissawu2009@gmail.com", msg.as_string())

        # If insertion returns null, then username must be taken
        result = db.execute("INSERT INTO users (username, hash, name, email, preferences, permissions) VALUES(:username, :hashed, :name, :email, :preferences, :permissions)",
        username=username, hashed=generate_password_hash(password), name=name, email=email, preferences=rejoin(preferences), permissions=rejoin(permissions))

        if not result:
            return render_template("error.html", message="Username is taken")

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)

        session["user_id"] = rows[0]["id"]
        return redirect("/")

        # Add permissions to user database

    else:
        return render_template("register.html", clubs = db.execute("SELECT name FROM clubs"))


@app.route("/clubs", methods=["GET", "POST"])
@login_required
def clubs():
    if request.method == "GET":
        clubs = db.execute("SELECT * FROM clubs")
        return render_template("clubs.html", clubs=clubs)


@app.route("/search")
def search():
    q = "'%" + request.args.get("q") + "%'"
    results = db.execute("SELECT * FROM clubs WHERE name LIKE " + q)
    return jsonify(results)


@app.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar():
    return render_template("calendar.html")


@app.route("/eventsearch", methods=["GET"])
@login_required
def searchevent():
    tagNames = ["Academic", "Art", "Business", "Club Sports", "College Life", "Community Service", "Cultural", "Dance", "Free Food","Gender and Sexuality", "Government and Politics", "Health", "House Committee", "Media", "Offices", "Peer Counseling", "Performing Arts", "Pre-Professional", "Publications", "Religious", "Social", "Special Interests", "STEM", "Women’s Initiatives"]
    clubs = db.execute("SELECT name FROM clubs")
    return render_template("eventsearch.html", tags=tagNames, clubs=clubs)


@app.route("/eventsearchtag")
@login_required
def eventsearchtag():
    tag = request.args.get("tag")
    taggedevents = []
    events = db.execute("SELECT * FROM events")
    for event in events:
        eventtags = event["tags"]
        eventtags = parse(eventtags)
        taggedevent = {}
        if tag in eventtags:
            taggedevent.update(event)
            taggedevents.append(taggedevent)
    return jsonify(taggedevents)


@app.route("/eventsearchclub")
@login_required
def eventsearchclub():
    club = request.args.get("club")
    clubdata = db.execute("SELECT * FROM clubs WHERE name=:name", name=club)
    clubevents = []
    events = db.execute("SELECT * FROM events")
    for event in events:
        club_id = event["club_id"]
        clubevent = {}
        if club_id == clubdata[0]["club_id"]:
            clubevent.update(event)
            clubevents.append(clubevent)
    return jsonify(clubevents)


@app.route("/eventsearchtitle")
@login_required
def eventsearchtitle():
    q = "'%" + request.args.get("q") + "%'"
    results = db.execute("SELECT * FROM events WHERE title LIKE " + q)
    return jsonify(results)


@app.route("/permissions", methods=["GET", "POST"])
@login_required
def permissions():
    if request.method == "POST":
        club = request.form.get("userclub")
        if not club:
            return render_template("error.html", message="You must provide your club")
        user = request.form.get("nameofuser")
        if not user:
            return render_template("error.html", message="You must provide the user you want to give permissions to")
        db.execute("UPDATE users SET permissions=:permissions WHERE name=:name", permissions=club, name=user)
        return render_template("calendar.html")
    else:
        clubs = db.execute("SELECT name FROM clubs")
        users = db.execute("SELECT name FROM users")
        return render_template("permissions.html", clubs=clubs, users=users)


@app.route("/createevent", methods=["GET", "POST"])
@login_required
def createevent():
    tagNames = ["Academic", "Art", "Business", "Club Sports", "College Life", "Community Service", "Cultural", "Dance", "Free Food","Gender and Sexuality", "Government and Politics", "Health", "House Committee", "Media", "Offices", "Peer Counseling", "Performing Arts", "Pre-Professional", "Publications", "Religious", "Social", "Special Interests", "STEM", "Women’s Initiatives"]
    if request.method == "POST":
        # Store inputs in variables for easier access

        # Return relevant error is user didn't input one variable
        title = request.form.get("eventname")
        if not title:
            return render_template("error.html", message="You must provide an event name")
        club = request.form.get("club")
        if not club:
            return render_template("error.html", message="You must provide a club")
        club_id = db.execute("SELECT club_id FROM clubs WHERE name=:club", club=club)
        description = request.form.get("description")
        pictureuploadcheck = request.form.get("pictureuploadcheck")
        if not pictureuploadcheck:
            return render_template("error.html", message="You must say whether or not you want to upload a picture")
        if pictureuploadcheck == "yes":
            picture = request.files["picture"]
            nospaces = title.replace(" ", "")
            filename = nospaces + ".jpg"
            picture.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            picturelink = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        else:
            picturelink = ""
        location = request.form.get("location")
        if not location:
            return render_template("error.html", message="You must provide a location")
        tags = request.form.get("tags")
        startmonth = request.form.get("startmonth")
        if not startmonth:
            return render_template("error.html", message="You must provide a starting date (month)")
        startday = request.form.get("startday")
        if not startday:
            return render_template("error.html", message="You must provide a starting date (day)")
        startyear = request.form.get("startyear")
        if not startyear:
            return render_template("error.html", message="You must provide a starting date (year)")
        endmonth = request.form.get("endmonth")
        if not endmonth:
            return render_template("error.html", message="You must provide an ending date (month)")
        endday = request.form.get("endday")
        if not endday:
            return render_template("error.html", message="You must provide an ending date (day)")
        endyear = request.form.get("endyear")
        if not endyear:
            return render_template("error.html", message="You must provide an ending date (year)")
        starthour = request.form.get("starthour")
        if not starthour:
            return render_template("error.html", message="You must provide a starting time (hour)")
        startminutes = request.form.get("startminutes")
        if not startminutes:
            return render_template("error.html", message="You must provide a starting time (minutes)")
        startampm = request.form.get("startampm")
        if not startampm:
            return render_template("error.html", message="You must provide a starting time (am/pm)")
        endhour = request.form.get("endhour")
        if not endhour:
            return render_template("error.html", message="You must provide an ending time (hour)")
        endminutes = request.form.get("endminutes")
        if not endminutes:
            return render_template("error.html", message="You must provide an ending time (minutes)")
        endampm = request.form.get("endampm")
        if not endampm:
            return render_template("error.html", message="You must provide an ending time (am/pm)")
        if startampm == "AM":
            starthourmilitary = int(starthour) + 12
            starthour = str(starthourmilitary)
        if endampm == "AM":
            endhourmilitary = int(endhour) + 12
            endhour = str(endhourmilitary)

        permissions = db.execute("SELECT permissions FROM users WHERE id = :user_id",user_id=session["user_id"])
        for i in range(len(parse(permissions[0]["permissions"]))):
            if parse(permissions[0]["permissions"])[i] == club:
                print(parse(permissions[0]["permissions"])[i])
                print(club)
                break
            if i == len(parse(permissions[0]["permissions"]))-1:
                return render_template("error.html", message="Sorry, but you do not have permission to post events for this club")

        startdateandtime = startyear + "-" + startmonth + "-" + startday + "T" + starthour + ":" + startminutes + ":00-04:00"
        enddateandtime = endyear + "-" + endmonth + "-" + endday + "T" + endhour + ":" + endminutes + ":00-04:00"

        tags = []
        for tag in tagNames:
            value = request.form.get(tag)
            if value != None:
                tags.append(tag)

        date = startmonth + "/" + startday + "/" + startyear + "-" + endmonth + "/" + endday + "/" + endyear
        time = starthour + ":" + startminutes + startampm + "-" + endhour + ":" + endminutes + endampm
        club_id = db.execute("SELECT club_id FROM clubs WHERE name=:club", club=club)

        db.execute("INSERT INTO events (club_id, title, description, picture, tags, date, time, location) VALUES(:club_id, :title, :description, :picture, :tags, :date, :time, :location)",
        club_id=club_id[0]["club_id"], title=title, description=description, picture=picturelink, tags=rejoin(tags), date=date, time=time, location = location)

        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        """
        store = file.Storage('token.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('calendar', 'v3', http=creds.authorize(Http()))
        """
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        SERVICE_ACCOUNT_FILE = 'service.json'
        credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)
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
        return render_template("index.html", events = db.execute("SELECT * FROM events"))
    else:
        userpermissions = db.execute("SELECT permissions FROM users WHERE id=:id", id=session["user_id"])
        if userpermissions[0]["permissions"] == None or userpermissions[0]["permissions"] == "":
            return render_template("error.html", message="You do not have permissions to post for any clubs")
        else:
            clubs = db.execute("SELECT name FROM clubs")
            return render_template("createevent.html", clubs=clubs)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return render_template("error.html", message=e.name)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
