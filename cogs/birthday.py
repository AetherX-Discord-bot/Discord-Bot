import discord
import datetime
import sqlite3
from discord.ext import commands
from discord import app_commands
from zoneinfo import ZoneInfo as zi

import bot


class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


        @commands.hybrid_command(name="birthday", description="Set your birthday")
        async def birthday(self, ctx: commands.Context, date: str, timezone: str = "UTC"):
            """Set your birthday"""
            try:
                database = sqlite3.connect('AetherX.db')
                cursor = database.cursor()
                cursor.execute("INSERT OR REPLACE INTO birthdays (user_id, birthday, timezone) VALUES (?, ?, ?)", (ctx.author.id, date, timezone))
                database.commit()
                await ctx.send(f"Your birthday has been set to {date} in timezone {timezone}.")
                database.close()
            except Exception as e:
                await ctx.send(f"An error occurred while setting your birthday: {e}")

            


            
                

            



async def setup(bot):
    await bot.add_cog(Birthday(bot))