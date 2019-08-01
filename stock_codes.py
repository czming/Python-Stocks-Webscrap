#this updates the stock_codes.json and stock_names.json files
import urllib.request
import json                 #use http://infopub.sgx.com/Apps?A=COW_App_DB&B=isincodedownload&F=1 to find stock codes
                            #when comparing the company, may want to capitalize since I've noticed that this data is not the same capitalization as the SGX one
fileobj = urllib.request.urlopen("http://infopub.sgx.com/Apps?A=COW_App_DB&B=isincodedownload&F=1").readlines()
fileobj = fileobj[1:]
code_dict = {}                  
file = open("stock_codes.json", "w")
for i in range(len(fileobj)):
    fileobj[i] = fileobj[i].decode("utf-8")
    fileobj[i] = fileobj[i].split('  ')
    j = 0
    while j < len(fileobj[i]):
        if fileobj[i][j] == '':
            del fileobj[i][j]
            continue
        fileobj[i][j] = fileobj[i][j].strip()
        j += 1
for i in fileobj:
    if len(i[2]) > 4:                   #filtering those with long stock codes that based on previous runs have shown to not have price nor dividends
        del i                           #deleting so next run won't have to deal with it
        continue
    code_dict[i[0]] = i[2]
file.write(json.dumps(code_dict))
file.close()
file = open("stock_names.json", "w")
for i in fileobj:
    code_dict[i[2]] = i[0]
file.write(json.dumps(code_dict))
file.close()
