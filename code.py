import ipaddress
import ssl
import wifi
import socketpool
import adafruit_requests
import rtc
import time
import alarm
import json
from adafruit_magtag.magtag import MagTag
import traceback
import sys

TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"
JSON_QUOTES_URL = "https://www.adafruit.com/api/quotes.php"

op_count = 0

def connectWifi():
    # Get wifi details and more from a secrets.py file
    try:
        from secrets import secrets
    except ImportError:
        print("WiFi secrets are kept in secrets.py, please add them there!")
        raise

    wifi.radio.connect(secrets["ssid"], secrets["password"])

def getWeatherJson(requests):
    url = "https://api.weather.gov/gridpoints/LWX/86,83/forecast"
    response = requests.get(url)
    weather = json.loads(response.text)
    return weather

def weatherTask(requests, MAGTAG):

    weather = getWeatherJson(requests)
    string = ""
    count = 0
    for period in weather["properties"]["periods"]:
        name = period["name"]
        short_forcast = period["shortForecast"]
        temperature = period["temperature"]
        temperature_unit = period["temperatureUnit"]

        string = string + f"{name}: {temperature} {temperature_unit}; {short_forcast}\t"
        count = count + 1

        if count > 4:
            break
    weather_pixels = magtag.add_text(
    text_scale=1,
    text_wrap=40,
    text_maxlen = 300,
    text_position=(0,10),
    text_anchor_point=(0,0))

    MAGTAG.set_text(string, weather_pixels)
    
    # date_pixels = MAGTAG.add_text(
    #     text_scale=1,
    #     text_wrap=20,
    #     text_maxlen=128,
    #     text_position=(10,50),
    #     text_anchor_point=(0,0))
    # generationTime = time.strptime(weather["properties"]["generatedAt"])


    # MAGTAG.set_text(generationTime, date_pixels)
    

def quotesTask(requests):
    print("Fetching json from", JSON_QUOTES_URL)
    response = requests.get(JSON_QUOTES_URL)
    quote = json.loads(response.text)
    print(f"Current Quote: {quote[0]["text"]}")


if __name__ == "__main__":
    connectWifi()

    magtag=MagTag()

    
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    try:
        quotesTask(requests)
    except:
        print("Unable to retrieve any quotes.")

    try:
        weatherTask(requests, magtag)
    except Exception:
        print(traceback.print_exception())
        print("Weather task failed.")

    
    if alarm.wake_alarm is None:
        alarm.sleep_memory[0] = 0
    else:
        alarm.sleep_memory[0] = alarm.sleep_memory[0] + 1

    count_pixels = magtag.add_text(
    text_scale=1,
    text_wrap=30,
    text_maxlen = 300,
    text_position=(100,0),
    text_anchor_point=(0,0))

    magtag.set_text(f"Count: {alarm.sleep_memory[0]}", count_pixels)

    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + (60*15))

    alarm.exit_and_deep_sleep_until_alarms(time_alarm)