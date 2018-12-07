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

# Configure CS50 Library to use SQLite database, preferences global list
db = SQL("sqlite:///ClubPub.db")
# Create a list of preferences
all_preferences = ["Free Food", "Academic and Pre-Professional", "College Life", "Creative and Performing Arts", "Cultural and Racial Initiatives", "Gender and Sexuality", "Government and Politics", "Health and Wellness",
                   "Hobbies and Special Interests", "Media and Publications", "PBHA", "Peer Counseling/Peer Education", "Public Service", "Religious and Spiritual Life", "SEAS", "Social Organization", "Women's Initiatives"]


@app.route("/")
@login_required
def index():
    """Display all events for the future"""
    # get all of the events in the database
    events = db.execute("SELECT * FROM events")
    # get the current date
    now = datetime.datetime.now()
    # format the current date
    currentdate = now.strftime("%m %d, %Y")
    # format the current date for comparison
    currentdate = time.strptime(currentdate, "%m %d, %Y")
    # loop through all of the events in the database
    for event in events:
        # get the event id
        event_id = event["event_id"]
        # get the date of the event
        date = event["date"]
        # split the date into the start and end date if necessary
        splitdate = date.split("-")
        # if there is a start and end date
        if len(splitdate) == 2:
            # use the end date and format it for comparison
            enddate = time.strptime(splitdate[1], "%m/%d/%Y")
            # if the end date of the event is before the current date, the event has already happened and can be deleted
            if enddate < currentdate:
                # get the picture associated with the event, if applicable
                photo = db.execute("SELECT picture FROM events WHERE event_id=:event_id", event_id=event_id)
                # if there is a picture for the event
                if photo[0]["picture"] != "":
                    # get the picture
                    picture = photo[0]["picture"]
                    # split the picture's destination to access the filename
                    destination = picture.split("/")
                    # access the name of the picture
                    filename = destination[2]
                    # delete the picture from the files
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # delete the event from the database
                db.execute("DELETE FROM events WHERE event_id=:event_id", event_id=event_id)
        # the event does not have a start and end date, only a start date
        else:
            # get the date of the event
            startdate = time.strptime(splitdate[0], "%m/%d/%Y")
            # if the date of the event is before the current date, the event has already happened and can be deleted
            if startdate < currentdate:
                # get the picture associated with the event, if applicable
                photo = db.execute("SELECT picture FROM events WHERE event_id=:event_id", event_id=event_id)
                # if there is a picture for the event
                if photo[0]["picture"] != "":
                    # get the picture
                    picture = photo[0]["picture"]
                    # split the picture's destination to access the filename
                    destination = picture.split("/")
                    # access the name of the picture
                    filename = destination[2]
                    # delete the picture from the files
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # delete the event from the database
                db.execute("DELETE FROM events WHERE event_id=:event_id", event_id=event_id)
    # get the updated events list
    events = db.execute("SELECT * FROM events JOIN clubs on events.club_id=clubs.club_id")
    # display the event feed
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


