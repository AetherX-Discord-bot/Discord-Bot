import discord
import datetime
import sqlite3
import zoneinfo as zi
from typing import Optional
from discord.ext import commands




class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect('AetherX.db')
        

    @commands.hybrid_command(name="birthday", description="Set your birthday")
    async def birthday(self, ctx: commands.Context, date: str, timezone: str = "UTC"):
        """Set your birthday"""
        try:
            cursor = self.db.cursor()
            cursor.execute("INSERT OR REPLACE INTO birthdays (user_id, birthday, timezone) VALUES (?, ?, ?)", (ctx.author.id, date, timezone))
            self.db.commit()
            await ctx.send(f"Your birthday has been set to {date} in timezone {timezone}.")
            self.db.close()
        except Exception as e:
            await ctx.send(f"An error occurred while setting your birthday: {e}")

    @commands.hybrid_command(name="timezones", description="List available timezones")
    async def timezones(self, ctx: commands.Context):
        """List available timezones"""
        timezones = sorted(zi.available_timezones())
        await ctx.send(f"Available timezones:\n{', '.join(timezones)}")

    @commands.hybrid_command(name="set_birthday_channel", description="Set the channel for birthday announcements")
    @commands.has_permissions(administrator=True)
    async def set_birthday_channel(self, ctx: commands.Context, channel: discord.TextChannel, role: Optional[discord.Role]): 
        """Set the channel for birthday announcements"""
        try:
            cursor = self.db.cursor()
            cursor.execute("INSERT OR REPLACE INTO birthday_conf (guild_id, channel_id, role_id) VALUES (?, ?, ?)", (ctx.guild.id, channel.id, role.id if role else None))
            self.db.commit()
            await ctx.send(f"Birthday announcements will be sent to {channel.mention}.")
            self.db.close()
        except Exception as e:
            await ctx.send(f"An error occurred while setting the birthday channel: {e}")





async def setup(bot):
    await bot.add_cog(Birthday(bot))