import Adafruit_DHT
import time
import socket

UDP_IP = socket.gethostbyname("jetsonnano")
UDP_PORT = 4815
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4
ROOM = "Office"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None:
        print("Temp={0:0.1f}C Humidity={1:0.1f}%".format(temperature, humidity))
        message = str.encode("{0}, {1:0.1f}, {2:0.1f}".format(ROOM, temperature, humidity))
        sock.sendto(message, (UDP_IP, UDP_PORT))
    else:
        print("Sensor failure. Check wiring.");
    time.sleep(3)
