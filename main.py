# -*- coding: utf-8 -*-

import configparser
import json
import discord
import requests.exceptions
from discord.ext import tasks
from requests import get
from gc import collect
from loguru import logger
from sys import stdout
from configparser import ConfigParser
from json import loads
from os.path import exists
from os import rename
from os import remove
# TODO tf, there is only ~200 lines in this file, why here so many imports?
# ok, now I know why
# TODO make it smaller with comma

# remove default logger
logger.remove()

# set up logger levels
logger.level("INFO", icon="🩵", color="<blue>")
logger.level("SUCCESS", icon="🍀", color="<green>")
logger.level("WARNING", icon="⚠️", color="<yellow>")
logger.level("CRITICAL", icon="💥", color="<red>")

# file logger
logger.add(
    'logs/{time:YYYY-MM-DD}.log',
    format='{time:YYYY-MM-DD at HH:mm:ss:SSS} | {line} | {level} {message}',
    level='INFO',
    rotation='00:00',
    encoding='utf-8',
    colorize=False,
    compression='zip')

# console logger
logger.add(
    sink=stdout,
    format='[{time:YYYY-MM-DD at HH:mm:ss}] | {line} | [{level.icon}]<level> {message} </level>',
    level='INFO')

# parsing config.ini
config = ConfigParser()


# main class
class main(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        logger.info('Loading config file...')

        # auto fix def
        def fix(error: str):

            logger.critical(f'Config file not found or it invalid! ({error} error)')

            if exists('config.ini'):
                logger.info('Creating backup of config file...')
                if exists('config.ini.old'):
                    logger.warning('Backup already exists! Overwrite?')
                    if input('Y/n? ').lower() == 'y':
                        pass
                    else:
                        logger.critical('Operation aborted!')
                        exit(0)
                remove('config.ini.old')  # remove old backup
                rename('config.ini', 'config.ini.old')  # rename invalid config to old backup
                logger.success('Backup created with name: config.ini.old')

            logger.warning('Creating config file with example...')

            # very bad config example
            # TODO make it better
            example = [
                '[bot]\n',
                'token = "9876f5fsdf4321sa"\n'
                '\n'
                '[endpoints];\n'
                '; format: [url, channel id, [on_name, off_name]]\n'
                'endpoints: [\n'
                '\n'
                '   ["https://example.com", 123456789, ["OFF!", "ON!"]],\n'
                '   ["https://google.com", 123456789, ["🔴┃📡・Example!", "🟢┃📡・Example!"]]\n'
                '   ; add more endpoints if needed!\n'
                '           ]'
                ]
            # write example to new config
            with open('config.ini', 'w+t') as f:
                for i in example:
                    f.write(i)
            logger.success('Config file created with name: config.ini')

            logger.warning('Please, edit config.ini and restart the bot!')
            exit(1)

        # Catching parsing errors
        try:
            config.read('config.ini')
        except configparser.ParsingError:
            fix('Parsing')
        if not (config.has_section('bot') and
                config.has_section('endpoints') and
                config.has_option('bot', 'token') and
                config.has_option('endpoints', 'endpoints')):
            fix('Options and sections')
        try:
            config.get('bot', 'token')
            loads(config.get('endpoints', 'endpoints').replace('\n', ' '))
        except json.JSONDecodeError:
            fix('Decode')

        logger.success('Config file loaded!')

        self.latest = list()
        self.endpoints = loads(config.get('endpoints', 'endpoints').replace('\n', ' '))  # get endpoints list
        for i in range(len(self.endpoints)):  # add status for endpoints
            self.latest.append(False)
            self.endpoints[i].append(False)

    # On bot ready
    async def on_ready(self):
        logger.success('We are logged in as {0.user}'.format(self))
        self.update_status.start()

    # Endpoint status update
    async def update(self):
        current = list()
        for i in range(len(self.endpoints)):
            current.append(self.endpoints[i][3])

        if current != self.latest:

            self.latest = current
            for i in range(len(self.endpoints)):
                if current[i]:
                    # if endpoint status is true change name to first name in config
                    name = self.endpoints[i][2][1]
                else:
                    # if endpoint status is false change name to second name in config
                    name = self.endpoints[i][2][0]
                try:
                    channel = self.get_channel(int(self.endpoints[i][1]))
                except discord.errors.NotFound:
                    logger.critical(f'Channel not found: {self.endpoints[i][1]}')
                    logger.critical('Please, correct channel id in config.ini file!')
                    exit(1)
                await channel.edit(name=name, reason='Endpoint status update')
        collect()

    # Loop for status update
    # TODO add cooldown setting
    @tasks.loop(seconds=30)
    async def update_status(self):
        for endpoint in self.endpoints:
            try:
                get(endpoint[0], timeout=5, allow_redirects=True)
            except requests.exceptions.ConnectionError:
                endpoint[3] = False
                logger.warning(f'Connection error: {endpoint[0]}. Is it right url?')
                continue
            except (
                    requests.exceptions.ConnectTimeout or
                    requests.exceptions.ReadTimeout or
                    requests.exceptions.Timeout):
                endpoint[3] = False
                logger.warning(f'Request timeout: {endpoint[0]}')
                continue
            except requests.exceptions.MissingSchema:
                endpoint[3] = False
                logger.warning(f'Missing schema: {endpoint[0]}')
                continue
            except requests.exceptions.InvalidSchema:
                endpoint[3] = False
                logger.warning(f'Invalid schema: {endpoint[0]}')
                continue
            except requests.exceptions.InvalidURL:
                endpoint[3] = False
                logger.warning(f'Invalid url: {endpoint[0]}')
                continue
            except requests.exceptions.InvalidHeader:
                endpoint[3] = False
                logger.warning(f'Invalid header: {endpoint[0]}')
                continue
            except requests.exceptions as e:
                endpoint[3] = False
                logger.warning(f'Unexpected error: {e}. Is it right url?')
                continue
            except Exception as e:
                endpoint[3] = False
                logger.warning(f'Unexpected error at python: {e}. Is it right url?')
                continue
            # TODO we need more exceptions

            # TODO add allowed error codes to config
            if get(endpoint[0]).status_code in range(200, 399):
                endpoint[3] = True
            else:
                print(123)
                endpoint[3] = False
            if get(endpoint[0]).status_code in range(400, 407):
                endpoint[3] = True

        await self.update()


# Bot run
if __name__ == '__main__':
    bot = main(intents=discord.Intents.all())
    try:
        bot.run(config.get('bot', 'token'))
    except discord.LoginFailure:
        # TODO make check better
        logger.critical('Invalid token! Please, check config.ini file!')
        exit(1)
