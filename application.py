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
    events = db.execute("SELECT * FROM events")
    now = datetime.datetime.now()
    currentdate = now.strftime("%m %d, %Y")
    currentdate = time.strptime(currentdate, "%m %d, %Y")
    for event in events:
        event_id = event["event_id"]
        date = event["date"]
        splitdate = date.split("-")
        if len(splitdate) == 2:
            enddate = time.strptime(splitdate[1], "%m/%d/%Y")
            if enddate < currentdate:
                photo = db.execute("SELECT picture FROM events WHERE event_id=:event_id", event_id=event_id)
                if photo[0]["picture"] != "":
                    picture = photo[0]["picture"]
                    destination = picture.split("/")
                    filename = destination[2]
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.execute("DELETE FROM events WHERE event_id=:event_id", event_id=event_id)
        else:
            startdate = time.strptime(splitdate[0], "%m/%d/%Y")
            if startdate < currentdate:
                photo = db.execute("SELECT picture FROM events WHERE event_id=:event_id", event_id=event_id)
                if photo[0]["picture"] != "":
                    picture = photo[0]["picture"]
                    destination = picture.split("/")
                    filename = destination[2]
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.execute("DELETE FROM events WHERE event_id=:event_id", event_id=event_id)
    events = db.execute("SELECT * FROM events JOIN clubs on events.club_id=clubs.club_id")
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
        return render_template("settings.html", username = user["username"], name = user["name"], email = user["email"], subscriptions = parse(user["subscriptions"]), permissions = parse(user["permissions"]))


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
            text = "Hi! A student has requested to post events on behalf of your club. Please verify their club membership through this link: "
            html = """\
            <html>
              <head></head>
              <body>
                <p>Hi! A student has requested to post events on behalf of your club. Please verify their club membership through this <a href="http://ide50-carissawu.cs50.io:8080/permissions">link</a>.
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
        username=username, hashed=generate_password_hash(password), name=name, email=email, preferences=rejoin(preferences), permissions=None)

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
    else:
        subscription = request.form.get("subscribe")
        row = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])[0]
        if row["subscriptions"]:
            clubsList = parse(row["subscriptions"])
            clubsList.append(subscription)
        else:
            clubsList = subscription
        db.execute("UPDATE users SET subscriptions = :subscriptions WHERE id = :user_id", user_id=session["user_id"], subscriptions=rejoin(clubsList))

        return redirect("/")

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
        permissions = db.execute("SELECT permissions FROM users WHERE name = :name", name = user)
        updatePermissions = []
        if permissions[0]["permissions"] == None:
            permissions[0]["permissions"] = club
            updatePermissions.append(club)
        else:
            #print(parse(permissions[0]["permissions"]).append(club))
            updatePermissions = parse(permissions[0]["permissions"])
            updatePermissions.append(club)
        db.execute("UPDATE users SET permissions=:permissions WHERE name=:name", permissions=rejoin(updatePermissions), name = user)
        return render_template("calendar.html")
    else:
        clubs = db.execute("SELECT name FROM clubs")
        users = db.execute("SELECT name FROM users")
        return render_template("permissions.html", clubs=clubs, users=users)


@app.route("/createevent", methods=["GET", "POST"])
@login_required
def createevent():
    # Create the list of possible tags for events
    tagNames = ["Academic", "Art", "Business", "Club Sports", "College Life", "Community Service", "Cultural", "Dance", "Free Food","Gender and Sexuality", "Government and Politics", "Health", "House Committee", "Media", "Offices", "Peer Counseling", "Performing Arts", "Pre-Professional", "Publications", "Religious", "Social", "Special Interests", "STEM", "Women’s Initiatives"]
    if request.method == "POST":
        # Store user inputs and return relevant error is user didn't input a required variable
        # Store the event name
        title = request.form.get("eventname")
        # Return error if title was not provided
        if not title:
            return render_template("error.html", message="You must provide an event name")
        # Store the club
        club = request.form.get("club")
        # Return error if club was not provided
        if not club:
            return render_template("error.html", message="You must provide a club")
        # Store the clubid for the club input to put in database
        club_id = db.execute("SELECT club_id FROM clubs WHERE name=:club", club=club)
        # Store the description
        description = request.form.get("description")
        # Store whether or not a user wants to upload a photo
        pictureuploadcheck = request.form.get("pictureuploadcheck")
        # Return error if the picture upload preference was not provided
        if not pictureuploadcheck:
            return render_template("error.html", message="You must say whether or not you want to upload a picture")
        # If the user wants to upload a photo
        if pictureuploadcheck == "yes":
            # Try to store the picture from the form
            try:
                picture = request.files["picture"]
            # Either the user did not provide a photo or provided an invalid image
            except:
                return render_template("error.html", message="You did not provide an image and you stated you wanted to upload one, or you provided an invalid image")
            # Create the file
            # Get the title of the event for the filename
            nospaces = title.replace(" ", "")
            # Store the filename
            filename = nospaces + ".jpg"
            # Save the picture to the images folder
            picture.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Store the link to the picture
            picturelink = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # If the user does not want to upload a photo, store no path to a photo
        else:
            picturelink = ""
        # Store the location
        location = request.form.get("location")
        # Return error if no location is provided
        if not location:
            return render_template("error.html", message="You must provide a location")
        # Store the start month
        startmonth = request.form.get("startmonth")
        # Return error if no start month was provided
        if not startmonth:
            return render_template("error.html", message="You must provide a starting date (month)")
        # Store the start day
        startday = request.form.get("startday")
        # Return error if no start day was provided
        if not startday:
            return render_template("error.html", message="You must provide a starting date (day)")
        # Store the start year
        startyear = request.form.get("startyear")
        # Return error if no start year was provided
        if not startyear:
            return render_template("error.html", message="You must provide a starting date (year)")
        # Store the end month
        endmonth = request.form.get("endmonth")
        # Return error if no end month was provided
        if not endmonth:
            return render_template("error.html", message="You must provide an ending date (month)")
        # Store the end day
        endday = request.form.get("endday")
        # Return error if no end day was provided
        if not endday:
            return render_template("error.html", message="You must provide an ending date (day)")
        # Store the end year
        endyear = request.form.get("endyear")
        # Return error if no end year was provided
        if not endyear:
            return render_template("error.html", message="You must provide an ending date (year)")
        # Store the start hour
        starthour = request.form.get("starthour")
        # Return error if no start hour was provided
        if not starthour:
            return render_template("error.html", message="You must provide a starting time (hour)")
        # Store the start minutes
        startminutes = request.form.get("startminutes")
        # Return error if no start minutes were provided
        if not startminutes:
            return render_template("error.html", message="You must provide a starting time (minutes)")
        # Store the start am pm
        startampm = request.form.get("startampm")
        # Return error if no start am pm was provided
        if not startampm:
            return render_template("error.html", message="You must provide a starting time (am/pm)")
        # Store the end hour
        endhour = request.form.get("endhour")
        # Return error if no end hour was provided
        if not endhour:
            return render_template("error.html", message="You must provide an ending time (hour)")
        # Store the end minutes
        endminutes = request.form.get("endminutes")
        # Return error if no end minutes were provided
        if not endminutes:
            return render_template("error.html", message="You must provide an ending time (minutes)")
        # Store the end am pm
        endampm = request.form.get("endampm")
        # Return error if no end am pm was provided
        if not endampm:
            return render_template("error.html", message="You must provide an ending time (am/pm)")
        # if the start am pm is am
        if startampm == "AM":
            # get the end hour in the proper format for the Google Calendar event
            starthourmilitary = int(starthour) + 12
            starthour = str(starthourmilitary)
        # if the end am pm is am
        if endampm == "AM":
            # get the end hour in the proper format for the Google Calendar event
            endhourmilitary = int(endhour) + 12
            endhour = str(endhourmilitary)

        # verify that the user has permission to post for the club they are trying to post for
        permissions = db.execute("SELECT permissions FROM users WHERE id = :user_id",user_id=session["user_id"])
        for i in range(len(parse(permissions[0]["permissions"]))):
            # if the user has permission for the club allow them to post
            if parse(permissions[0]["permissions"])[i] == club:
                print(parse(permissions[0]["permissions"])[i])
                print(club)
                break
            # if the user does not have permission return an error
            if i == len(parse(permissions[0]["permissions"]))-1:
                return render_template("error.html", message="Sorry, but you do not have permission to post events for this club")

        # format the start date and time and end date and time for the Google Calendar event
        startdateandtime = startyear + "-" + startmonth + "-" + startday + "T" + starthour + ":" + startminutes + ":00-05:00"
        enddateandtime = endyear + "-" + endmonth + "-" + endday + "T" + endhour + ":" + endminutes + ":00-05:00"

        # initialize an empty list ot store tags in
        tags = []

        # Go through all of the tags and check if the user selected that tag for the event
        for tag in tagNames:
            value = request.form.get(tag)
            # If the user did select the tag, add it to the list
            if value != None:
                tags.append(tag)

        # format the start date
        startdate = startmonth + "/" + startday + "/" + startyear
        # format the end date
        enddate = endmonth + "/" + endday + "/" + endyear
        # format the start date for comparison
        formattedstartdate = time.strptime(startdate, "%m/%d/%Y")
        # format the end date for comparison
        formattedenddate = time.strptime(enddate, "%m/%d/%Y")

        # if the start and end date are the same, store the event with one date
        if formattedstartdate == formattedenddate:
            eventdate = startdate
        else:
            # if the end date is before the start date, return an error
            if formattedenddate < formattedstartdate:
                return render_template("error.html", message="You must provide an end date that is the same day as or after the start date")
            # store the event date in the proper format
            eventdate = startdate + "-" + enddate

        # format the start time
        starttime = starthour + ":" + startminutes + startampm
        # format the end time
        endtime = endhour + ":" + endminutes + endampm
        # format the start time for comparison
        formattedstarttime = time.strptime(starttime, "%I:%M%p")
        # format the end time for comparison
        formattedendtime = time.strptime(endtime, "%I:%M%p")

        # if the start and end time are the same, store the event with one time
        if starttime == endtime:
            eventtime = starttime
        else:
            # if the event is on the same day, test the time
            if formattedstartdate == formattedenddate:
                # if the end time is before the start time, return an error
                if formattedendtime < formattedstarttime:
                    return render_template("error.html", message="You must provide an end time that is equal to or after your start time")
            # store the event time in the proper format
            eventtime = starttime + "-" + endtime

        # add the event to the database
        db.execute("INSERT INTO events (club_id, title, description, picture, tags, date, time, location) VALUES(:club_id, :title, :description, :picture, :tags, :date, :time, :location)",
        club_id=club_id[0]["club_id"], title=title, description=description, picture=picturelink, tags=rejoin(tags), date=eventdate, time=eventtime, location = location)

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
        SERVICE_ACCOUNT_FILE = '/home/ubuntu/workspace/final-project/service.json'
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

        event = service.events().insert(calendarId='cs50projectchi@gmail.com', body=event).execute()
        print('Event created: %s' % (event.get('htmlLink')))

        rows = db.execute("SELECT email, subscriptions FROM users WHERE subscriptions IS NOT NULL")
        print(rows)
        emailList = []

        for row in rows:
            print(row["subscriptions"])
            row = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])[0]
            if row["subscriptions"]:
                clubsList = parse(row["subscriptions"])
                if str(club_id[0]["club_id"]) in clubsList:
                    emailList.append(row["email"])
        print(emailList)
        send_email(emailList, "New event posted by one of your clubs", "One of the clubs you subscribe to just posted a new event. Check it out!")

        return render_template("index.html", events = db.execute("SELECT * FROM events JOIN clubs on events.club_id=clubs.club_id"))
    else:
        userpermissions = db.execute("SELECT permissions FROM users WHERE id=:id", id=session["user_id"])
        if userpermissions[0]["permissions"] == None or userpermissions[0]["permissions"] == "":
            return render_template("error.html", message="You do not have permissions to post for any clubs. Please wait for your club to approve of your club membership")
        else:
            clubs = db.execute("SELECT name FROM clubs")
            months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            return render_template("createevent.html", clubs=clubs, tags=tagNames, months = months)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return render_template("error.html", message=e.name)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
