"""
list,dict
"""
fruits=["apple","banana","cherry"]

print(fruits[0])
print(fruits[1:3])
print(len(fruits))
print(max(fruits))
print(min(fruits))
print(sorted(fruits))
print(reversed(fruits))
print(fruits.index("banana"))
print(fruits.count("banana"))

person={
  "name":"json",
  "age":"abc"
}
print(person["name"])
print(person["age"])
print(person.get("name"))
print(person.get("age"))
print(person.keys())
print(person.values())

squares=[]
for i in range(1,11):
  squares.append(i**2)
print(f"{squares}")
squares2=[i**2 for i in range(1,11) if i%2==0]
print(f"{squares2}")

prices = {"苹果": 5, "香蕉": 3, "橙子": 4}
discounted={}
for fruit,price in prices.items():
  discounted[fruit]=price*0.9
print(f"{discounted}")
discounted2={fruit:price*0.8 for fruit,price in prices.items()}
print(f"{discounted2}")