import discord
from discord import app_commands
from discord.ext import commands

version = "0.2.0-alpha"
class Updates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="updates", description="View the latest updates and changes to AetherX.")
    async def updates(self, ctx: commands.Context):
        embed = discord.Embed(title="AetherX Update Log", description=f"Version {version} - Latest Updates and Changes", color=discord.Color.blue())
        embed.add_field(name="New Features", value="- Added most of the old commands back as hybrid commands", inline=False)
        embed.add_field(name="Bug Fixes", value="- No new bug fixes at this time", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Updates(bot))