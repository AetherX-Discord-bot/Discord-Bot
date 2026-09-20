import discord
from discord import app_commands
from discord.ext import commands

version = "0.3.2-alpha"
class Updates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="updates", description="View the latest updates and changes to AetherX.")
    async def updates(self, ctx: commands.Context):
        embed = discord.Embed(title="AetherX Update Log", description=f"Version {version} - Latest Updates and Changes", color=discord.Color.blue())
        embed.add_field(name="New Features", value="- None at this time", inline=False)
        embed.add_field(name="Bug Fixes", value="- Fixed tickets setup not being remembered", inline=False)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Updates(bot))