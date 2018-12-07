from bs4 import BeautifulSoup
from cs50 import SQL
import requests

db = SQL("sqlite:///ClubPub.db")

# Get HTML from OSL and convert to BeautifulSoup format
site = requests.get("https://fas-mini-sites.fas.harvard.edu/osl/grouplist")
content = site.content
soup = BeautifulSoup(content, features="lxml")

# Find links to get to individual pages for clubs
links = [link.get('href') for link in soup.find_all('a')]

# Iterate through links and navigate to pages
for link in links:
    tempSite = requests.get("https://fas-mini-sites.fas.harvard.edu/osl/grouplist" + link)
    tempSoup = BeautifulSoup(tempSite.content, features="lxml")

    name = tempSoup.find('h2').get_text()
    purpose = tempSoup.find('p').get_text()

    li_all = tempSoup.find_all('li')
    result = []

    for li in li_all:
        result.extend(li.find_all('a'))
    category = result[0].get_text()
    email = result[1].get_text()
    if not (db.execute("SELECT name FROM clubs WHERE name = :name", name=name)):
        db.execute("INSERT INTO clubs (name, email, category, purpose) VALUES(:name, :email, :category, :purpose)",
        name=name, email=email, category=category, purpose=purpose)




