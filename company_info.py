#NEED TO ACCOUNT FOR DIFFERENT REPORTING CURRENCIES

from html.parser import HTMLParser
import urllib.request as urllib2
from datetime import date
import json
import http.client as httplib
import sys

stock_codes = json.load(open("short_stock_codes.json", "r"))     #need to run stock_codes.py 
nodata = sorted(stock_codes.keys())
httplib.HTTPConnection._http_vsn = 10
httplib.HTTPConnection._http_vsn_str = 'HTTP/1.0'
company_info = {}
currency_codes = open("currency_code_updated_4March2017.txt", "r").readlines()
#rates only from euro
raw_rates = json.loads(urllib2.urlopen("http://data.fixer.io/api/latest?access_key=ba572c710328817f97e8854ae9fe5f22").read().decode("ISO-8859-1"))["rates"]
rates = {}
for i in raw_rates.keys():
    rates[i] = raw_rates[i] / raw_rates["SGD"]

for i in range(len(currency_codes)):
    currency_codes[i] = currency_codes[i].strip()

class IncomeParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.span = 0   #currently in span element
        self.net_profit_recording = 0 #recording net profit
        self.net_profit = []
        self.date_recording = 0
        self.date = []
        self.revenue_recording = 0
        self.revenue = []
        self.currency = ""
        self.currency_recording = 0

    def handle_starttag(self, tag, attr):
        if tag == "span":
            self.span = 1

    def handle_data(self, data):
        if data.strip() and self.span:
            if data == "Net income from continuing ops":
                self.net_profit_recording = 1
            elif self.net_profit_recording:
                if data == '-':
                    self.net_profit.append("N/A")
                else:
                    self.net_profit.append(float(data.strip().replace(',', ''))*1000/rates[self.currency])
            elif data == "Revenue":   #get the dates
                self.date_recording = 1
            elif self.date_recording:
                if data == "-":
                    self.date.append("N/A")
                else:
                    self.date.append(data.strip())
            elif data == "Total revenue":
                self.revenue_recording = 1
            elif self.revenue_recording:
                if data == "-":
                    self.revenue.append("N/A")
                else:
                    self.revenue.append(float(data.strip().replace(',', ''))*1000/rates[self.currency])
            elif data == "Income statement":
                self.currency_recording = 1
            elif self.currency_recording:  #need to find a way to catch the currency more easily
                for i in data.split():
                    if i.replace(".", "") in currency_codes:
                        print (data)
                        self.currency = i.replace(".", "")
                    if i == "Currency":
                        self.currency_recording = 0
                    
                
    def handle_endtag(self,tag):
        if tag == "tr":
            self.net_profit_recording = 0
            self.date_recording = 0
            self.revenue_recording = 0
            self.span = 0
            self.minority_interest_recording = 0
        if tag == "div":
            if self.currency == "":  #default case
                self.currency = "SGD"

class AssetsParser(HTMLParser):
    def __init__(self, currency):
        HTMLParser.__init__(self)
        self.span = 0   #currently in span element
        self.cash_recording = 0 #recording net profit
        self.cash = []
        self.debt_recording = 0 #more values than 1 because have 2 rows for debt (short/long term)
        self.debt = []
        self.assets_recording = 0  #look only at tangible assets
        self.assets = []
        self.currency = currency
        

    def handle_starttag(self, tag, attr):
        if tag == "span":
            self.span = 1

    def handle_data(self, data):
        if data.strip() and self.span:
            if data == "Cash and cash equivalents":
                self.cash_recording = 1
            elif self.cash_recording:
                if data == '-':
                    self.cash.append("N/A")
                else:
                    self.cash.append(float(data.strip().replace(',', ''))*1000/rates[self.currency])
            elif data == "Short/current long-term debt" or data == "Long-term debt":   #special case for debt since have 2 rows 
                self.debt_recording = 1
            elif self.debt_recording:
                if len(self.debt) < self.debt_recording:
                    self.debt.append(0)
                if data != "-":   #take - as 0, so can ignore it
                    self.debt[self.debt_recording - 1] += float(data.strip().replace(',', ''))*1000/rates[self.currency]
                self.debt_recording  += 1   #so it is added to the right column
            elif data == "Net tangible assets":
                self.assets_recording = 1
            elif self.assets_recording:
                if data == "-":
                    self.assets.append("N/A")
                else:
                    self.assets.append(float(data.strip().replace(',', ''))*1000/rates[self.currency])
                
    def handle_endtag(self,tag):
        if tag == "tr":
            self.cash_recording = 0
            self.debt_recording = 0
            self.assets_recording = 0
            self.span = 0

class StatsParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.shares_recording = 0
        self.shares = 0

    def handle_starttag(self, tag, attr):
        if self.shares_recording and tag == "td":
            self.shares_recording += 1

    def handle_data(self, data):
        if data == "Shares outstanding":
            self.shares_recording = 1
        elif self.shares_recording == 2:  #got an element there in the same box, a footnote
            if data[-1] == "B":  #convert symbols to numbers
                self.shares = int(float(data[:-1]) * 1000000000)
            elif data[-1] == "M":
                self.shares = int(float(data[:-1]) * 1000000)
            elif data == "N/A":
                self.shares = "N/A"
            else:
                self.shares = "N/A, less than 1 million shares"
            self.shares_recording = 0


while nodata:
    i = nodata[0]
    if (i[-1].isdigit() or i[-2].isdigit() or '%' in i or '$' in i) or 'SEC' in i[-3:] or i[-1].upper() == i[-1]:           #all those with numbers at the back don't pay out dividends, either warrents, bonds or perpetual securities, later thinking of removing non-stocks from the stock list anyway
        del nodata[0]
        continue        #alternatively bonds also have an A or R at the end, so need to check if all stocks do not have those at the end
    income_url = "https://sg.finance.yahoo.com/quote/{0}.SI/financials?p={0}.SI".format(stock_codes[i])
    assets_url = "https://sg.finance.yahoo.com/quote/{0}.SI/balance-sheet?p={0}.SI".format(stock_codes[i])
    stats_url = "https://sg.finance.yahoo.com/quote/{0}.SI/key-statistics?p={0}.SI".format(stock_codes[i])
    try:
        income_file = urllib2.urlopen(income_url).read().decode("ISO-8859-1")
        assets_file = urllib2.urlopen(assets_url).read().decode("ISO-8859-1")
        stats_file = urllib2.urlopen(stats_url).read().decode("ISO-8859-1")
    except:
        continue
           #i have no idea, just that this works for some characters that can't be decoded by utf-8
    incomeparser = IncomeParser()
    incomeparser.feed(income_file)
    currency = incomeparser.currency
    assetsparser = AssetsParser(currency)
    assetsparser.feed(assets_file)
    statsparser = StatsParser()
    statsparser.feed(stats_file)

    company_info[stock_codes[i]] = {}
    company_info[stock_codes[i]]["Net Profit"] = incomeparser.net_profit
    company_info[stock_codes[i]]["Date"] = incomeparser.date
    company_info[stock_codes[i]]["Revenue"] = incomeparser.revenue
    company_info[stock_codes[i]]["Currency"] = currency
    company_info[stock_codes[i]]["Cash"] = assetsparser.cash
    company_info[stock_codes[i]]["Debt"] = assetsparser.debt
    company_info[stock_codes[i]]["Net Tangible Assets"] = assetsparser.assets
    company_info[stock_codes[i]]["Shares Oustanding"] = statsparser.shares
    print (i)
    del nodata[0]

    with open("company_info.json", "w") as outfile:
        outfile.write(json.dumps(company_info))

