import discord
from discord import app_commands
from discord.ext import commands

class Say(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="say",
        description="Send a message as the bot in the current channel."
    )
    @app_commands.describe(
        message="The message to send"
    )
    async def say(self, interaction: discord.Interaction, message: str):
        """Make the bot say something"""
        # Check if the user has administrator permissions (ensure user is a Member)
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        # Defer privately so the invoker isn't shown, then send the message to the channel.
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel
        # Some channel types (Category, Forum) don't have send; handle safely.
        # Use discord.abc.Messageable which defines the send() coroutine.
        if channel is not None and isinstance(channel, discord.abc.Messageable):
            await channel.send(message)
        else:
            # Fallback: send a public followup if channel isn't available.
            await interaction.followup.send(message, ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(Say(bot))