
import datetime
import asyncio
import discord
import random
import locale


def get_output(*items: list) -> str:
		"""
		Creates a discord.Embed friendly formatting and returns it.

		Args:
			*items: Items to concatonate together into one output.

		Returns:
			Discord friendly text !

		"""

		return " ".join(*items)


def create_embed(title: str, text: str, highlight: bool = True, 
	discord_mark_up: str ='ini', color: int = None) -> discord.Embed: 
	"""
	Generates a pretty embed for discord consisting of two groups,
	the significant price changes / RSI vals.

	Args:
		outputs: Tuple of what the data is called and the data.

	Returns:
		a discord.Embed of items inside the list

	"""

	r = lambda: random.randint(0, 255)
	if not color:
		color = (r(), r(), r())
		color = (int("0x%02x%02x%02x" % color, 16))

	if not text:
		return None

	embed = discord.Embed(
		title=title, type="rich", 
		timestamp=datetime.datetime.now(),
		colour=discord.Colour(color)
		)


	if highlight:
		text = "```{0}\n{1}\n```".format(discord_mark_up, text) 

	#\u200b
	embed.add_field(name="\u200b", value=text, inline=False)

	return embed


def create_cmc_embed(info: dict) -> discord.Embed:

	locale.setlocale( locale.LC_ALL, 'English_United States.1252' )

	n = info["name"]

	color = 0x21ff3b if float(info["percent_change_24h"]) >= 0 else 0xff0000
	img_url = "https://files.coinmarketcap.com/static/img/coins/32x32/{}.png".format(
		info["id"])


	embed = discord.Embed(
		title=n,
		colour=color, timestamp=datetime.datetime.now()
		)

	text = locale.currency(float(info["price_usd"]), grouping=True)\
		+ " / " + info["price_btc"] + " BTC"

	changes = [info["percent_change_1h"], 
		info["percent_change_24h"], info["percent_change_7d"]]

	changes = [i if i else "0.0" for i in changes]

	suffixes = [" 1 hour", " 24 hour", " 1 week"]

	changes = ["{0: <8} - {1}".format(v + "%", suffixes[i]) if float(v) < 0 else 
			"{0: <8}  - {1}".format("+" + v + "%", suffixes[i])
			for i, v in enumerate(changes)]


	embed.set_thumbnail(url=img_url)
	embed.add_field(name="Price", value=text, inline=True)

	mc = float(info["market_cap_usd"]) if info["market_cap_usd"] else 0
	embed.add_field(name="Market Cap - Rank " + info["rank"], value=locale.currency(
		mc, grouping=True), inline=True)

	embed.add_field(name="\u200b", 
		value="```diff\nChange\n\n{}```".format('\n'.join(changes)), inline=False)

	return embed