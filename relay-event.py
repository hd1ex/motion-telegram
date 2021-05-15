#!/usr/bin/python

import socket
import sys

server_address = '/tmp/motion-telegram'
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

event = ' '.join(sys.argv[1:])

sock.connect(server_address)
sock.sendall(event.encode('utf-8'))
