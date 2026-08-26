import discord
from discord import app_commands
from discord.ext import commands

version = "0.3.1-alpha"
class Updates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="updates", description="View the latest updates and changes to AetherX.")
    async def updates(self, ctx: commands.Context):
        embed = discord.Embed(title="AetherX Update Log", description=f"Version {version} - Latest Updates and Changes", color=discord.Color.blue())
        embed.add_field(name="New Features", value="- Added logging options and update tracking", inline=False)
        embed.add_field(name="Bug Fixes", value="- Fixed error messages related to tickets (A bug where memory of ticket configs being saved is known)", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Updates(bot))