@app.route("/check-email", methods=["GET"])
def check_email():
    """Return true if email not in use, else false, in JSON format"""
    # get the email from the user input from the form
    new_email = request.args.get("email")
    # get all of the current emails of users
    currentEmails = db.execute("SELECT email FROM users")
    # iterate through each user
    for email in currentEmails:
        # if the email the current user is trying to use already exists, return false and notify them, via the javascript, that the username is taken
        if email["email"] == new_email:
            return jsonify(False)
    # the email is not taken, the user can use it and return true
    return jsonify(True)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    # User reached route via post
    if request.method == "POST":
        # get the users from the database
        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])[0]
        changes = {
            "name": request.form.get("name"),
            "username": request.form.get("username"),
            "email": request.form.get("email"),
        }

        # append club IDs of selected clubs
        subscriptions = user["subscriptions"]
        if subscriptions != None and subscriptions != '':
            subscriptions = parse(subscriptions)
        else:
            subscriptions = []
        new_subscriptions = request.form.getlist("subscriptions")
        if new_subscriptions:
            for club_name in new_subscriptions:
                club_id = db.execute("SELECT club_id FROM clubs WHERE name=:name", name=club_name)[0]["club_id"]
                if club_id not in subscriptions:
                    subscriptions.append(str(club_id))

        # append name of selected preferences
        preferences = user["preferences"]
        if preferences == None or preferences == "":
            preferences = []
        else:
            preferences = parse(preferences)
        new_preferences = request.form.getlist("preferences")
        if new_preferences:
            for pref in new_preferences:
                if pref not in preferences:
                    preferences.append(pref)

        # send permissions email to clubs
        permissions_requests = request.form.getlist("permissions")
        emailList = []
        if permissions_requests:
            for club_name in permissions_requests:
                email = db.execute("SELECT email FROM clubs WHERE name=:name", name=club_name)[0]["email"]
                emailList.append(email)
        send_email(emailList, "Verify Posting Permissions",
                   "Hi! A student has requested to post events on behalf of your club. Please verify their club membership through this link: http://ide50-omidiran.cs50.io:8080/permissions")
        db.execute("UPDATE users SET preferences = :preferences, subscriptions=:subscriptions WHERE id=:user_id",
                   preferences=rejoin(preferences), subscriptions=rejoin(subscriptions), user_id=session["user_id"])

        for change in changes:
            if changes[change] != '':
                db.execute("UPDATE users SET :change = :value WHERE id=:user_id",
                           change=change, value=changes[change], user_id=session["user_id"])

        # Make sure user fills out all fields if they've filled out any
        if request.form.get("password") or request.form.get("new-password") or request.form.get("confirmation"):
            if not request.form.get("password"):
                return render_template("error.html", message="Must provide password")
            elif not request.form.get("new-password"):
                return render_template("error.html", message="Must provide new password")
            elif not request.form.get("confirmation"):
                return render_template("error.html", message="Must confirm password")

            rows = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id=session["user_id"])
            if not check_password_hash(rows[0]["hash"], request.form.get("password")):
                return render_template("error.html", message="Invalid password")
            else:
                if request.form.get("new-password") == request.form.get("confirmation"):
                    db.execute("UPDATE users SET hash = :hashedpass WHERE id = :user_id",
                               hashedpass=generate_password_hash(request.form.get("new-password")), user_id=session["user_id"])
                    return redirect("/")
                else:
                    return render_template("error.html", message="New passwords do not match")
        flash("Settings successfully updated")
        return redirect("/settings")

    # User reached route via get
    else:
        # get relevant tables
        user = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])[0]
        clubs = db.execute("SELECT * FROM clubs")

        # error-checking for no preferences/subscriptions/permissions
        subscriptions = user["subscriptions"]
        if subscriptions != None and subscriptions != '':
            subscriptions = [int(x) for x in parse(user["subscriptions"])]
        else:
            subscriptions = []
        permissions = user["permissions"]
        if permissions == None or permissions == '':
            permissions = []
        else:
            permissions = parse(permissions)

        # initialize empty arrays
        not_subbed = []
        subbed = []
        preferences = []
        not_preferences = []

        # populate arrays based on if the user hasn't already indicated preference
        for club in clubs:
            if club["club_id"] in subscriptions:
                subbed.append(club["name"])
            else:
                not_subbed.append(club["name"])
        for preference in all_preferences:
            if user["preferences"] != None and user["preferences"] != '':
                if preference in parse(user["preferences"]):
                    preferences.append(preference)
                else:
                    not_preferences.append(preference)
            # if user has no preferences
            else:
                not_preferences.append(preference)
        return render_template("settings.html", user=user, clubs=clubs, subscriptions=subbed, not_subscribed=not_subbed, preferences=preferences, not_preferences=not_preferences, permissions=permissions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # from problem set 8 - finance

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="Must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="Must provide password")

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
    # from problem set 8 - finance

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # from our own implementation in problem set 8 - finance but with new features

    # user reached route via post
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
            emailList = []
            for club in permissions:
                email = db.execute("SELECT email FROM clubs WHERE name=:name", name=club)[0]["email"]
                emailList.append(email)
            send_email(emailList, "Verify Posting Permissions",
                       "Hi! A student has requested to post events on behalf of your club. Please verify their club membership through this link: http://ide50-carissawu.cs50.io:8080/permissions")

        # If insertion returns null, then username must be taken
        result = db.execute("INSERT INTO users (username, hash, name, email, preferences, permissions) VALUES(:username, :hashed, :name, :email, :preferences, :permissions)",
                            username=username, hashed=generate_password_hash(password), name=name, email=email, preferences=rejoin(preferences), permissions=None)
        # Return the relevant error
        if not result:
            return render_template("error.html", message="Username is taken")
        # get the user from the database
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        # store the user id
        session["user_id"] = rows[0]["id"]
        # redirect to index
        return redirect("/")
    # user reached route via get
    else:
        # show the register form
        return render_template("register.html", clubs=db.execute("SELECT name FROM clubs"), preferences=all_preferences)


@app.route("/clubs", methods=["GET", "POST"])
@login_required
def clubs():
    # the user reached the route via get get
    if request.method == "GET":
        # get the clubs from the database
        clubs = db.execute("SELECT * FROM clubs")
        # get the subscriptions for the current user
        row = db.execute("SELECT subscriptions FROM users WHERE id = :user_id", user_id=session["user_id"])[0]
        subscriptions = row["subscriptions"]
        # if the user has subscriptions, create list with row values casted to int
        if subscriptions != None and subscriptions != '':
            subscriptions = [int(x) for x in parse(row["subscriptions"])]
        # if the user has no subscriptions, create an empty list
        else:
            subscriptions = []
        # calculate number of clubs to access index when iterating in html
        num = len(clubs)
        # display clubs page
        return render_template("clubs.html", clubs=clubs, num=num, subscribed_clubs=subscriptions)
    # the user reached the route via post
    else:
        # get the user input for subscription
        subscription = request.form.get("subscribe")
        # create a blank list to store clubs in
        clubsList = []
        # select the user from the database
        row = db.execute("SELECT * FROM users WHERE id = :user_id",
                         user_id=session["user_id"])[0]
        # if the user has subscriptinos
        if row["subscriptions"] != None and row["subscriptions"] != "":
            clubsList = parse(row["subscriptions"])
            # if the user is not already subscribed to the club, add it to their subscriptions
            if subscription not in clubsList:
                clubsList.append(subscription)
        # if the user is not subscribed to any clubs, add the club to a blank list
        else:
            # update the user's subscriptions
            clubsList.append(subscription)
        db.execute("UPDATE users SET subscriptions = :subscriptions WHERE id = :user_id",
                   user_id=session["user_id"], subscriptions=rejoin(clubsList))
        # redirect to index
        return redirect("/")


@app.route("/search")
def search():
    # get the word or letter the user is searching
    q = "'%" + request.args.get("q") + "%'"
    # get clubs that have similar names to the searched word or letter
    results = db.execute("SELECT * FROM clubs WHERE name LIKE " + q)
    # return the clubs that match the search to the webpage to be displayed
    return jsonify(results)


@app.route("/calendar", methods=["GET", "POST"])
@login_required
def calendar():
    # display the calendar
    return render_template("calendar.html")


@app.route("/eventsearch", methods=["GET"])
@login_required
def searchevent():
    # get all of the possible tags and clubs
    tagNames = all_preferences
    clubs = db.execute("SELECT name FROM clubs")
    # display the event search form
    return render_template("eventsearch.html", tags=tagNames, clubs=clubs)


@app.route("/eventsearchtag")
@login_required
def eventsearchtag():
    # get the tag the user wants to search by
    tag = request.args.get("tag")
    # create a blank list to store the events with that tag in
    taggedevents = []
    # get all of the events from the database
    events = db.execute("SELECT * FROM events")
    # loop through the events
    for event in events:
        # get the tags for the event from the database
        eventtags = event["tags"]
        # separate the string of tags into a list
        eventtags = parse(eventtags)
        # create a blank dictionary to store the event information in if it matches the event search
        taggedevent = {}
        # if the searched tag is in the event tags
        if tag in eventtags:
            # add the event information to the dictionary
            taggedevent.update(event)
            # add the dictionary to the list of all matching events
            taggedevents.append(taggedevent)
    # return the list of events that match the search to the webpage to be displayed
    return jsonify(taggedevents)


@app.route("/eventsearchclub")
@login_required
def eventsearchclub():
    # get the club the user wants to search by
    club = request.args.get("club")
    # get all of the clubs from the database
    clubdata = db.execute("SELECT * FROM clubs WHERE name=:name", name=club)
    # create a blank list ot store the events hosted by that club in
    clubevents = []
    # get all of the events from the database
    events = db.execute("SELECT * FROM events")
    # loop through the events
    for event in events:
        # get the hosting club id for the event
        club_id = event["club_id"]
        # create a blank dictionary to store the event information in if it matches the club search
        clubevent = {}
        # if the searched club is hosting the event
        if club_id == clubdata[0]["club_id"]:
            # add the event information to the dictionary
            clubevent.update(event)
            # add the dictionary to the list of all matching events
            clubevents.append(clubevent)
    # return the list of events that match the search to the webpage to be displayed
    return jsonify(clubevents)


@app.route("/eventsearchtitle")
@login_required
def eventsearchtitle():
    # get the word or letter the user is searching
    q = "'%" + request.args.get("q") + "%'"
    # get events that have similar names to the searched word or letter
    results = db.execute("SELECT * FROM events WHERE title LIKE " + q)
    # return the events that match the search to the webpage to be displayed
    return jsonify(results)


@app.route("/preferences", methods=["POST"])
@login_required
def preferences():
    # get the preferences for the user
    preferences = db.execute("SELECT preferences FROM users WHERE id = :user_id", user_id=session["user_id"])
    # if the user has no preferences
    if preferences[0]["preferences"] == None or preferences[0]["preferences"] == "":
        # return a blank event feed
        return render_template("index.html", events=[])
    # create a blank list to store the events in
    events = []
    # loop through the user preferences
    for preference in parse(preferences[0]["preferences"]):
        # if the preferences of the user match the tags of an event
        if db.execute("SELECT * FROM events WHERE instr(tags, :preference) > 0", preference=preference) != []:
            # add the event to the list
            events += (db.execute("SELECT * FROM events WHERE instr(tags, :preference) > 0", preference=preference))
    # return the events with the same tags as the user's preferences
    return render_template("index.html", events=events)


@app.route("/permissions", methods=["GET", "POST"])
@login_required
def permissions():
    # user reached route via post
    if request.method == "POST":
        # get the club the user input
        club = request.form.get("userclub")
        # if the user did not provide a club, return an error instructing them to do so
        if not club:
            return render_template("error.html", message="You must provide your club")
        # get the name of the user that was input
        user = request.form.get("nameofuser")
        # if a user's name was not provided, return an error instructing them to do so
        if not user:
            return render_template("error.html", message="You must provide the user you want to give permissions to")
        # get the current permissions of the user who was selected from the database
        permissions = db.execute("SELECT permissions FROM users WHERE name = :name", name=user)
        # start a blank list to update their permissions
        updatePermissions = []
        # if the user does not currently have any permissions
        if permissions[0]["permissions"] == None:
            # set their permissions equal to the club name
            permissions[0]["permissions"] = club
            # append the list with the club name which they now have permissions for
            updatePermissions.append(club)
        # if the user already has permissions for some clubs
        else:
            # get their current permissions and put them into a list
            updatePermissions = parse(permissions[0]["permissions"])
            # add their new permissions to the list
            updatePermissions.append(club)
        # update their permissions in the database as a string separating the club names with commas
        db.execute("UPDATE users SET permissions=:permissions WHERE name=:name", permissions=rejoin(updatePermissions), name=user)
        return render_template("calendar.html")
    # user reached route via get
    else:
        # get all of the clubs
        clubs = db.execute("SELECT name FROM clubs")
        # get all of the users
        users = db.execute("SELECT name FROM users")
        # display the correct webpage with the clubs and users filled into the form
        return render_template("permissions.html", clubs=clubs, users=users)


@app.route("/createevent", methods=["GET", "POST"])
@login_required
def createevent():
    # Create the list of possible tags for events
    tagNames = all_preferences
    # user reached route via post
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

        # verify that the user has permission to post for the club they are trying to post for
        permissions = db.execute("SELECT permissions FROM users WHERE id = :user_id", user_id=session["user_id"])
        for i in range(len(parse(permissions[0]["permissions"]))):
            # if the user has permission for the club allow them to post
            if parse(permissions[0]["permissions"])[i] == club:
                break
            # if the user does not have permission return an error
            if i == len(parse(permissions[0]["permissions"]))-1:
                return render_template("error.html", message="Sorry, but you do not have permission to post events for this club. Request permissions on settings in order to be authorized to post events.")

        # convert to military time to put into calendar
        if startampm == "pm" and int(starthour) != 12:
            # get the end hour in the proper format for the Google Calendar event
            starthourmilitary = int(starthour) + 12
            starthourmilitary = str(starthourmilitary)
        else:
            starthourmilitary = starthour
        if endampm == "pm" and int(endhour) != 12:
            # get the end hour in the proper format for the Google Calendar event
            endhourmilitary = int(endhour) + 12
            endhourmilitary = str(endhourmilitary)
        else:
            endhourmilitary = endhour

        # format the start date and time and end date and time for the Google Calendar event
        startdateandtime = startyear + "-" + startmonth + "-" + startday + "T" + starthourmilitary + ":" + startminutes + ":00-05:00"
        enddateandtime = endyear + "-" + endmonth + "-" + endday + "T" + endhourmilitary + ":" + endminutes + ":00-05:00"

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
                   club_id=club_id[0]["club_id"], title=title, description=description, picture=picturelink, tags=rejoin(tags), date=eventdate, time=eventtime, location=location)

        # The file service.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        SERVICE_ACCOUNT_FILE = '/home/ubuntu/workspace/final-project/service.json'
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = googleapiclient.discovery.build('calendar', 'v3', credentials=credentials)
        # create event based on user input
        event = {
            'summary': title,
            'location': location,
            'description': description,
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
        # add the event to the calendar
        event = service.events().insert(calendarId='cs50projectchi@gmail.com', body=event).execute()

        # get the email and subscriptions from users
        rows = db.execute("SELECT email, subscriptions FROM users WHERE subscriptions IS NOT NULL")
        # create an empty list of recipients
        emailList = []
        # loop through each each user
        for row in rows:
            # if the user has subscriptions
            if row["subscriptions"] != None and row["subscriptions"] != "":
                # get a list of subscriptions
                clubsList = parse(row["subscriptions"])
                # if the club is in the list of clubs the user is subscribed to, add their email to the group to email
                if str(club_id[0]["club_id"]) in clubsList:
                    emailList.append(row["email"])
        # send the email
        send_email(emailList, "New event posted by one of your clubs",
                   "One of the clubs you subscribe to just posted a new event. Check it out at http://ide50-omidiran.cs50.io:8080!")
        # redirect to index
        return redirect("/")
    # user reached route via get
    else:
        # get the permission for the user
        userpermissions = db.execute("SELECT permissions FROM users WHERE id=:id", id=session["user_id"])
        # if the user has no permissions, they can not access the page
        if userpermissions[0]["permissions"] == None or userpermissions[0]["permissions"] == "":
            return render_template("error.html", message="You do not have permissions to post for any clubs. Please wait for your club to approve of your club membership")
        # store the club names
        clubs = db.execute("SELECT name FROM clubs")
        # store the months
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        # return the template for creating an event with relevant information
        return render_template("createevent.html", clubs=clubs, tags=tagNames, months=months)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return render_template("error.html", message=e.name)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
