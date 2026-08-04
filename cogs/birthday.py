import discord
import datetime
import sqlite3
import zoneinfo as zi
import asyncio
from typing import Optional
from discord.ext import commands, tasks
from discord import app_commands


class TimezonePaginator(discord.ui.View):
    def __init__(self, pages, author, timeout=120):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)
        self.author = author
        self.message = None
    
    async def update_embed(self, interaction):
        embed = discord.Embed(
            title="🌍 Available Timezones",
            description=f"```\n{', '.join(self.pages[self.current_page])}\n```",
            color=discord.Color.blue()
        )
        embed.set_footer(
            text=f"Page {self.current_page + 1}/{self.total_pages} • {sum(len(page) for page in self.pages)} total timezones"
        )
        
        self.children[0].disabled = self.current_page == 0  
        self.children[1].disabled = self.current_page == 0  
        self.children[2].disabled = self.current_page == self.total_pages - 1  
        self.children[3].disabled = self.current_page == self.total_pages - 1  
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⏮️ First", style=discord.ButtonStyle.gray)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ You can't control this pagination!", ephemeral=True)
            return
        self.current_page = 0
        await self.update_embed(interaction)

    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ You can't control this pagination!", ephemeral=True)
            return
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_embed(interaction)

    @discord.ui.button(label="▶️ Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ You can't control this pagination!", ephemeral=True)
            return
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        await self.update_embed(interaction)

    @discord.ui.button(label="⏭️ Last", style=discord.ButtonStyle.gray)
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ You can't control this pagination!", ephemeral=True)
            return
        self.current_page = self.total_pages - 1
        await self.update_embed(interaction)

    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ You can't control this pagination!", ephemeral=True)
            return
        await interaction.message.delete()
        self.stop()

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

