import discord
from discord import app_commands
from discord.ext import commands

version = "0.1.3"
class Updates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="updates", description="View the latest updates and changes to AetherX.")
    async def updates(self, ctx: commands.Context):
        embed = discord.Embed(title="AetherX Update Log", description=f"Version {version} - Latest Updates and Changes", color=discord.Color.blue())
        embed.add_field(name="New Features", value="- Added Update_log to show latest updates and changes.", inline=False)
        embed.add_field(name="Bug Fixes", value="-Reworked slash commands load time\n"
            "- Applied back end fixes to welcome.\n" \
            "Fixed more backend issues on other cogs. Let's go gambling 🎰")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Updates(bot))