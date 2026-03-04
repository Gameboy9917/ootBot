import discord
import asyncio
from discord.ext import commands

class SpamDetect(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.watchlist = {}

	@commands.Cog.listener('on_message')
	async def spam_detect(self, message):
		SPAM_COUNT = 3  # message count
		SPAM_TIME  = 32 # seconds buffer
		# ------------------------
		watchlist    = self.watchlist
		sender       = message.author
		channel      = message.channel
		server       = message.guild
		reporting_id = 304724247450877953
		reporting    = self.bot.get_channel(reporting_id)
		content      = message.content.strip()

		if not content:
			return

		if sender not in watchlist:
			# add the user to the watchlist and track this message.
			watchlist[sender] = {
				"count": 1,
				"channels": [channel],
				"messages": [message],
				"content": content
			}
		# if the user is already being watched, check if this is the same message.
		# posted in a new channel
		elif content == watchlist[sender]["content"] and channel not in watchlist[sender]["channels"]:
			watchlist[sender]["count"] += 1
			watchlist[sender]["channels"].append(channel)
			watchlist[sender]["messages"].append(message)
		else:
			return

		# if the user has posted the same message in SPAM_COUNT different channels
		# within a SPAM_TIME window, treat it as spam.
		if watchlist[sender]["count"] >= SPAM_COUNT:
			# grant the possible spammer role to mute them.
			spammer_role = discord.utils.get(server.roles, name="Possible Spammer")
			await sender.add_roles(spammer_role)
			# report the incident to the mods channel.
			await reporting.send(f"Possible spammer detected: {sender.mention}. Removed messages:")
			# relay the deleted messages to confirm it was spam, then delete them.
			for msg in watchlist[sender]["messages"]:
				await reporting.send(embed=discord.Embed(description=msg.content))
				await msg.delete()

		await asyncio.sleep(SPAM_TIME)

		# sanity check in case the user was removed from the
		# watchlist through some weird async race condition
		# (not sure how possible it is, just in case).
		if sender in watchlist:
			# lower watch level after spam timer runs out
			# and remove the sent channel from the list.
			watchlist[sender]["count"] -= 1
			watchlist[sender]["channels"].remove(channel)
			if watchlist[sender]["count"] <= 0:
				del watchlist[sender]

def setup(bot):
	bot.add_cog(SpamDetect(bot))
