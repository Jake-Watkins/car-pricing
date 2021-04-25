#import gspread
#from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
from urllib.request import urlopen, Request
from selenium import webdriver
from selenium.common.exceptions import WebDriverException,TimeoutException,ElementNotInteractableException, ElementClickInterceptedException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.firefox.options import Options
import time
import pyodbc

connStr = ""

carLists = ["https://www.autotempest.com/results?make=subaru&radius=300&zip=98004&maxprice=8000&transmission=man",
            "https://www.autotempest.com/results?make=chevrolet&model=corvette&radius=300&zip=98004&transmission=man",
            "https://www.autotempest.com/results?make_kw=&radius=300&zip=98092&minyear=2008&minprice=3000&maxprice=15000&minmiles=1&maxmiles=200000&bodystyle=sedan&saleby=dealer",
            "https://www.autotempest.com/results?make_kw=&radius=300&zip=98092&minyear=2008&minprice=3000&maxprice=15000&minmiles=1&maxmiles=200000&bodystyle=coupe&saleby=dealer",
            "https://www.autotempest.com/results?make_kw=&radius=300&zip=98092&minyear=2008&minprice=3000&maxprice=15000&minmiles=1&maxmiles=200000&bodystyle=hatchback&saleby=dealer"]
perYearInfo = "https://www.edmunds.com/"


def connect():
    
    try:
        return pyodbc.connect(connStr)
    except :
        input("Whitelist this IP and continue")
        return pyodbc.connect(connStr)

def atoi(table):
    try:
        rtn = []
        for i in table:
            line = []
            for j in i:
                val = int(j.replace("$","").replace(",","").replace(".","").replace("mi","").strip())
                line.append(val)
            rtn.append(line)
        return rtn
    except ValueError:
        print(ValueError)
        print(table)
        return [[]]

'''args = [make, model, year]'''
def getYearlyCostURL(args):
    return perYearInfo + '/'.join(args) + '/cost-to-own/'

def getYearlyCostTable(args):
    cap = DesiredCapabilities().FIREFOX
    options = Options()
    ##options.add_argument('-headless')
    driver = webdriver.Firefox(capabilities = cap, options= options)
    try:
        webpath = getYearlyCostURL(args)
        print(webpath)
        driver.implicitly_wait(30)
        driver.get(webpath)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table",{"class":"costs-table text-gray-darker table table-borderless"})
        rows= table.findAll("tr")
        ##[title, depreciation, taxes, financing, fuel, insurance, maintenance, repairs, true cost to own]
        rtn = []
        for row in rows:
            item = row.find("td",{"class":"font-weight-bold"})
            try:
                rtn.append(int(item.get_text().replace("$","").replace(",","").replace(".","").replace("mi","").strip()))
            except:
                rtn.append(-1)
                print("lomo")
    except:
        rtn = [-1,-1,-1,-1,-1,-1,-1,-1,-1]
        print('rip')
    driver.close()
    driver.quit()
    return rtn


def splitymm(ymm):
    try:
        strings = ymm.split(' ')
        return [strings[0],strings[1].lower(),strings[2].lower()]
    except IndexError:
        return [' ',' ',' ']
def loadEntireResults(carLists):
    entries = []
    for cars in carLists:
        cap = DesiredCapabilities().FIREFOX
        options = Options()
        ##options.add_argument('-headless')
        driver = webdriver.Firefox(capabilities = cap, options= options)
        driver.implicitly_wait(30)
        driver.get(cars)
        attempts = 0
        foundButton = True
        while foundButton :
            buttons = driver.find_elements_by_class_name("more-results")
            try:
                time.sleep(1)
                buttons[attempts].click()
            
            except (ElementNotInteractableException, ElementClickInterceptedException, WebDriverException):
                driver.execute_script("return arguments[0].scrollIntoView();", buttons[attempts])
                attempts = attempts + 1

            except IndexError:
                foundButton = False
        soup = BeautifulSoup(driver.page_source, "html.parser")
        listOfCars = soup.findAll("div",{"class":"description-wrap"})
        driver.close()
        driver.quit()
        for entry in listOfCars:
            ymm = entry.find("a").get_text().strip()
            [year, make, model] = splitymm(ymm)
            if year==' ':
                print(ymm)
            
            link = entry.find("a")['href']
            try:
                price = atoi([[entry.find("div",{"class":"price"}).get_text()]])
            except :
                #eBaybids
                price = -1
            try:
                mileage = atoi([[entry.find("span",{"class":"info mileage"}).get_text()]]) 
            except :
                #eBay cars
                mileage = -1
            car = [[make, model, year],link,price,mileage]
            #print(car)
            entries.append(car)  
    return entries

def doesNotExist(car, cnxn, cursor):
    query = "select count(*) from Cost where url = \'{}\'".format(car[1])
    cursor.execute(query)
    for row in cursor.fetchall():
        print(row)
        if row[0] == 0:
            print('zero!')
            return True
    return False

def addToTable(car, costTable, cnxn, cursor):
    query = "insert into Cost(Make, Model, Year, purchase_price, url, Insurance, Maintenance, Repairs, Taxes, Financing, Depreciation, Fuel, Total_Cost, Mileage, Title) values (\'{0}\', \'{1}\', {2}, {3}, \'{4}\', {5}, {6}, {7}, {8}, {9}, {10}, {11}, {12}, {13}, {14})".format(car[0][0],car[0][1],car[0][2],car[2][0][0],car[1],costTable[5],costTable[6],costTable[7],costTable[2],costTable[3],costTable[1],costTable[4],costTable[8],car[3][0][0],costTable[0])
    print(query)
    cursor.execute(query)
    cnxn.commit()
    
            
cars = loadEntireResults(carLists)
print(len(cars))
cnxn = connect()
cursor = cnxn.cursor()
for car in cars:
    time.sleep(1)
    args = car[0]
    try:
        if(doesNotExist(car,cnxn,cursor)):
            costTable = (getYearlyCostTable(args))
            ##(Make varchar(20), Model varchar(50), Year INT, purchase_price INT, url varchar(150), Insurance INT,
            ## Maintenance INT, Repairs INT, Taxes INT, Financing INT, Depreciation INT, Fuel INT, Total_Cost INT, Mileage INT, Title INT)

            ##[[make, model, year],link,price,mileage]
            ##[title, depreciation, taxes, financing, fuel, insurance, maintenance, repairs, true cost to own]
            addToTable(car, costTable, cnxn, cursor)
            time.sleep(60)
    except AttributeError:
        print(car)
    except TimeoutException:
        time.sleep(10)
        costTable = (getYearlyCostTable(args))
    except:
        print('lmao')
        print(args)
