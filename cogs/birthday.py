import discord
import datetime
import sqlite3
from discord.ext import commands
from zoneinfo import ZoneInfo as zi

import bot


class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        database = sqlite3.connect('AetherX.db')
        cursor = database.cursor()

        @commands.hybrid_command(name="birthday", description="Set your birthday")
        async def birthday(self, ctx: commands.Context, date: str, timezone: str = "UTC"):
            """Set your birthday"""
            try:
                cursor.execute("INSERT OR REPLACE INTO birthdays (user_id, birthday, timezone) VALUES (?, ?, ?)", (ctx.author.id, date, timezone))
                database.commit()
                await ctx.send(f"Your birthday has been set to {date} in timezone {timezone}.")
                database.close()
            except Exception as e:
                await ctx.send(f"An error occurred while setting your birthday: {e}")

        @commands.hybrid_command(name="timezones", description="List available timezones")
        async def timezones(self, ctx: commands.Context):
            """List available timezones"""
            timezones = sorted(zi.available_timezones())
            await ctx.send(f"Available timezones:\n{', '.join(timezones)}")







async def setup(bot):
    await bot.add_cog(Birthday(bot))