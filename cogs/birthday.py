import discord
import datetime
import sqlite3
import zoneinfo as zi
from typing import Optional
from discord.ext import commands
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
        

    @commands.hybrid_command(name="birthday", description="Set your birthday")
    @app_commands.describe(date="(mm\dd\yyyy)", timezone="timezone you are in")
    async def birthday(self, ctx: commands.Context, date: str, timezone: str = "UTC"):
        """Set your birthday"""
        try:
            cursor = self.db.cursor()
            cursor.execute("INSERT OR REPLACE INTO birthdays (user_id, birthday, timezone) VALUES (?, ?, ?)", (ctx.author.id, date, timezone))
            self.db.commit()
            await ctx.send(f"Your birthday has been set to {date} in timezone {timezone}.")
            
        except Exception as e:
            await ctx.send(f"An error occurred while setting your birthday: {e}")



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
    async def set_birthday_channel(self, ctx: commands.Context, channel: discord.TextChannel,message: str, role: Optional[discord.Role]): 
        """Set the channel for birthday announcements"""
        try:
            cursor = self.db.cursor()
            cursor.execute("INSERT OR REPLACE INTO birthday_conf (guild_id, channel_id, message, role_id) VALUES (?, ?, ?)", (ctx.guild.id, channel.id, message, role.id if role else None))
            self.db.commit()
            await ctx.send(f"Birthday announcements will be sent to {channel.mention}.")
            self.db.close()
        except Exception as e:
            await ctx.send(f"An error occurred while setting the birthday channel: {e}")





async def setup(bot):
    await bot.add_cog(Birthday(bot))