import discord
from discord import app_commands
from discord.ext import commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="say", description="Send a message as the bot in the current channel.")
    async def say(self, ctx: commands.Context, message: str):
        """Make the bot say something"""
        if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.administrator:
            if ctx.interaction is not None:
                await ctx.interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            else:
                await ctx.reply("You do not have permission to use this command.")
            return

        if ctx.interaction is not None:
            await ctx.interaction.response.defer(ephemeral=True)

        channel = ctx.channel
        if channel is not None and isinstance(channel, discord.abc.Messageable):
            await channel.send(message)
        else:
            if ctx.interaction is not None:
                await ctx.interaction.followup.send(message, ephemeral=False)
            else:
                await ctx.send(message)

async def setup(bot):
    await bot.add_cog(Say(bot))