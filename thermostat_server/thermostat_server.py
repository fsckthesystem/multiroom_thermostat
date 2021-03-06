import RPi.GPIO as GPIO
import socket
import time
import threading
import math
import datetime
from collections import deque
from itertools import combinations

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM) # set pin naming scheme to rpi

UDP_IP = "192.168.100.137" # server ip
UDP_PORT = 4815 # server port

# set up socket
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.bind((UDP_IP, UDP_PORT))

# set up pins
FANPIN = 22
HEATPIN = 17
COOLPIN = 10

PINS = [HEATPIN, COOLPIN, FANPIN]

# this is for easier readability
RELAYOFF = GPIO.HIGH
RELAYON = GPIO.LOW

# Tempurature range
TEMPHIGH = 76
TEMPLOW = 69

# Using deques as they can have a fixed number and drop off the oldest
# when a new value is added.
# This gives make getting a rolling average easier

### TODO: Make a dictionary that use the room name as the key and the value being a deque.
### This will make it easier to add new rooms dynamically instead of having to hard
### program it in.

DEQUELENGTH = 20 # size of the deques

rolling_temps = {}
rolling_hums = {}

last_received = {}

def main():
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
        checking_thread.start()
        run()

    # Catch ctrl-c and cleanly exit program
    except KeyboardInterrupt:
        print("\nQuiting...\nCleaning up...\n")
        checking_thread.join(1)
        collecting_thread.join(1)
        GPIO.cleanup()


# collects incoming data from nodes and sorts into correct deque
def data_collection():
    while True:
        data, addr = SOCK.recvfrom(1024) # buffer size is 1024 bytes
        message = data.decode()
        loc, temp, hum = message.split(", ")
        temp = (float(temp) * 1.8) + 32 # convert from C to F

        if loc not in rolling_temps:
            rolling_temps[loc] = deque(DEQUELENGTH*[((TEMPHIGH + TEMPLOW)/2)], DEQUELENGTH)
        if loc not in rolling_hums:
            rolling_hums[loc] = deque(DEQUELENGTH*[40], DEQUELENGTH)
        
        rolling_temps[loc].appendleft(temp)
        rolling_hums[loc].appendleft(hum)
        last_received[loc] = datetime.datetime.utcnow()


def node_check():       
        # check if the nodes have stopped sending data; if one has, set data to the average
        # TEMPHIGH and TEMPLOW, and humidity to 40%
    time.sleep(7)
    while True:
        if len(last_received) > 0:
            for loc in dict(last_received):
                if (datetime.datetime.utcnow() - last_received[loc]).total_seconds() >= 600:
                    rolling_temps.pop(loc)
                    rolling_hums.pop(loc)
                    last_received.pop(loc)
        else:
            print("No nodes found. Please check that nodes are running.")

        time.sleep(6)


def run():
    print("Starting thermostat")
    time.sleep(7)
    # loop to check rolling average of room temps and to set systems accordingly
    while True:

        loc_temp_avg = {}
        above_temphigh = False
        below_templow = False
        loc_temp_diff = 0
        
        if len(rolling_temps) > 0:
            for loc in rolling_temps:
                loc_temp_avg[loc] = sum(rolling_temps[loc])/len(rolling_temps[loc])
                if loc_temp_avg[loc] > TEMPHIGH:
                    above_temphigh = True
                elif loc_temp_avg[loc] < TEMPLOW:
                    below_templow = True
            if len(rolling_temps) > 1:
                loc_temp_diff_tuple = max(combinations(loc_temp_avg, 2), key = lambda temps: abs(loc_temp_avg[temps[0]] - loc_temp_avg[temps[1]]))
                loc_temp_diff = loc_temp_avg[loc_temp_diff_tuple[1]] - loc_temp_avg[loc_temp_diff_tuple[0]]

        if loc_temp_diff > 3:
            print("Temps vary too much; toggling fan on")
            GPIO.output(HEATPIN, RELAYOFF)
            GPIO.output(COOLPIN, RELAYOFF)
            GPIO.output(FANPIN, RELAYON)
            time.sleep(300)

        elif below_templow:
            print("Temp is low; toggling heat on")
            GPIO.output(COOLPIN, RELAYOFF)
            GPIO.output(FANPIN, RELAYON)
            GPIO.output(HEATPIN, RELAYON)
            time.sleep(300)

        elif above_temphigh:
            print("Temp is high; toggling cooling on")
            GPIO.output(HEATPIN, RELAYOFF)
            GPIO.output(FANPIN, RELAYON)
            GPIO.output(COOLPIN, RELAYON)
            time.sleep(300)
        
        else:
            print("Climate is within set parameters; toggling systems off if any are on")
            GPIO.output(HEATPIN, RELAYOFF)
            GPIO.output(COOLPIN, RELAYOFF)
            GPIO.output(FANPIN, RELAYOFF)
            time.sleep(120)



def init():
    print("initializing...")
    print("setting relays off")
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, RELAYOFF)



if __name__ == '__main__':
    main()

