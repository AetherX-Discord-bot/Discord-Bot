import discord
from discord.ext import commands
import time
import platform
import psutil

START_TIME = time.time()

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="stats", description="Show bot statistics")
    async def stats(self, interaction: discord.Interaction):

        uptime_seconds = int(time.time() - START_TIME)
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))

        latency = round(self.bot.latency * 1000)

        process = psutil.Process()
        mem_mb = process.memory_info().rss / 1024 / 1024

        python_version = platform.python_version()
        discord_version = discord.__version__

        embed = discord.Embed(
            title="Bot Statistics",
            color=discord.Color.blue()
        )
        embed.add_field(name="Uptime", value=uptime_str)
        embed.add_field(name="Ping", value=f"{latency} ms")
        embed.add_field(name="Memory Usage", value=f"{mem_mb:.2f} MB")
        embed.add_field(name="Python Version", value=python_version)
        embed.add_field(name="Discord.py Version", value=discord_version)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Stats(bot))