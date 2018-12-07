import requests
import urllib.parse
import smtplib

from flask import redirect, render_template, request, session
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def parse(text):
    """Splits SQL text into list. Text should be delimited by a comma."""
    # Make sure that there's text to be split
    if text == None:
        return text
    return text.split(',')

def rejoin(textList):
    """Rejoins list into comma-delimited string for storage in database."""
    return ','.join(textList)

def send_email(recipients, subject, body):
    """Sends email given recipients list, subject line, and body message.
    https://stackabuse.com/how-to-send-emails-with-gmail-using-python/"""
    # Store login info
    gmail_user = 'cs50projectchi@gmail.com'
    gmail_password = 'carissahunterife'

    # Build message in format needed for gmail
    email_text = "\r\n".join([
      "From: " + gmail_user,
      "To: " + ",".join(recipients),
      "Subject: " + subject,
      "",
       body
      ])


    try:
        # Open server
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipients, email_text)
        server.close()
    except:
        return None