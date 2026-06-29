"""
if-else,for,range,while,break,continue
"""
price = 1500.0
volume = 100000
change_pct=2.5

if change_pct>5:
  print("大涨")
elif change_pct>0:
  print("小涨")
elif change_pct==0:
  print("横盘")
elif change_pct>-5:
  print("小跌")
else:
  print("大跌")

if(100<price<2000) and (volume>50000) and( change_pct>0):
  print("符合条件")
else:
  print("不符合条件")

stocks=["茅台","五粮液","招商银行"]
stock_info = {
    "code": "600519",
    "name": "贵州茅台",
    "price": 1500.0,
    "change": 2.5
}
for stock in stocks:
  print(f"股票：{stock}")
for i in range(1,11):
  print(f"i=:{i}")
for key,value in stock_info.items():
  print(f"{key}:{value}")

count=0
while count<5:
  print(f"count:{count}")
  count+=1

for i in range(10):
  if i==5:
    break
  print(f"i:{i}")

for i in range(10):
  if i==2:
    continue
  print(f"i:{i}")