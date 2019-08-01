import urllib.request as urllib2
import json
import datetime
stock_names_file = open("short_stock_names.json", "r")
stock_names = json.load(stock_names_file)
stock_names_file.close()
price_data = {}

price_data = {}

for stock_code in stock_names.keys():            #looking for the stock codes
    curr_stock = {}
    i = stock_names[stock_code]
    if (i[-1].isdigit() or i[-2].isdigit() or '%' in i or '$' in i) or 'SEC' in i[-3:] or i[-1].upper() == i[-1]:           #all those with numbers at the back don't pay out dividends, either warrents, bonds or perpetual securities, later thinking of removing non-stocks from the stock list anyway
        continue
    try:            #may not have the stock price, there are non trade bonds in the list too
        cookievals = {"cmp":"t=1529903335&j=0",
                      "GUC":"AQEBAQFbHwhb_0IhPwSt&s=AQAAAKva2sLM&g=Wx3CVw",
                      "B":"ba6edjpdgk75n&b=3&s=pp",
                      "PRF":"t%3D{0}.SI%252BYHOO".format(i)}
        opener = urllib2.build_opener()
        opener.addheaders.append(('Cookie', "; ".join('%s=%s' % (k,v) for k,v in cookievals.items())))
        price_file = opener.open("https://query1.finance.yahoo.com/v7/finance/download/{0}.SI?period1=0&period2=9999999999&interval=1d&events=history&crumb=JS.OMyPro5z".format(stock_code))
    except Exception as e:
        continue
    #for prices, first element ignored since its just the column names
    price_file = price_file.read().decode()
    prices = [k.split(',') for k in price_file.split('\n')[1:]]         #splits the lines into the different section, 2D array first is by the date then within each first level element is the different types of prices
    for j in prices:
        if len(j) < 5 or j[4] == "null" or j[5] == "null" or float(j[4]) == 0 or float(j[5]) == 0:     #no trading in the share for that day, will not be present in dataset
            continue
        #dash removed to save space
        curr_stock[j[0].replace("-", "")] = [float(j[4]), float(j[5]), float(j[6])]     #gives the close (j[4]) and the adjusted close (j[5]) 
    print (stock_names[stock_code])   #some visual indication that something is being done
    price_data[stock_code] = curr_stock  #index is the stock code
with open("price_data.json", "w") as file:
    file.write(json.dumps(price_data))
