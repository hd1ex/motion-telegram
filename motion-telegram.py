#!/usr/bin/python

import enum
import logging
import pathlib
import socket
import threading
import re
import os

from gettext import gettext

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class MotionTelegramBot:
    class Mode(enum.Enum):
        SILENT = 'silent'
        TEXT = 'text'
        VIDEO = 'video'

        def get_message(self):
            if self == MotionTelegramBot.Mode.SILENT:
                return gettext('From now on I am completely silent.')
            elif self == MotionTelegramBot.Mode.TEXT:
                return gettext('From now on I will only report motion using '
                               'text. I will not send or save any video '
                               'files.')
            elif self == MotionTelegramBot.Mode.VIDEO:
                return gettext('From now on I will send short video files on '
                               'detected motion.')

            return gettext('I am in an undefined mode :(')

        def get_description(self):
            if self == MotionTelegramBot.Mode.SILENT:
                return gettext('silent - do not report any camera events')
            elif self == MotionTelegramBot.Mode.TEXT:
                return gettext('text - report camera events using text')
            elif self == MotionTelegramBot.Mode.VIDEO:
                return gettext('video - report camera events by sending a '
                               'video clip of the event')

            return gettext('I am in an undefined mode :(')

    def __init__(self):
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if token is None:
            raise Exception(
                'Please provide a telegram bot token in the server env var '
                'TELEGRAM_BOT_TOKEN')

        self.updater = Updater(token)
        self.mutex = threading.Lock()
        self.mode = MotionTelegramBot.Mode.SILENT

        self.updater.dispatcher.add_handler(
            CommandHandler('mode', self.mode_command_handler))

    def mode_command_handler(self, update: Update, context: CallbackContext):
        args = context.args

        if not args:
            # TODO: show keyboard
            update.message.reply_text(gettext(
                f'The current mode is "{self.mode.get_description()}." '
                'Use the command "/mode <mode-name>" to set a new mode.'))
            return

        for mode in MotionTelegramBot.Mode:
            if args[0] == mode.value:
                with self.mutex:
                    self.mode = mode
                update.message.reply_text(mode.get_message())
                return

        update.message.reply_text(gettext(f'Unknown mode: <{args[0]}>'))

    def start(self):
        self.updater.start_polling()

    def process_event(self, event: str):
        with self.mutex:
            m = re.match(r'motion-start (.+)', event)
            if m:
                camera_id = m.group(1)
                logger.debug(f'Motion started on camera {camera_id}')
                if self.mode == MotionTelegramBot.Mode.TEXT:
                    self.updater.bot.send_message(
                        self.chat_id,
                        gettext(
                            f'Detected some motion on camera {camera_id}'
                        ))
                return
            m = re.match(r'motion-end (.+)', event)
            if m:
                camera_id = m.group(1)
                logger.debug(f'Motion ended on camera {camera_id}')
                return
            m = re.match(r'movie-end (.+) (.+)', event)
            if m:
                movie_file = pathlib.Path(m.group(1))
                camera_id = m.group(2)
                logger.debug(
                    f'Movie ended on camera {camera_id} @ {movie_file}')

                if self.mode == MotionTelegramBot.Mode.VIDEO:
                    self.updater.bot.send_video(
                        self.chat_id,
                        open(movie_file, 'rb'),
                        caption=f'{camera_id}',
                        timeout=300)
                os.unlink(movie_file)
                return

            logger.debug(f"Unknown event: {event}")


def start_server():
    server_address = '/tmp/motion-telegram'
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

    # Make sure the socket does not already exist
    try:
        os.unlink(server_address)
    except OSError:
        if os.path.exists(server_address):
            raise

    logger.info(f'Starting server on {server_address}')
    sock.bind(server_address)

    sock.listen(1)

    bot = MotionTelegramBot()
    bot.start()

    while True:
        connection, client_address = sock.accept()
        try:
            data = connection.recv(1024).decode('utf-8')

            bot.process_event(data)
        except Exception as e:
            logger.error(f'Error while processing event: {e}')
        finally:
            connection.close()


if __name__ == '__main__':
    start_server()
