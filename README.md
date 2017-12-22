# Hasami
Hasami is a discord bot that monitors bittrex and binance exchanges for significant changes in price / significant RSI values and prints it out in a specified channel.

## Usage
For basic personal use you need to set `"token"` to your personal bot's token, and `"update_channel"` to the channel the bot should print updates to in **config.json**

```json
"token": "your token",
"update_channel": "your channel id",
```

### Commands
| Command | Description |
| --- | --- |
| `$start` | Starts checking the markets for price/rsi updates | 
| `$stop` | Stops checking the markets for price/rsi updates | 
| `$exit` | Shuts down the bot. |
| `$greet` | Greets whoever wants to be greeted. |

### Requirements
- Python >= 3.5.3
- [discord](https://github.com/Rapptz/discord.py)
- [aiohttp](https://github.com/aio-libs/aiohttp)


### Configuration
All configuration takes place within **config.json**

```json
{
	"token": "your token",
	"update_channel": "your channel id",
	"free_fall": -4,
	"mooning": 4,
	"rsi_tick_interval": "thirtyMin",
	"rsi_time_frame": 14, 
	"over_bought": 75,
	"over_sold": 25,
	"update_interval": 1
}
```

| Option | Description | 
| --- | --- | 
| `token` | The bot's token to use to create connection with discord | 
| `update_channel` | The channel the bot will print updates to |
| `free_fall` | Low value to flag market for printing **(Price Change)**|
| `mooning` | High value to flag market for printing **(Price Change)** |
| `rsi_tick_interval` | Interval between each tick used to calculate **(RSI)** [Options](https://github.com/thebotguys/golang-bittrex-api/wiki/Bittrex-API-Reference-(Unofficial)#getticks): "oneMin", "fiveMin", "thirtyMin", "hour", "day".  |
| `rsi_time_frame` | Number of ticks to use to calculate **(RSI)** |
| `over_bought` | Over bought value to flag market for printing **(RSI)** |
| `over_sold` | Over sold value to flag market for printing **(RSI)** | 
| `update_interval` | Delay between each time it checks the markets (in minutes) |

### What it's doing
When a market's growth/decline is greater than or equal to `mooning` or `free_fall`, the bot flags it and prints an update according to this format.
```
<market_name> changed by <change> on <exchange>
```

When a market's rsi value is greater than or equal to `over_bought` or `over_sold`, the bot flags it and prints an update according to this format.
```
<market_name> RSI: <rsi>
```

## TODO
1. Support for more exchanges.
2. Switch to v2.0 of bittrex api.
3. Support for other trading tools.
4. Price display under `playing` on bot.
5. Colors? 
