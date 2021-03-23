#
# This code is originally by Mike Murray (@TheGeekPub) from https://www.thegeekpub.com/236867/using-the-dht11-temperature-sensor-with-the-raspberry-pi/
#
# I have slightly modified it to meet the requirements of my project.
#



import time
import socket
import sys
import Adafruit_DHT


if len(sys.argv) != 3:
    print("Usage: python3 sensor_node.py \"<room name>\" \"<server hostname>\"")
    sys.exit()

ROOM = sys.argv[1]
SERVER_HOSTNAME = sys.argv[2]
UDP_IP = socket.gethostbyname(SERVER_HOSTNAME)
UDP_PORT = 4815
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4


SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


while True:
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None:
        print("Temp={0:0.1f}C Humidity={1:0.1f}%".format(temperature, humidity))
        message = str.encode("{0}, {1:0.1f}, {2:0.1f}".format(ROOM, temperature, humidity))
        try:
            SOCK.sendto(message, (UDP_IP, UDP_PORT))

        except:
            print("Network Error")


    else:
        print("Sensor failure. Check wiring.")
    time.sleep(3)
