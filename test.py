from cs50 import SQL
from helpers import parse

db = SQL("sqlite:///ClubPub.db")

userpermissions = db.execute("SELECT permissions FROM users WHERE id=:id", id="2")
print(userpermissions[0]["permissions"])
if userpermissions[0]["permissions"] == None:
    print("You do not have permission")
else:
    print("You have permission")