
import logging.config
import traceback
import datetime
import psycopg2
import logging
import asyncio
import locale
import random
import yaml
import json
import sys
import re

import discord
import aiohttp

sys.path.append("helpers/")

import output_generator as og
import exchange_processor
import database

CONFIG_FILE = "config.json"
LOGGING_CONFIG = "log_conf.yaml"


class Bot:
	"""
	Bot used to analyze the bittrex and binance markets for significant price changes and
	RSI values.

	These significant markets are then printed out into a discord server.

	Attributes:
		client: Client used to communicate with the discord server
		config: configuration to edit the bot.
		logger: Logger to be used when logging.
		_mooning: High significant price change.
		_free_fall: Low significant price change.
		_over_bought: High significant RSI val.
		_over_sold: Low significant RSI val.
		_interval: Time to wait between each analysis of the markets.
		_rsi_tick_interval: Interval between each price update used to calculate the markets.
		_rsi_time_frame: Number of candles used to calculate RSI.

	"""
	def __init__(self, client: discord.Client, logger: logging.Logger, config: dict, db=None):
		self._client = client
		self._logger = logger
	
		# config stuff

		self._interval = config["update_interval"]
		self._base_prefix = config["prefix"]

		self._db = database.ServerDatabase("hasami", "hasami", "password")

		self.mp = exchange_processor.Processor(self._logger, config, self._db)

		self._client.loop.create_task(self._set_playing_status())

		self._client.loop.run_until_complete(self._initialize_checker())

		self._client.loop.create_task(self.send_server_price_update_signals())
		self._client.loop.create_task(self.send_server_rsi_update_signals())


	async def _set_playing_status(self):
		locale.setlocale(locale.LC_ALL, "")

		while True:
			await self._client.wait_until_ready()

			data = await self.mp.get_crypto_mcap()

			mc = int(data["total_market_cap_usd"])
			mc = locale.currency(mc, grouping=True)

			self._logger.info("Setting market cap {0}".format(mc))

			await self._client.change_presence(
				game=discord.Game(name=mc))

			await asyncio.sleep(900)


	async def add_server_for_signals(self, message: discord.Message, 
			exchanges: list) -> None:

		await self._client.send_message(
			message.channel , "Starting {0.author.mention} !".format(message)
			)

		if not exchanges:
			exchanges = ["bittrex"]

		server_id = message.server.id
		server_name = message.server.name
		
		if not self._db.server_exists(server_id):
			self._db.add_server(server_id, server_name, self._base_prefix)

		# load markets
		await self.mp.load_exchanges(exchanges)

		self._db.update_output_channel(server_id, message.channel.id)
		self._db.add_exchanges(server_id, exchanges)

		text = "Added {0.server.name}-{0.channel} to rsi/update outputs and checking {1}"\
			.format(message, exchanges)

		self._logger.info(text)


	async def _initialize_checker(self) -> None:
		servers = self._db.servers_wanting_signals()

		for server in servers:
			print(server)
			exchanges = server[3].split(" ")
			self._logger.info("Loading exchanges {0}".format(exchanges))
			await self.mp.load_exchanges(exchanges)


	async def send_server_price_update_signals(self) -> None:
		while True:
			try: 
				async for channel, embed in self.mp.yield_exchange_price_updates():
					channel = discord.Object(channel)
					await self._client.send_message(channel, embed=embed)

			except Exception as e:
				self._logger.debug(traceback.print_exc())
				self._logger.warning(e)

			await asyncio.sleep(int(self._interval * 60))


	async def send_server_rsi_update_signals(self) -> None:
		while True:
			try:
				async for channel, embed in self.mp.yield_exchange_rsi_updates():
					channel = discord.Object(channel)
					await self._client.send_message(channel, embed=embed)

			except Exception as e:
				self._logger.debug(traceback.print_exc())
				self._logger.warning(e)

			await asyncio.sleep(int(self._interval * 60))


	async def stop_sending_signals(self, message: discord.Message, exchanges: list) -> None:
		"""
		Stops checking markets, notifies user who called for it of that it's stopping.

		Args:
			message: The message used to ask the bot to stop, used
				to mention the user that it's stopping.

		Returns:
			None

		TODO: 
			If no markets are specified stop completely, else remove exchanges from being
			updated.

		"""
		chan = message.channel

		await self._client.send_message(
			message.channel, "Stopping {0.author.mention} !".format(message))

		server_id = message.server.id
		self._db.update_output_channel(server_id, None)
		
		if len(exchanges) == 0:
			text = "Removing {0.server.name}-{1} from update channels"\
				.format(message, chan)

			self._db.update_exchanges(server_id, None)

		else:
			text = "Removing exchanges {2} from {0.server.name}-{1}"\
				.format(message, chan, exchanges)

			self._db.remove_exchanges(server_id, exchanges)

		self._logger.info(text)


	async def price(self, message: discord.Message, markets: list) -> None:
		for market in markets:

			if market == "":
				continue

			market = await self.mp.find_cmc_ticker(market)

			if not market:
				continue

			info = await self.mp.cmc_market_query(market)
			await self._client.send_message(
				message.channel, embed=og.create_cmc_price_embed(info[0]))


	async def crypto_cap(self, message: discord.Message) -> None:

		info = await self.mp.get_crypto_mcap()

		await self._client.send_message(
			message.channel, embed=og.create_cmc_cap_embed(info))


	async def greet(self, message: discord.Message) -> None:
		"""
		Greets whoever wants to be greeted !

		Args:
			message: message used to ask for a greet from the bot.
				Used to mention the user for greet.

		Returns:
			None

		"""
		await self._client.send_message(
			message.channel, "Hello {0.author.mention} !".format(message)
			)


	async def exit(self, message: discord.Message) -> None:
		"""
		Shutsdown the bot, logs it, and notifies user who called for it of the exit

		Args:
			message: Discord message used to call for exit.

		Returns:
			None

		"""

		await self._client.send_message(
			message.channel, "Bye {0.author.mention}!".format(message)
			)
		sys.exit()


	async def source(self, message: discord.Message) -> None:
		await self._client.send_message(message.channel, "https://github.com/lokraan/hasami")


	async def change_prefix(self, message: discord.Message, params: list) -> None:
		self._db.update_prefix(message.server.id, params[0])

		text = "Changed {0.author.mention} prefix to {1}".format(message, params[0])
		await self._client.send_message(message.channel, text)


	def joined_server(server):
		self._logger.info("Joined {0}".format(server.name))

		self._db.add_server(server.id, server.name, self._base_prefix)

