import RPi.GPIO as GPIO
import socket
import time
import threading
import math
import datetime
from collections import deque

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
TEMPHIGH = 78
TEMPLOW = 69

# Using deques as they can have a fixed number and drop off the oldest
# when a new value is added.
# This gives make getting a rolling average easier

### TODO: Make a dictionary that use the room name as the key and the value being a deque.
### This will make it easier to add new rooms dynamically instead of having to hard
### program it in.

DEQUELENGTH = 15 # size of the deques

rolling_temp_living_room = deque(DEQUELENGTH*[(TEMPHIGH + TEMPLOW) / 2], DEQUELENGTH)
rolling_hum_living_room = deque(DEQUELENGTH*[40], DEQUELENGTH)
rolling_temp_office = deque(DEQUELENGTH*[(TEMPHIGH + TEMPLOW) / 2], DEQUELENGTH)
rolling_hum_office = deque(DEQUELENGTH*[40], DEQUELENGTH)

lr_last_received = datetime.datetime.utcnow()
off_last_received = datetime.datetime.utcnow()


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

    global lr_last_received
    global off_last_received
    while True:
        data, addr = SOCK.recvfrom(1024) # buffer size is 1024 bytes
        message = data.decode()
        loc, temp, hum = message.split(", ")
        temp = (float(temp) * 1.8) + 32 # convert from C to F
        if loc == "Living Room":
            lr_last_received = datetime.datetime.utcnow()
            rolling_temp_living_room.appendleft(temp)
            rolling_hum_living_room.appendleft(hum)
        if loc == "Office":
            off_last_received = datetime.datetime.utcnow()
            rolling_temp_office.appendleft(temp)
            rolling_hum_office.appendleft(hum)
       

def node_check():       
        # check if the nodes have stopped sending data; if one has, set data to the average
        # TEMPHIGH and TEMPLOW, and humidity to 40%
    while True:

        lr_diff = datetime.datetime.utcnow() - lr_last_received
        if lr_diff.total_seconds() >= 600:
            print("Lost contact with Living Room")
            rolling_temp_living_room = deque(DEQUELENGTH*[((TEMPHIGH + TEMPLOW)/2)], DEQUELENGTH)
            rolling_hum_living_room = deque(DEQUELENGTH*[40], DEQUELENGTH)
        
        off_diff = datetime.datetime.utcnow() - off_last_received
        if off_diff.total_seconds() >= 600:
            print("Lost contact with Office")
            rolling_temp_office = deque(DEQUELENGTH*[((TEMPHIGH + TEMPLOW)/2)], DEQUELENGTH)
            rolling_hum_office = deque(DEQUELENGTH*[40], DEQUELENGTH)
        time.sleep(60)


def run():
    print("Starting thermostat")
    
    # loop to check rolling average of room temps and to set systems accordingly
    while True:
        lr_avg = sum(rolling_temp_living_room)/len(rolling_temp_living_room)
        off_avg = sum(rolling_temp_office)/len(rolling_temp_office)

        if abs(lr_avg - off_avg) > 3:
            print("Temps vary too much; toggling fan on")
            GPIO.output(HEATPIN, RELAYOFF)
            GPIO.output(COOLPIN, RELAYOFF)
            GPIO.output(FANPIN, RELAYON)
            time.sleep(300)

        elif lr_avg < TEMPLOW or off_avg < TEMPLOW:
            print("Temp is low; toggling heat on")
            GPIO.output(COOLPIN, RELAYOFF)
            GPIO.output(FANPIN, RELAYON)
            GPIO.output(HEATPIN, RELAYON)
            time.sleep(300)

        elif lr_avg > TEMPHIGH or off_avg > TEMPHIGH:
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


def prep():
    print("Populating buffers")
    while None in rolling_temp_living_room or None in rolling_temp_office:
        data, addr = SOCK.recvfrom(1024) # buffer size is 1024 bytes
        message = data.decode()
        loc, temp, hum = message.split(", ")
        temp = (float(temp) * 1.8) + 32
        if loc == "Living Room":
            rolling_temp_living_room.appendleft(temp)
            rolling_hum_living_room.appendleft(hum)
        if loc == "Office":
            rolling_temp_office.appendleft(temp)
            rolling_hum_office.appendleft(hum)


def init():
    print("initializing...")
    print("setting relays off")
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, RELAYOFF)



if __name__ == '__main__':
    main()

