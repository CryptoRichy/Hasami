
import logging.config
import datetime
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
import processor as processor
import market_grabber

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
	def __init__(self, client: discord.Client, logger: logging.Logger, config: dict):
		self._client = client
		self._logger = logger
	
		# config stuff

		self._interval = config["update_interval"]
		self._prefix = config["prefix"]

		chan = config["update_channel"]
		self._update_channels = set([chan])

		self.mi = market_grabber.MarketInterface(self._logger)
		self.mp = processor.Processor(self._logger, config, self.mi)

		self._updating = False
		self._cmc_pairs = []

		self._client.loop.create_task(self._set_playing_status())


	async def _set_playing_status(self):
		locale.setlocale(locale.LC_ALL, "")
		while True:
			await self._client.wait_until_ready()

			data = await self.mi.get_crypto_mcap()

			mc = int(data["total_market_cap_usd"])
			mc = locale.currency(mc, grouping=True)

			self._logger.info("Setting market cap {0}".format(mc))

			await self._client.change_presence(
				game=discord.Game(name=mc))

			await asyncio.sleep(900)


	async def check_exchanges(self, message: discord.Message, exchanges: str) -> None:
		"""
		Begins checking markets, notifies user who called for it of that it's starting.

		Processes bittrex and binance markets for signifcant price/rsi updates 
		and sends outputs to discord. 
		
		Does while self._updating is true every interval minutes. 

		Args:
			message: The message used to ask the bot to start, used
			to mention the user that it's starting.

		Returns:
			None
		
		"""

		await self._client.send_message(
			message.channel , "Starting {0.author.mention} !".format(message)
			)

		self._update_channels.add(message.channel.id)
		self._logger.info("Added {0.channel} ({0.channel.id}) to rsi update outputs"\
			.format(message))

		if self._updating:
			return

		self._updating = True

		self._logger.info("Starting to check markets.")
		async with aiohttp.ClientSession() as session:

			# load markets
			await self.mp.load_markets(session)

			# loop through at least once
			while self._updating:
				price_updates = {}

				self._logger.info("Checking markets")

				outputs, price_updates["Bittrex"] = await self.mp.check_bittrex_markets(
					session)

				outputs2, price_updates["Binance"] = await self.mp.check_binance_markets(
					session)

				# send outputs
				for key, val in outputs2.items(): 
					outputs[key].extend(val)
					self._logger.info("Outputs: {0}".format(outputs))

					highlight =  "diff" 
					if key == "RSI":
						highlight = "ini"

					embed = og.create_embed(title=key, text="\n".join(outputs[key]), 
						highlight=True, discord_mark_up=highlight)

					if embed:
						for channel in self._update_channels:
							channel = discord.Object(channel)
							try:
								await self._client.send_message(destination=channel, embed=embed)
							except discord.HTTPException as e:
								self._logger.info(e)


				self._logger.debug("Async sleeping {0}".format(str(self._interval * 60)))
				await asyncio.sleep(int(self._interval*60))

				self.mp.update_prices(price_updates)


	async def stop_checking_markets(self, message: discord.Message) -> None:
		"""
		Stops checking markets, notifies user who called for it of that it's stopping.

		Args:
			message: The message used to ask the bot to stop, used
				to mention the user that it's stopping.

		Returns:
			None

		"""
		chan = message.channel

		await self._client.send_message(
			message.channel, "Stopping {0.author.mention} !".format(message))
			
		if chan.id in self._update_channels:
			self._logger.info("Removing {0.id} from update channels".format(chan))
			self._update_channels.remove(chan.id)

		if len(self._update_channels) == 0:
			self._logger.info("Stopping checking markets")
			self._updating = False


	async def price(self, message: discord.Message, markets: list) -> None:
		for market in markets:

			if market == "":
				continue

			market = await self.mp.find_cmc_ticker(market)

			if not market:
				continue

			info = await self.mi.cmc_market_query(market)
			await self._client.send_message(
				message.channel, embed=og.create_cmc_price_embed(info[0]))


	async def crypto_cap(self, message: discord.Message) -> None:

		info = await self.mi.get_crypto_mcap()

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

