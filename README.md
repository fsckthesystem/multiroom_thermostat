# Multiroom Thermostat
Control your thermostat with multiple sensor nodes using Raspberry Pis

## Pre-requisites

### Hardware
At least 1 Raspberry Pi, but multiple is recommended.
A relay board with at least 3 relays
DHT11 or DHT22 (I recommend the DHT22 as it has a margin of error of .5C where the DHT11 is 2C) 

Please be sure to research which wires are for your system and how to wire them up. I am not an HVAC technician, so please don't take my word as fact, but from what I have researched, this is what I found:
```
Y = AC
W = Furnace
H = Heat pump
G = Fan
R = Power
```
You will need to connect R(power) to each relay's normally open terminal.
On each of the 3 relays common terminal, you will need to connect your heating wire, cooling wire, and your fan wire.

This software only currently supports heating/cooling/fan or '4 wire' systems with no reserve heating or cooling setups as that is what I have and what I can test on. If you need something other than that, you can fork this project and have a go at adjusting it to work with other systems. Hopefully my code comments aren't too terrible!

### Software
You will need to install 2 packages from pip: RPi.GPIO and Adafruit-Python-DHT


first we will make sure pip3 is up-to-date

```sudo -H pip3 install --upgrade pip```


For the Raspberry Pi that will be controlling the relay that interfaces with the AC/Heating system:

```sudo pip3 install RPi.GPIO```


For the temperature sensor Raspberry Pis and if you have a temperature sensor connected Raspberry Pi controlling the relay:

```sudo pip3 install adafruit-python-dht```


## Usage
There are 2 programs you will use; One for the controller Raspberry Pi and one for Raspberry Pis with the temperature sensor connected to it.
`sensor_node.py` what to run on each temperature sensor Raspberry Pis and `thermostat_server.py` on the controller Raspberry Pi.


### thermostat_server.py
Inside this file, you will likely need to modify some of the constants in the code to match which pins you are using for the relay, min and max desired temps, and the IP address of the Raspberry Pi you are running it on. (Currently trying to figure out how get the IP address programmically without just getting the loopback address)
After that is configured to your liking, you just need to run it with root access so it can access and control GPIO pins:

```sudo python3 thermostat_server.py```

### sensor_node.py
Inside this file, you will need to change the the constant SERVER_HOSTNAME to the name of the Raspberry Pi that is running `thermostat_server.py` and change DHT_PIN to the pin the sensor is connected to.
After that is configured, you can start it with:

```sudo python3 sensor_node.py "<name_of_room>"```

with `<name of room>` being a unique name for the room you have the node in.

# Note
This software is still being developed and is likely very buggy. Please use with caution.
