from lxml import html
import requests

page = requests.get('https://fas-mini-sites.fas.harvard.edu/osl/grouplist')
tree = html.fromstring(page.content)