class Birthday(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect('AetherX.db')
        self.init_db()
        self.check_birthdays.start()

    def init_db(self):
        cursor = self.db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS birthdays (
                user_id INTEGER PRIMARY KEY,
                birthday TEXT NOT NULL,
                timezone TEXT NOT NULL,
                send_message INTEGER DEFAULT 1,
                last_announced_year INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS birthday_conf (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                message TEXT,
                role_id INTEGER
            )
        """)
        self.db.commit()

    def cog_unload(self):
        self.check_birthdays.cancel()
        self.db.close()

    @tasks.loop(time=datetime.time(hour=0, minute=0, second=0))
    async def check_birthdays(self):
        """Check for birthdays daily at midnight UTC"""
        cursor = self.db.cursor()
        
        cursor.execute("SELECT user_id, birthday, timezone, send_message, last_announced_year FROM birthdays WHERE send_message = 1")
        all_users = cursor.fetchall()
        
        current_year = datetime.datetime.now().year
        birthday_users = {}
        
        for user_id, birthday, timezone, send_message, last_announced_year in all_users:
            try:
                user_tz = zi.ZoneInfo(timezone)
                now = datetime.datetime.now(user_tz)
                today_in_user_tz = now.strftime("%m/%d")
                
                birthday_date = datetime.datetime.strptime(birthday, "%m/%d/%Y")
                birthday_month_day = birthday_date.strftime("%m/%d")
                
                if birthday_month_day == today_in_user_tz and last_announced_year != current_year:
                    birthday_users[user_id] = birthday
            except (ValueError, KeyError):
                continue
        
        if not birthday_users:
            return
        
        cursor.execute("SELECT guild_id, channel_id, message, role_id FROM birthday_conf")
        guild_configs = cursor.fetchall()
        
        for guild_id, channel_id, custom_message, role_id in guild_configs:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            
            mentions = []
            announced_users = []
            
            for user_id in birthday_users.keys():
                user = guild.get_member(user_id)
                if user:
                    mentions.append(user.mention)
                    announced_users.append(user_id)
            
            if not mentions:
                continue
            
            mention_text = " ".join(mentions)
            
            if custom_message:
                message_text = custom_message.replace("{mention}", mention_text)
            else:
                message_text = f"🎉 Happy Birthday {mention_text}! 🎉"
            
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    message_text = f"{role.mention} {message_text}"
            
            try:
                await channel.send(message_text)
                
                for user_id in announced_users:
                    cursor.execute(
                        "UPDATE birthdays SET last_announced_year = ? WHERE user_id = ?",
                        (current_year, user_id)
                    )
                self.db.commit()
                
            except Exception as e:
                print(f"Failed to send birthday message in guild {guild_id}: {e}")

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="birthday", description="Set your birthday")
    @app_commands.describe(date="(mm/dd/yyyy)", timezone="timezone you are in")
    async def birthday(self, ctx: commands.Context, date: str, timezone: str = "UTC"):
        """Set your birthday"""
        try:
            datetime.datetime.strptime(date, "%m/%d/%Y")
        except ValueError:
            await ctx.send("❌ Invalid date format. Please use mm/dd/yyyy")
            return
        
        if timezone not in zi.available_timezones():
            await ctx.send("❌ Invalid timezone. Use `/timezones` to see available timezones.")
            return
        
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO birthdays (user_id, birthday, timezone, send_message, last_announced_year) VALUES (?, ?, ?, 1, 0)", 
                (ctx.author.id, date, timezone)
            )
            self.db.commit()
            await ctx.send(f"✅ Your birthday has been set to {date} in timezone {timezone}.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred while setting your birthday: {e}")

    @commands.hybrid_command(name="birthday_toggle", description="Toggle birthday announcements for yourself")
    async def birthday_toggle(self, ctx: commands.Context):
        """Toggle whether you receive birthday announcements"""
        cursor = self.db.cursor()
        
        cursor.execute("SELECT send_message FROM birthdays WHERE user_id = ?", (ctx.author.id,))
        result = cursor.fetchone()
        
        if not result:
            await ctx.send("❌ You haven't set your birthday yet! Use `/birthday` first.")
            return
        
        current_status = result[0]
        new_status = 0 if current_status == 1 else 1
        
        cursor.execute(
            "UPDATE birthdays SET send_message = ? WHERE user_id = ?",
            (new_status, ctx.author.id)
        )
        self.db.commit()
        
        status_text = "enabled" if new_status == 1 else "disabled"
        await ctx.send(f"✅ Birthday announcements have been {status_text} for you.")

    @commands.hybrid_command(name="timezones", description="List available timezones")
    async def timezones(self, ctx: commands.Context):
        """List available timezones with pagination buttons"""
        all_timezones = sorted(zi.available_timezones())
        
        items_per_page = 30
        pages = []
        for i in range(0, len(all_timezones), items_per_page):
            pages.append(all_timezones[i:i + items_per_page])
    
        if not pages:
            await ctx.send("❌ No timezones found.")
            return
    
        embed = discord.Embed(
            title="🌍 Available Timezones",
            description=f"```\n{', '.join(pages[0])}\n```",
            color=discord.Color.blue()
        )
        embed.set_footer(
            text=f"Page 1/{len(pages)} • {len(all_timezones)} total timezones"
        )
    
        view = TimezonePaginator(pages, ctx.author)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @commands.hybrid_command(name="set_birthday_channel", description="Set the channel for birthday announcements")
    @commands.has_permissions(administrator=True)
    async def set_birthday_channel(self, ctx: commands.Context, channel: discord.TextChannel, message: str = None, role: Optional[discord.Role] = None): 
        """Set the channel for birthday announcements"""
        try:
            cursor = self.db.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO birthday_conf (guild_id, channel_id, message, role_id) VALUES (?, ?, ?, ?)", 
                (ctx.guild.id, channel.id, message, role.id if role else None)
            )
            self.db.commit()
            await ctx.send(f"✅ Birthday announcements will be sent to {channel.mention}.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred while setting the birthday channel: {e}")

async def setup(bot):
    await bot.add_cog(Birthday(bot))