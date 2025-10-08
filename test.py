import requests
H = {"User-Agent":"Mozilla/5.0"}
print(requests.get("https://query1.finance.yahoo.com/v1/finance/search",
                   params={"q":"apple","quotesCount":5,"newsCount":0},
                   headers=H, timeout=(5,8)).status_code)
print(requests.get("https://query2.finance.yahoo.com/v1/finance/search",
                   params={"q":"apple","quotesCount":5,"newsCount":0},
                   headers=H, timeout=(5,8)).status_code)
