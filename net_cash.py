import json
import datetime
from math import log10

def round_sig(number, sig_fig):                     #for rounding number to a certain sf
    number = float(number)
    if number == 0:
        position = 0
    else:
        position = -int(log10(abs(number))//1)-1 + sig_fig
    return round(number, position)

stock_codes = json.load(open("stock_codes.json", "r")).values()
stock_names_temp = json.load(open("stock_codes.json", "r"))
short_stock_names = json.load(open("short_stock_names.json", "r"))
stock_names = {}
for i in stock_names_temp.keys():
    stock_names[stock_names_temp[i]] = i
price_data = json.load(open("price_data.json", "r"))
company_info = json.load(open("company_info.json", "r"))
dividend_data = json.load(open("dividends.json", "r"))
processed_data = {}

for i in stock_codes:

    date = datetime.datetime.today()
    if i in price_data.keys() and price_data[i] != {}:
        today = datetime.datetime.strftime(date, "%Y%m%d")
        while today not in price_data[i].keys():  #trying to find current price by checking if today is in the list (then going back one day if not)
            date = date - datetime.timedelta(days = 1)
            today = datetime.datetime.strftime(date, "%Y%m%d")  #can just sort and take the highest value too
    else:
        continue
    if len(price_data[i].keys()) > 10:
        recent_price_dates = sorted(list(price_data[i].keys()))[-10:]
    else:  #if have less than 10 days of trading data
        recent_price_dates = sorted(list(price_data[i].keys()))
    value_traded = 0 #volume for past 10 days or less
    days = 0
    for date in recent_price_dates:
        value_traded += price_data[i][date][2] * price_data[i][date][0]
        days += 1
    avg_value_traded = value_traded / days
    price = price_data[i][today][0]
    if i not in company_info.keys() or company_info[i]["Shares Oustanding"] == 0:
        continue
    if len(company_info[i]["Cash"]) > 0 and type(company_info[i]["Shares Oustanding"]) is int:
        if company_info[i]["Cash"][0] == "N/A" or company_info[i]["Debt"][0] == "N/A":
            continue
        cash = (company_info[i]["Cash"][0] - company_info[i]["Debt"][0]) / company_info[i]["Shares Oustanding"]
    else:
        continue
    if len(company_info[i]["Net Tangible Assets"]) > 0:
        if company_info[i]["Net Tangible Assets"][0] == "N/A":
            continue
        assets = (company_info[i]["Net Tangible Assets"][0]) / company_info[i]["Shares Oustanding"]
    else:
        continue
    if len(company_info[i]["Net Profit"]) > 0:
        avg_profit = 0
        weightage = [0.45, 0.35, 0.15, 0.05] #weighs more recent profit as more important
        weights = 0
        for j in range(len(company_info[i]["Net Profit"])):
            if company_info[i]["Net Profit"][j] == "N/A":
                continue
            avg_profit += company_info[i]["Net Profit"][j] * weightage[j]
            weights += weightage[j]     #the weights used, cause company might not have been operating for all 4 years
        if weights == 0: #no profit recorded, all N/A
            continue
        avg_profit = (avg_profit / weights)/company_info[i]["Shares Oustanding"]
    if i in dividend_data.keys():
        weight = 0
        avg_dividend = 0
        years = sorted(dividend_data[i].keys())  #sorted from earliest to latest
        if len(years) > 10:
            years = years[-10:]
        years.remove("currency")
        if str(datetime.datetime.today().year) in years:  #remove current year (since it might be early and they haven't paid yet
            years.remove(str(datetime.datetime.today().year))
        weightage = [i ** 2 for i in range(len(years))]
        prev_div = 0   #tracking previous dividend
        change_div = 0
        for j in range(len(years)):  
            curr_div = dividend_data[i][years[j]]
            avg_dividend += curr_div * weightage[j]
            weight += weightage[j]
            if prev_div == 0: #0 division error, just started paying dividends, no increase noted
                prev_div = curr_div
                continue
            if j != 0:  #don't want to count the first year, otherwise its always a 100% increase from prev_div = 0
                if curr_div < prev_div:  #paid less than previous year
                    change_div -= ((prev_div - curr_div) * weightage[j] * 2 / prev_div)  #added greater weightage for r, shows company not stable/not doing well
                elif curr_div > 2 * prev_div:  #limit the increase to 100%, beyond that is irrelevant
                    change_div += weightage[j]
                else:  #credits increase in dividend too
                    change_div += (curr_div - prev_div) * weightage[j] / prev_div
            prev_div = curr_div
        if avg_dividend == 0:  #never paid dividend before, not interested in them
            continue
        if int(years[-1]) < datetime.datetime.today().year - 1: #if last year no dividend then we take it as a complete drop
            change_div -= weightage[j]   #the full amount times 2
        change_div = change_div / weight
        avg_dividend = avg_dividend / weight
    else:
        continue
    processed_data[i] = {"Current Price": price}
    processed_data[i]["Avg Value"] = round_sig(avg_value_traded,3)
    processed_data[i]["Net Cash"] = round_sig(cash, 5)
    processed_data[i]["Avg Profit"] = round_sig(avg_profit, 5)
    processed_data[i]["Currency"] = company_info[i]["Currency"]
    processed_data[i]["Avg Dividend"] = round_sig(avg_dividend, 5)
    processed_data[i]["Dividend Change"] = round_sig(change_div, 5)
    processed_data[i]["Tangible Equity"] = round_sig(assets, 5)

valuation_dict = {}

for i in processed_data.keys():
    if processed_data[i]["Avg Value"] < 10000:  #if less than $10000 worth of trade in past 10 trading dats, pass, too little volume to invest
        continue
    if processed_data[i]["Avg Dividend"] > processed_data[i]["Avg Profit"]:
        #if company pays more dividend than profit
        curr_dividend = processed_data[i]["Avg Profit"]
    else:
        curr_dividend = processed_data[i]["Avg Dividend"]
    if processed_data[i]["Net Cash"] > 0:
        valuation = processed_data[i]["Net Cash"] * 0.6 + processed_data[i]["Tangible Equity"] * 0.05 + processed_data[i]["Avg Profit"] * 7 + (1 + processed_data[i]["Dividend Change"]) * curr_dividend * 12
    else:
        valuation = processed_data[i]["Net Cash"] * 0.3 + processed_data[i]["Tangible Equity"] * 0.05 + processed_data[i]["Avg Profit"] * 7 + (1 + processed_data[i]["Dividend Change"]) * curr_dividend * 12
    valuation_dict[i] = {"Value Ratio": valuation / processed_data[i]["Current Price"]}
    valuation_dict[i]["Valuation"] = valuation

sorted_valuation = sorted(valuation_dict.keys(), key = lambda x : valuation_dict[x]["Value Ratio"])

for i in sorted_valuation:
    if processed_data[i]["Current Price"] >= 0.2:
        print ("{0:30s} {1:4s} {2:.5f} {3:.5f} {4:.3f} {5:.0f} {6}".format(stock_names[i], i, processed_data[i]["Current Price"], valuation_dict[i]["Valuation"], valuation_dict[i]["Value Ratio"], processed_data[i]["Avg Value"], processed_data[i]["Currency"]))

while True: #for queries
    query = input("Input query: ")
    query = query.split()
    if len(query) != 2:
        print ("Invalid query")
        continue
    ticker = None
    for i in query:
        if not ticker:
            ticker = ""
            for j in i:
                if j.isalpha():
                    ticker += j.upper()
                else:
                    ticker += j
        try:
            if i == "p":
                data = processed_data[ticker]
                print ("Company Information: {0} ({1})".format(short_stock_names[ticker], ticker))
                for i in data.keys():
                    print (i + " : " + str(data[i]))
            elif i == "d":
                data = dividend_data[ticker]
                print ("Company Dividends: {0} ({1})".format(short_stock_names[ticker], ticker))
                for i in data.keys():
                    print (i + " : " + str(data[i]))
            elif i == "w":
                with open("starred_shares.txt", "r+") as infile:
                    code_in = False
                    for line in infile.readlines():
                        if line.split()[0] == ticker:
                            code_in = True
                            break
                    if not code_in:
                        infile.write("{0} {1}\n".format(ticker, short_stock_names[ticker]))
                        print ("Stock code added to file")
                    else:
                        print ("Stock code already in file")
                        
        except KeyError:
            print ("Invalid stock code")
            break

