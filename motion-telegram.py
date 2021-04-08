#!/usr/bin/python

import socket
import sys
import re
import os

from threading import Thread, Lock

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


server_address = '/tmp/motion-telegram'
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
mutex = Lock()


def send_event(event: str):
    sock.connect(server_address)
    sock.sendall(event.encode('utf-8'))


class TelegramBot:
    def __init__(self):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if token is None:
            raise Exception(
                'Please provide a telegram bot token in the server env '
                'TELEGRAM_BOT_TOKEN')

        self.updater = Updater(token)
        pass

    def start(self):
        self.updater.start_polling()

    def process_event(self, event: str):
        with mutex:
            m = re.match(r'motion-start (.+)', event)
            if m:
                camera_id = m.group(1)
                self.updater.bot.send_message(
                    self.chat_id, f'Motion started on camera {camera_id}')
                return
            m = re.match(r'motion-end (.+)', event)
            if m:
                camera_id = m.group(1)
                self.updater.bot.send_message(
                    self.chat_id, f'Motion ended on camera {camera_id}')
                return
            m = re.match(r'movie-end (.+) (.+)', event)
            if m:
                camera_id = m.group(1)
                movie_file = m.group(2)
                eprint(f'Movie ended on camera {camera_id} @ {movie_file}')
                self.updater.bot.send_video(
                    self.chat_id, movie_file, caption=f'{camera_id}')
                os.unlink(movie_file)
                return

            eprint(f"Unknown event: {event}")


def start_server():
    # Make sure the socket does not already exist
    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise

    eprint(f'starting up on {server_address}')
    sock.bind(server_address)

    sock.listen(1)

    bot = TelegramBot()

    while True:
        connection, client_address = sock.accept()
        try:
            data = connection.recv(1024).decode('utf-8')

            bot.process_event(data)
        except e:
            eprint(f'Error while processing event: {e}')
        finally:
            connection.close()


def print_usage():
    eprint('Usage: Run with start-server to run as a server and '
           'with send-event to relay an event to the server.')


def main():
    args = sys.argv

    if len(args) < 2:
        print_usage()
        return

    if args[1] == 'start-server':
        start_server()
    elif args[1] == 'send-event':
        send_event(' '.join(args[2:]))
    else:
        print_usage()


if __name__ == '__main__':
    main()
