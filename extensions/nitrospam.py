import discord
import asyncio
from discord.ext import commands

class SpamDetect(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.watchlist = {}

	def image_attachments(self, message):
		return [
			attachment
			for attachment in message.attachments
			if (
				getattr(attachment, "content_type", None)
				and attachment.content_type.startswith("image/")
			)
			or getattr(attachment, "width", None) is not None
			or getattr(attachment, "height", None) is not None
		]

	def message_signature(self, message):
		content = message.content.strip()
		images = self.image_attachments(message)

		if not content and not images:
			return None

		image_details = tuple(
			(
				attachment.size,
				getattr(attachment, "width", None),
				getattr(attachment, "height", None),
				getattr(attachment, "content_type", None),
			)
			for attachment in images
		)

		return (content, image_details)

	async def send_message_report(self, reporting, message, include_image=True):
		images = self.image_attachments(message)
		description = message.content.strip()

		if include_image and images:
			files = [await image.to_file() for image in images]
			await reporting.send(content=description or None, files=files)
			return

		embed = discord.Embed(description=description or "[image attachment]")
		await reporting.send(embed=embed)

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
		signature    = self.message_signature(message)

		if not signature:
			return

		if sender not in watchlist:
			# add the user to the watchlist and track this message.
			watchlist[sender] = {
				"count": 1,
				"channels": [channel],
				"messages": [message],
				"signature": signature
			}
		# if the user is already being watched, check if this is the same message.
		# posted in a new channel
		elif signature == watchlist[sender]["signature"] and channel not in watchlist[sender]["channels"]:
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
			first_message = watchlist[sender]["messages"][0]
			if self.image_attachments(first_message) and not first_message.content.strip():
				removed_message = "Removed image spam"
			else:
				removed_message = "Removed messages"
			await reporting.send(
				f"Possible spammer detected: {sender.mention}. "
				f"{removed_message} in {watchlist[sender]['count']} channels:"
			)
			await self.send_message_report(reporting, first_message)
			# delete the spam messages after saving one copy for moderator review.
			for msg in watchlist[sender]["messages"]:
				try:
					await msg.delete()
				except discord.NotFound:
					pass

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
