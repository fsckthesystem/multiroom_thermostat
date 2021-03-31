"""
A multiroom thermostat controller
"""

import socket
import time
import threading
import datetime
from copy import copy
from collections import deque
import RPi.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM) # set pin naming scheme to rpi

# If you are running Debian (including Raspbian/Raspberry Pi OS) or Ubuntu,
# you will either need to remove the "127.0.1.1 <hostname>" from your
# /etc/hosts file, or change UDP_IP to the host's IP address manually below
UDP_IP = socket.gethostbyname(socket.gethostname()) # server ip
UDP_PORT = 4815 # server port

# set up socket
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.bind((UDP_IP, UDP_PORT))

# set up pins
## Change these pins to match what you are using
FANPIN = 22
HEATPIN = 17
COOLPIN = 10

PINS = [HEATPIN, COOLPIN, FANPIN]

# this is for easier readability
RELAYOFF = GPIO.HIGH
RELAYON = GPIO.LOW

# Tempurature range
TEMPHIGH = 76
TEMPLOW = 70
TEMPMID = (TEMPHIGH + TEMPLOW) / 2
# rolling_X variables are populated in the data_collection function with
# deques dynamically for each node that receives from.

# Using deques as they can have a fixed number and drop off the oldest
# when a new value is added.
# This gives make getting a rolling average easier


ROLLING_TEMPS = {}
ROLLING_HUMS = {}

DEQUELENGTH = 20 # size of the deques

TEMPDEQUEDEFAULT = deque(DEQUELENGTH*[TEMPMID], DEQUELENGTH)
HUMDEQUEDEFAULT = deque(DEQUELENGTH*[40], DEQUELENGTH)

# Keeps track of time of last received datagram for each location
LAST_RECEIVED = {}


def main():
    """
    Main method
    """
    # Creating thread for receiving climate info from sensor nodes
    collecting_thread = threading.Thread(target=data_collection)
    collecting_thread.daemon = True

    # Creating thread for checking if nodes have sent data in given
    # amount of time.
    checking_thread = threading.Thread(target=node_check)
    checking_thread.daemon = True

    # Start up server
    try:
        init()
        collecting_thread.start()
        time.sleep(30)
        checking_thread.start()
        run()

    # Catch ctrl-c and cleanly exit program
    except KeyboardInterrupt:
        print("\nQuiting...\nCleaning up...\n")
        checking_thread.join(1)
        collecting_thread.join(1)
        GPIO.cleanup()


def init():
    """
    Initializes the GPIO pins
    """
    print("initializing...")
    print("setting relays off")
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, RELAYOFF)


def data_collection():
    """
    collects incoming data from nodes and sorts into correct deque
    """
    print("Detecting nodes")
    while True:
        data = SOCK.recvfrom(1024)[0] # buffer size is 1024 bytes
        message = data.decode()
        loc, temp, hum = message.split(", ")
        temp = (float(temp) * 1.8) + 32 # convert from C to F

        # Checks if location is alreay in the rolling_X dictionarys. If not, it creates an entry
        # in the dictionary and populates it with the defaults
        if loc not in ROLLING_TEMPS:
            ROLLING_TEMPS[loc] = copy(TEMPDEQUEDEFAULT)
            print(loc, "has connected")
        if loc not in ROLLING_HUMS:
            ROLLING_HUMS[loc] = copy(HUMDEQUEDEFAULT)

        # Append new temp and humidity to appropriate deque in dictionaries
        ROLLING_TEMPS[loc].appendleft(temp)
        ROLLING_HUMS[loc].appendleft(hum)
        LAST_RECEIVED[loc] = datetime.datetime.utcnow()


def node_check():
    """
    Checks if any location has sent data in the past 10 mins
    if it has not, it removes location from dictionaries
    """
    while True:
        if LAST_RECEIVED:
            for loc in dict(LAST_RECEIVED):
                if (datetime.datetime.utcnow() - LAST_RECEIVED[loc]).total_seconds() >= 600:
                    ROLLING_TEMPS.pop(loc)
                    ROLLING_HUMS.pop(loc)
                    LAST_RECEIVED.pop(loc)
                    print("connection to", loc, "has been lost")
        else:
            print("No nodes found. Please check that nodes are running.")

        time.sleep(6)


def heat_on():
    """
    Turn heating system on
    """
    print("Temp is low; toggling heat on")
    GPIO.output(COOLPIN, RELAYOFF)
    GPIO.output(FANPIN, RELAYOFF)
    GPIO.output(HEATPIN, RELAYON)
    time.sleep(900)

def cool_on():
    """
    Turn cooling system on
    """
    print("Temp is high; toggling cooling on")
    GPIO.output(HEATPIN, RELAYOFF)
    GPIO.output(FANPIN, RELAYOFF)
    GPIO.output(COOLPIN, RELAYON)
    time.sleep(900)

def fan_on():
    """
    Turn only the fan on
    """
    print("Temps vary too much; toggling fan on")
    GPIO.output(HEATPIN, RELAYOFF)
    GPIO.output(COOLPIN, RELAYOFF)
    GPIO.output(FANPIN, RELAYON)
    time.sleep(300)


def all_off():
    """
    turn all systems off
    """
    print("Climate is within set parameters; toggling systems off if any are on")
    GPIO.output(HEATPIN, RELAYOFF)
    GPIO.output(COOLPIN, RELAYOFF)
    GPIO.output(FANPIN, RELAYOFF)
    time.sleep(120)


def run():
    """
    Starts the thermostat
    """
    print("Starting thermostat")
    # loop to check rolling average of room temps and to set systems accordingly
    while True:
        loc_temp_avg = {}
        above_temphigh = False
        below_templow = False
        loc_temp_diff = 0
        max_temp = -1000
        min_temp = 1000

        # Logic for determining average temp for location, temp differences, and
        # checks for temps below or above set TEMPMAX and TEMPLOW and sets the
        # above variables accordingly
        if ROLLING_TEMPS:
            for loc in ROLLING_TEMPS:
                loc_temp_avg[loc] = sum(ROLLING_TEMPS[loc])/len(ROLLING_TEMPS[loc])
                if loc_temp_avg[loc] > max_temp:
                    max_temp = loc_temp_avg[loc]
                if loc_temp_avg[loc] < min_temp:
                    min_temp = loc_temp_avg[loc]


                print(f"{loc}: {loc_temp_avg[loc]:0.1f}F")
                if loc_temp_avg[loc] > TEMPHIGH:
                    above_temphigh = True
                elif loc_temp_avg[loc] < TEMPLOW:
                    below_templow = True

            loc_temp_diff = max_temp - min_temp

        # Toggles heating on if all temps are below TEMPLOW
        if max_temp < TEMPLOW:
            heat_on()

        # Toggles cooling on if all temps are above TEMPHIGH
        elif min_temp > TEMPHIGH:
            cool_on()

        # Toggles fan on if difference in temps is too much
        elif loc_temp_diff > 3:
            fan_on()

        # Toggles on heat if temp average is too low
        elif below_templow:
            heat_on()

        # Toggles on AC if temp average is too high
        elif above_temphigh:
            cool_on()

        # Toggles everything off if disired conditions are met
        else:
            all_off()


if __name__ == '__main__':
    main()
