from cs50 import SQL
from helpers import parse, send_email
import datetime
import time

starthour = "01"
startminutes = "30"
startampm = "am"
endhour = "01"
endminutes = "30"
endampm = "pm"

starttime = starthour + ":" + startminutes + startampm
endtime = endhour + ":" + endminutes + endampm
formattedstarttime = time.strptime(starttime, "%I:%M%p")
formattedendtime = time.strptime(endtime, "%I:%M%p")
print(formattedstarttime)
print(formattedendtime)