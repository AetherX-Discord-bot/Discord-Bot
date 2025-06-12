import os
import sqlite3
from discord.ext import commands
import discord

class Leveling(commands.Cog):
    """A cog to handle user leveling and XP in servers."""
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))

    async def add_xp(self, guild_id, user_id, amount, samount):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            # Ensure entry exists
            c.execute("INSERT OR IGNORE INTO server_leveling (server_id, user_id) VALUES (?, ?)", (guild_id, user_id))
            # Add XP
            c.execute("UPDATE server_leveling SET xp = xp + ? WHERE server_id = ? AND user_id = ?", (samount, guild_id, user_id))
            # Get new XP and level
            c.execute("SELECT xp, level FROM server_leveling WHERE server_id = ? AND user_id = ?", (guild_id, user_id))
            xp, level = c.fetchone()
            # Do the same for global XP
            c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
            c.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id))
            c.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
            global_xp, global_level = c.fetchone()
            # Level up logic (simple: 100 xp * level)
            new_level = xp // (level * 100)
            new_global_level = global_xp // (global_level * 100)
            leveled_up = False
            if new_global_level > global_level:
                c.execute("UPDATE users SET level = ? WHERE user_id = ?", (new_global_level, user_id))
                print(f"User {user_id} leveled up globally to level {new_global_level}.")
                leveled_up = True
            if new_level > level:
                c.execute("UPDATE server_leveling SET level = ? WHERE server_id = ? AND user_id = ?", (new_level, guild_id, user_id))
                leveled_up = True
            conn.commit()
            return new_level if leveled_up else None
        finally:
            conn.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        # Fetch prefix and leveling settings
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT prefix, leveling_xp_per_message, leveling_channel_id, leveling_message FROM server_settings WHERE server_id = ?", (message.guild.id,))
        row = c.fetchone()
        conn.close()
        if row:
            _, xp_per_message, leveling_channel_id, leveling_message = row
            xp_gain = xp_per_message if xp_per_message is not None else 10
        else:
            leveling_channel_id = None
            leveling_message = None
            xp_gain = 10
        level_up = await self.add_xp(message.guild.id, message.author.id, xp_gain, xp_gain)
        if level_up is not None:
            # Use custom leveling channel/message if set
            channel = message.channel
            user = f"<@{message.author.id}>"
            user_name = message.author.name
            user_display = message.author.display_name
            level = level_up
            if leveling_channel_id:
                channel = message.guild.get_channel(leveling_channel_id) or message.channel
            msg = leveling_message or f"🎉 {user} leveled up to {level_up}!"
            try:
                await channel.send(msg.format(member=message.author.mention, level=level_up))
            except Exception:
                print(f"Failed to send level up message in {channel.name} for {user_name} ({user_display}).")
                print(f"Error: {Exception}")
                await message.channel.send(f"🎉 {user} leveled up to {level_up}!")

    @commands.command(aliases=["xp", "lvl"])
    async def level(self, ctx, member: discord.Member = None):
        """Check your or another member's level."""
        if not member:
            member = ctx.author
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT prefix FROM server_settings WHERE server_id = ?", (ctx.guild.id,))
        prefix_row = c.fetchone()
        prefix = prefix_row[0] if prefix_row and prefix_row[0] else '!'
        c.execute("SELECT xp, level FROM server_leveling WHERE server_id = ? AND user_id = ?", (ctx.guild.id, member.id))
        row = c.fetchone()
        conn.close()
        if not row:
            await ctx.send(f"{member.mention} has no level data yet. Use `{prefix}level` after chatting to start earning XP!")
            return
        xp, level = row
        await ctx.send(f"{member.mention} is level {level} with {xp} XP. Use `{prefix}level` to check again!")

    @commands.command(aliases=["globalxp", "gxp", "glvl", "glevel"])
    async def globallevel(self, ctx, member: discord.Member = None):
        """Check your or another member's global level (across all servers)."""
        if not member:
            member = ctx.author
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT xp, level FROM users WHERE user_id = ?", (member.id,))
        row = c.fetchone()
        conn.close()
        if not row:
            await ctx.send(f"{member.mention} has no global level data yet.")
            return
        xp, level = row
        await ctx.send(f"{member.mention} is global level {level} with {xp} XP.")

async def setup(bot):
    await bot.add_cog(Leveling(bot))
