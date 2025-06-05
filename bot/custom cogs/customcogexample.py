# by default, this file is blacklisted in the config.json file
# but you can whitelist it to load it automatically
import discord
from discord.ext import commands

class MyCog(commands.Cog):
    """A simple custom cog example."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Hello from a custom cog!")

async def setup(bot):
    await bot.add_cog(MyCog(bot))