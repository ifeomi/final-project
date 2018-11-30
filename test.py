from bs4 import BeautifulSoup
import requests

site = requests.get("https://fas-mini-sites.fas.harvard.edu/osl/grouplist")