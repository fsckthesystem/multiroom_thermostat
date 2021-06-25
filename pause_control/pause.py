import socket


UDP_IP = socket.gethostbyname("bebop")
UDP_PORT = 4815

SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

SOCK.sendto(str.encode("cpause"), (UDP_IP, UDP_PORT))
