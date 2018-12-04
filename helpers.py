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
    return text.split(',')

def rejoin(textList):
    """Rejoins list into comma-delimited string for storage in database."""
    return ','.join(textList)

def send_email(recipients, subject, body):
    """Sends email given recipients list, subject line, and body message.
    https://stackabuse.com/how-to-send-emails-with-gmail-using-python/"""
    gmail_user = 'cs50projectchi@gmail.com'
    gmail_password = 'carissahunterife'

    sent_from = gmail_user

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.sendmail(sent_from, recipients, body)
        server.close()
    except:
        return None