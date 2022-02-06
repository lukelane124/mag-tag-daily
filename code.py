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

JSON_QUOTES_URL = "https://www.adafruit.com/api/quotes.php"
TIME_URL = "http://worldtimeapi.org/api/ip"

SLEEP_TIME = (60*6)

if alarm.wake_alarm is None:
    alarm.sleep_memory[0] = 1
    alarm.sleep_memory[1] = 0
else:
    alarm.sleep_memory[0] = alarm.sleep_memory[0] + 1

connectFailure = False

def connectWifi():
    # Get wifi details and more from a secrets.py file
    ret = [None, None]
    try:
        from secrets import secrets
    except ImportError:
        print("WiFi secrets are kept in secrets.py, please add them there!")
        raise

    try:
        wifi.radio.connect(secrets["ssid"], secrets["password"])
        pool = socketpool.SocketPool(wifi.radio)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())
        ret = [pool, requests]

    except Exception as error:
        print("Failed to connect to wifi")
        alarm.sleep_memory[1] = alarm.sleep_memory[1] + 1
        print(traceback.print_exception(Exception, error, None))
        connectFailure = True

    return ret



def getUnixTimeStamp(requests):
    ret = 0
    try:
        response = requests.get(TIME_URL)
        time = json.loads(response.text)
        ret = time["unixtime"]
    
    except Exception as error:
        print("Failed to get Unix Time.")
        print(traceback.print_exception(etype=Exception, value=error, tb=None))
        alarm.sleep_memory[1] = alarm.sleep_memory[1] + 1
    
    return ret


def getWeatherJson(requests):
    url = "https://api.weather.gov/gridpoints/LWX/86,83/forecast"
    response = requests.get(url, headers={'user-agent': 'km4lvw-MT-daily-MD/0.0.1'})
    weather = json.loads(response.text)
    print(f"{weather=}")
    with open("weather.json", "w") as outFile:
        outFile.write(json.dumps(weather))
        print(json.dumps(weather))
        outFile.close
    return weather

def weatherTask(requests, MAGTAG):
    try:
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
        weather_pixels = MAGTAG.add_text(
        text_scale=1,
        text_wrap=40,
        text_maxlen = 300,
        text_position=(0,10),
        text_anchor_point=(0,0))

        MAGTAG.set_text(string, weather_pixels)

    except Exception as error:
        print("Weather task failed.")
        print(traceback.print_exception(etype=Exception, value=error, tb=None))
        alarm.sleep_memory[1] = alarm.sleep_memory[1] + 1


def quotesTask(requests):
    try:
        print("Fetching json from", JSON_QUOTES_URL)
        response = requests.get(JSON_QUOTES_URL)
        quote = json.loads(response.text)
        print(f"Current Quote: {quote[0]["text"]}")
    except:
        print("Unable to retrieve any quotes.")
        alarm.sleep_memory[1] = alarm.sleep_memory[1] + 1

def printStatsTask(magtag):
    count_pixels = magtag.add_text(
    text_scale=1,
    text_wrap=38,
    text_maxlen = 300,
    text_position=(0,0),
    text_anchor_point=(0,0))

    magtag.set_text(f"Loops: {alarm.sleep_memory[0]}\tFailures: {alarm.sleep_memory[1]}\tSleepSecs: {SLEEP_TIME}\tVoltage: {magtag.peripherals.battery} ", count_pixels)

def timeTask(requests, MAGTAG):
    if alarm.sleep_memory[0] == 1:
        unixTime = getUnixTimeStamp(requests)
        if unixTime != 0:        
            r = rtc.RTC()
            print(f"{r.datetime=}")
            global rtcTimeStruct
            rtcTimeStruct = r.datetime
            rtcTime = time.mktime(rtcTimeStruct)

            if (abs(rtcTime - unixTime) > 2):
                print("Setting the RTC time.")
                r.datetime = time.localtime(unixTime)

    timeNow = rtc.RTC().datetime
    time_pixels = MAGTAG.add_text(
        text_scale=0,
        text_wrap=40,
        text_maxlen = 300,
        text_position=(0,73),
        text_anchor_point=(0,0))

    string = f"{timeNow.tm_year}/{timeNow.tm_mon}/{timeNow.tm_mday}-{timeNow.tm_hour}:{timeNow.tm_min}:{timeNow.tm_sec}"
    MAGTAG.set_text(string, time_pixels)


def main():
    [pool, requests] = connectWifi()
    
    if connectFailure is False:
        magtag=MagTag()

        
        # pool = socketpool.SocketPool(wifi.radio)
        # requests = adafruit_requests.Session(pool, ssl.create_default_context())

        print("Handling Time")
        timeTask(requests, magtag)

        print("Getting Quote")
        quotesTask(requests)
        
        print("Getting Weather")
        weatherTask(requests, magtag)
        
        print("Collecting Stats")
        printStatsTask(magtag)


if __name__ == "__main__":
    import storage
    storage.remount("/",False)
    main()
    storage.remount("/",True)

    # Update the weather 10 times an hour.
    time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + SLEEP_TIME)

    alarm.exit_and_deep_sleep_until_alarms(time_alarm)    