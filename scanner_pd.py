from bs4 import BeautifulSoup
import sys
import json
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Setting up google chrome environment
options = webdriver.ChromeOptions()
options.headless = True
options.add_argument("--window-size=1920,1080")
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")

driver = webdriver.Chrome(ChromeDriverManager().install(), options = options)
# Today date
today = datetime.datetime.now()
# Uploading airport database
f = open("airports.json", encoding="utf8")
data = json.load(f)


def eval_route(date, departure_f, destination_f):
    import time

    date = date.strftime("%Y-%m-%d")[:10]

    url = f"https://www.kayak.co.uk/flights/{departure_f}-{destination_f}/{date}/?sort=bestflight_a"
    print(url)

    driver.get(url)
    # Time sleep to allow website fully download
    time.sleep(15)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    # Check in case no flight were found
    notfound = soup.find("div", class_="IVAL-title")
    if notfound is not None:
        print("\nNo flights found\n")
        sys.exit()
    # Check in case of error
    error = soup.find("ul", class_="errorMessages").text
    if len(error) != 0:
        print("\n" + error)
        print("\nTry again\n")
        sys.exit()

    # Div element of all flights
    elements = soup.find_all("div", class_="nrc6-inner")

    dest_lst = []

    # Loop through each div/flight and fill in dataframe
    for element in elements:
        dest_temp = []
        ans = ""
        block = element.find("div", "vmXl vmXl-mod-variant-large")
        price = element.find("div", "f8F1-price-text-container").text
        price = price.replace(" ", "")
        price = price.replace(",", "")
        time = block.find_all("span")
        duration = element.find("div", class_="xdW8 xdW8-mod-full-airport").text
        stop_div = element.find("div", class_="JWEO")
        stops = stop_div.find_all("span")
        for i in time:
            if len(i.text) > 1:
                dest_temp.append(i.text)
        for s in stops:
            temp = s.text.replace(",", "")
            temp = temp.strip()
            if s.text not in ans:
                ans = ans + " " + temp
                if len(s.text) >= 7 and stops[0] != s:
                    ans = ans + "(Change airport)"
        dest_temp.append(departure_f)
        dest_temp.append(destination_f)
        dest_temp.append(duration)
        dest_temp.append(ans)
        dest_temp.append(int(price[1:]))
        dest_temp.append(date)
        dest_lst.append(dest_temp)
    data = pd.DataFrame(dest_lst,
                        columns=["departure_time", "arrival_time", "from", "to", "duration", "change", "price","day"])

    return data


def daterange(start, end):
    '''Return list of dates from "start" to "end" '''
    lst = []
    for n in range(int((end - start).days)+1):
        lst.append(start + datetime.timedelta(n))
    return lst


def eval_prices(file):
    '''Calculates average price for the following route'''
    prices = np.array(file.price)
    return np.amin(prices), np.mean(prices), np.amax(prices)


# Start Date of departure
while True:
    start_date = input("Start date(YYYY-MM-DD): ")
    start_date = start_date.replace(" ","")
    try:
        datetime.date.fromisoformat(start_date)
    except ValueError:
        print("Incorrect date format, it should be YYYY-MM-DD")
        continue
    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    if start_date<today:
        print("You cannot choose past date")
        continue
    break
# End Date of departure
while True:
    end_date = input("End date(YYYY-MM-DD): ")
    end_date = end_date.replace(" ","")
    try:
        datetime.date.fromisoformat(end_date)
    except ValueError:
        print("Incorrect date format, it should be YYYY-MM-DD")
        continue
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    if end_date<today:
        print("You cannot choose past date")
        continue
    break
# Choosing departure
while True:
    departure = input("\nFrom: ").lower()
    dest = 0
    for i in data:
        if data[i]["city"].lower() == departure:
            dest+=1
            print(i + " " + data[i]["name"])
            departure_f = i
    if dest>1:
        departure_f = input("Choose airport: ").upper()
        if departure_f.upper() not in data:
            print("No such airport on the list ")
            continue
        break
    elif dest == 0:
        print("No city was found, try again")
        continue
    break
# Choosing destination
while True:
    destination = input("\nTo: ").lower()
    dest = 0
    for i in data:
        if data[i]["city"].lower() == destination:
            dest+=1
            print(i + " " + data[i]["name"])
            destination_f = i
    if dest>1:
        destination_f = input("Choose airport: ").upper()
        if destination_f.upper() not in data:
            print("No such airport on the list ")
            continue
        break
    elif dest == 0:
        print("No city was found, try again")
        continue
    if destination_f == departure_f:
        print("\nDestination and departure should be unique\n")
        continue
    break
# Close the airport database
f.close()

print("\nLoading...\n")
# Create figure
fig = plt.figure(figsize=(12,6))
plt.title(f"{departure.capitalize()} - {destination.capitalize()}")
df = []
# Loop over each date
for single_date in daterange(start_date, end_date):
    # Convert datetime object to string as y-parameter
    temp_date = datetime.datetime.strftime(single_date, "%Y-%m-%d")
    # Create data
    data = eval_route(single_date, departure_f, destination_f)
    # Append data for future concatenation
    df.append(data)
    min_val, mean_val, max_val = eval_prices(data)
    row = data.loc[data.price == min_val]
    print(f"Cheapest offer on this day: {row.departure_time.values[0]} - {row.arrival_time.values[0]} {row.duration.values[0]} {row.change.values[0]} £{row.price.values[0]}\n")
    plt.plot(temp_date, min_val, "go")
    plt.plot(temp_date, mean_val, "bo")
    plt.plot(temp_date, max_val, "ro")


result = pd.concat(df)
print(result)
fig.autofmt_xdate()
plt.ylabel("Price/£")
plt.legend(["Minimum", "Mean", "Maximum"], loc="upper right")
plt.tight_layout()
plt.show()


driver.quit()