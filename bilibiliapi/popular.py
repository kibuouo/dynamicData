import Myfetch 
fetch = Myfetch.Fetch()
url="https://api.bilibili.com/x/web-interface/popular"

result = fetch.get('https://api.bilibili.com/x/web-interface/popular/region?ps=20&pn=1&rid=0')

print(result)