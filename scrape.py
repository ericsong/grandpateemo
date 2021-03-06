from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime, timedelta
from pytz import timezone
import pytz
import requests

eastern = timezone('US/Eastern')
pacific = timezone('US/Pacific')

def isNormalSale(sale):
  title = sale[0]
  if("Champion and skin sale" in title):
    return True
  else:
    return False

def isPrice(line):
  if("RP" in line):
    return True
  else:
    return False

def cleanString(str):
  return str.strip()

#might be bug where year is incorrectly set on the new year. too lazy to fix
def extractDates(str):
  loc_dt = eastern.localize(datetime.now())
  pac_dt = loc_dt.astimezone(pacific)
	
  date_strings = str[23:].split('-')
  dates = []
  for date in date_strings:
    dates.append(date.strip().split('.')) 

  start_date = pacific.localize(datetime(pac_dt.year, int(dates[0][0]), int(dates[0][1])))
  end_date = pacific.localize(datetime(pac_dt.year, int(dates[1][0]), int(dates[1][1])))
  return (start_date, end_date)

def scrapeSales(soup):
  container = soup.find("div", "field field-name-body field-type-text-with-summary field-label-hidden")
  title = soup.find_all("h1", "article-title")[0].string
  headers = container.find_all("h4")

  dates = extractDates(title)
  start_date = dates[0]
  end_date = dates[1]

  skinNames = [headers[1].string, headers[2].string, headers[3].string]
  champNames = [headers[5].string, headers[6].string, headers[7].string]

  skinPrices = [  next(filter(isPrice, headers[1].parent.contents)),
                  next(filter(isPrice, headers[2].parent.contents)),
                  next(filter(isPrice, headers[3].parent.contents)) ]
  
  champPrices = [ next(filter(isPrice, headers[5].parent.contents)),
                  next(filter(isPrice, headers[6].parent.contents)),
                  next(filter(isPrice, headers[7].parent.contents)) ]

  skins = []
  champs = []

  for i in range(0,3):
    skins.append((cleanString(skinNames[i]), cleanString(skinPrices[i])))
    champs.append((cleanString(champNames[i]), cleanString(champPrices[i])))

  sale = {
    "skins": skins,
    "champs": champs,
    "start_date": start_date,
    "end_date": end_date
  }

  return sale

def getNewSales():
  #grab page
  data = requests.get("http://na.leagueoflegends.com/en/news/store/sales").text
  soup = BeautifulSoup(data)
  items = soup.find_all("div", "gs-container")
  scraped_sales = []

  #scrape sale data  ("title", "href")
  for item in items:
    temp = item.find("div", "default-2-3")
    if(temp is not None):
      a_link = temp.find("a")
      scraped_sales.append((a_link.string, a_link.get('href')))

  #get currently grabbed sales
  client = MongoClient('localhost', 27017)
  db = client.lolwishlist
  sales = db.sales
  db_sales = []

  for sale in sales.find():
    db_sales.append((sale['title'], sale['href']))

  #find new sales
  new_sales = set(scraped_sales).difference(set(db_sales))

  #filter out non regular sales (for now)
  new_sales = filter(isNormalSale, new_sales)

  return_obj = []

  #do a thing
  for sale in new_sales:
    data = requests.get("http://na.leagueoflegends.com" + sale[1]).text
    soup = BeautifulSoup(data) 
    scraped_data = scrapeSales(soup)

    return_obj.append({
      "href": sale[1],
      "title": sale[0],
      "skins": scraped_data["skins"],
      "champs": scraped_data["champs"],
      "start_date": scraped_data['start_date'],
      "end_date": scraped_data['end_date']
    })

  return return_obj
