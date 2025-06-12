import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, Bot, Context
import os
import sqlite3

def is_eligable():
    async def predicate(ctx):
        # Always allow if the user is a bot owner or developer
        config = getattr(ctx.bot, 'config', {})
        owner_ids = config.get('BOT_OWNERS', [])
        developer_ids = config.get('BOT_DEVELOPERS', [])
        all_ids = set(owner_ids + developer_ids)
        if await ctx.bot.is_owner(ctx.author) or ctx.author.id in all_ids:
            return True
        # Only allow if the server has at least 100 human (non-bot) members
        if ctx.guild is None:
            return False
        human_members = [m for m in ctx.guild.members if not m.bot]
        return len(human_members) >= 100
    return commands.check(predicate)

class Moderation(commands.Cog):
    """A cog to handle moderation commands like kick, ban, and clear messages."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    @commands.command()
    @has_permissions(kick_members=True)
    async def kick(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Kick a member from the server."""
        try:
            await member.kick(reason=reason)
            # Ensure user exists in the database before removing karma
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, karma) VALUES (?, 0)", (member.id,))
            c.execute("UPDATE users SET karma = karma - 5 WHERE user_id = ?", (member.id,))
            conn.commit()
            conn.close()
            embed = discord.Embed(description=f"{member.mention} has been kicked. Reason: {reason if reason else 'No reason provided.'}", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to kick {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command()
    @has_permissions(ban_members=True)
    async def ban(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Ban a member from the server."""
        try:
            await member.ban(reason=reason)
            # Ensure user exists in the database before removing karma
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, karma) VALUES (?, 0)", (member.id,))
            c.execute("UPDATE users SET karma = karma - 10 WHERE user_id = ?", (member.id,))
            conn.commit()
            conn.close()
            embed = discord.Embed(description=f"{member.mention} has been banned. Reason: {reason if reason else 'No reason provided.'}", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to ban {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command()
    @has_permissions(manage_messages=True)
    async def clear(self, ctx: Context, amount: int = 5):
        """Clear a number of messages from the channel (default 5)."""
        deleted = await ctx.channel.purge(limit=amount+1)  # +1 to include the command message
        embed = discord.Embed(description=f"Deleted {len(deleted)-1} messages.", color=discord.Color.orange())
        await ctx.send(embed=embed, delete_after=3)

    @commands.command()
    @has_permissions(manage_guild=True)
    async def remove_bot(self, ctx: Context):
        """Remove the bot from the server."""
        if ctx.guild.me.guild_permissions.administrator:
            embed = discord.Embed(description="I cannot remove myself from this server as I have administrator permissions.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        try:
            await ctx.guild.leave()
            embed = discord.Embed(description="I have left the server.", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to leave the server: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(hidden=True)
    @has_permissions(manage_guild=True)
    async def ban_bot(self, ctx: Context):
        """Ban the bot from the server."""
        if ctx.guild.me.guild_permissions.administrator:
            embed = discord.Embed(description="I cannot ban myself from this server as I have administrator permissions.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        try:
            await ctx.guild.ban(ctx.guild.me, reason="Bot banned by command.")
            embed = discord.Embed(description="I have been banned from the server, f u n n y  t i m e", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to ban the bot: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(aliases=['chillchat', 'chill'])
    @has_permissions(manage_channels=True)
    async def slowmode(self, ctx: Context, seconds: int = 0):
        """Set the slowmode for the channel in seconds (0 to disable)."""
        if seconds < 0:
            embed = discord.Embed(description="Slowmode cannot be set to a negative value.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        elif seconds > 21600:  # 6 hours
            embed = discord.Embed(description="Slowmode cannot be set to more than 6 hours (21600 seconds). \n-# This is a Discord limitation, and i added this to prevent my broken code from breaking my terminal.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            embed = discord.Embed(description=f"Slowmode set to {seconds} seconds.", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to set slowmode: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(aliases=['lock'])
    @has_permissions(manage_channels=True)
    async def lock_channel(self, ctx: Context):
        """Lock the current channel so only admins can send messages."""
        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
            embed = discord.Embed(description=f"{ctx.channel.mention} has been locked.", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to lock the channel: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(aliases=['unlock'])
    @has_permissions(manage_channels=True)
    async def unlock_channel(self, ctx: Context):
        """Unlock the current channel so everyone can send messages."""
        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
            embed = discord.Embed(description=f"{ctx.channel.mention} has been unlocked.", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to unlock the channel: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(aliases=['mute'])
    @has_permissions(mute_members=True)
    async def mute_member(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Mute a member in the server."""
        if not ctx.guild.me.guild_permissions.manage_roles:
            embed = discord.Embed(description="I do not have permission to manage roles.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            try:
                mute_role = await ctx.guild.create_role(name="Muted", reason="Mute role created by moderation command.")
                for channel in ctx.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
            except Exception as e:
                embed = discord.Embed(description=f"Failed to create mute role: {e}", color=discord.Color.red())
                await ctx.send(embed=embed)
                return
        try:
            await member.add_roles(mute_role, reason=reason)
            # Ensure user exists in the database before removing karma
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, karma) VALUES (?, 0)", (member.id,))
            c.execute("UPDATE users SET karma = karma - 2 WHERE user_id = ?", (member.id,))
            conn.commit()
            conn.close()
            embed = discord.Embed(description=f"{member.mention} has been muted. Reason: {reason if reason else 'No reason provided.'}", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to mute {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(aliases=['unmute'])
    @has_permissions(mute_members=True)
    async def unmute_member(self, ctx: Context, member: discord.Member):
        """Unmute a member in the server."""
        if not ctx.guild.me.guild_permissions.manage_roles:
            embed = discord.Embed(description="I do not have permission to manage roles.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            embed = discord.Embed(description="There is no 'Muted' role in this server.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        try:
            await member.remove_roles(mute_role, reason="Unmuted by moderation command.")
            embed = discord.Embed(description=f"{member.mention} has been unmuted.", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to unmute {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(aliases=['timeout', 'tempmute'])
    @has_permissions(moderate_members=True)
    async def timeout_member(self, ctx: Context, member: discord.Member, duration: int, *, reason: str = None):
        """Timeout a member for a specified duration in seconds."""
        if not ctx.guild.me.guild_permissions.moderate_members:
            embed = discord.Embed(description="I do not have permission to moderate members.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        try:
            await member.timeout(duration=duration, reason=reason)
            # Ensure user exists in the database before removing karma
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, karma) VALUES (?, 0)", (member.id,))
            c.execute("UPDATE users SET karma = karma - 1 WHERE user_id = ?", (member.id,))
            conn.commit()
            conn.close()
            embed = discord.Embed(description=f"{member.mention} has been timed out for {duration} seconds. Reason: {reason if reason else 'No reason provided.'}", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to timeout {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.command(aliases=['untimeout', 'untimemute'])
    @has_permissions(moderate_members=True)
    async def untimeout_member(self, ctx: Context, member: discord.Member):
        """Remove timeout from a member."""
        if not ctx.guild.me.guild_permissions.moderate_members:
            embed = discord.Embed(description="I do not have permission to moderate members.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        try:
            await member.timeout(None, reason="Timeout removed by moderation command.")
            embed = discord.Embed(description=f"{member.mention} has been removed from timeout.", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to remove timeout from {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['showkarma', 'checkkarma'])
    async def karma(self, ctx: Context, member: discord.Member = None):
        """Check or modify a member's karma."""
        if not member:
            member = ctx.author
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT karma FROM users WHERE user_id = ?", (member.id,))
        row = c.fetchone()
        conn.close()
        if not row:
            embed = discord.Embed(description=f"{member.mention} does not have karma.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        karma = row[0]
        embed = discord.Embed(description=f"{member.mention} has {karma} karma points.", color=discord.Color.green())
        embed.add_field(name="", value="-# Karma is a measure of a member's contributions to Discord communities, ***this can be biased.***", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['addkarma'])
    @has_permissions(administrator=True)
    @is_eligable()
    async def add_karma(self, ctx: Context, member: discord.Member, amount: int):
        """Add karma to a member."""
        if amount <= 0:
            embed = discord.Embed(description="You must add a positive amount of karma.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        # Ensure user exists in the database
        c.execute("INSERT OR IGNORE INTO users (user_id, karma) VALUES (?, 0)", (member.id,))
        # Add karma
        c.execute("UPDATE users SET karma = karma + ? WHERE user_id = ?", (amount, member.id))
        conn.commit()
        conn.close()
        embed = discord.Embed(description=f"Added {amount} karma to {member.mention}.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(alias='sprefix')
    @has_permissions(manage_guild=True)
    async def setprefix(self, ctx: Context, prefix: str):
        """Set the server's command prefix."""
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET prefix = ? WHERE server_id = ?", (prefix, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(f"Prefix set to `{prefix}` for this server.")

    @commands.command(alias='welcomechannel')
    @has_permissions(manage_guild=True)
    async def setwelcomechannel(self, ctx: Context, channel: discord.TextChannel):
        """Set the welcome channel for the server."""
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET welcome_channel_id = ? WHERE server_id = ?", (channel.id, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(f"Welcome channel set to {channel.mention}.")

    @commands.command(alias='welcomemsg')
    @has_permissions(manage_guild=True)
    async def setwelcomemessage(self, ctx: Context, *, message: str):
        """Set the welcome message for the server."""
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET welcome_message = ? WHERE server_id = ?", (message, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send("Welcome message updated.")

    @commands.command(alias='levelingxp')
    @has_permissions(manage_guild=True)
    async def setlevelingxp(self, ctx: Context, per_message: int = None, per_reaction: int = None, per_command: int = None):
        """Set XP per message, reaction, and command for leveling (any can be omitted)."""
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        if per_message is not None:
            c.execute("UPDATE server_settings SET leveling_xp_per_message = ? WHERE server_id = ?", (per_message, ctx.guild.id))
        if per_reaction is not None:
            c.execute("UPDATE server_settings SET leveling_xp_per_reaction = ? WHERE server_id = ?", (per_reaction, ctx.guild.id))
        if per_command is not None:
            c.execute("UPDATE server_settings SET leveling_xp_per_command = ? WHERE server_id = ?", (per_command, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send("Leveling XP settings updated.")

    @commands.command(alias='levelchannel')
    @has_permissions(manage_guild=True)
    async def setlevelingchannel(self, ctx: Context, channel: discord.TextChannel):
        """Set the channel for leveling up messages."""
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET leveling_channel_id = ? WHERE server_id = ?", (channel.id, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send(f"Leveling channel set to {channel.mention}.")

    @commands.command(alias='levelmessage')
    @has_permissions(manage_guild=True)
    async def setlevelingmessage(self, ctx: Context, *, message: str):
        """Set the message for leveling up announcements."""
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO server_settings (server_id) VALUES (?)", (ctx.guild.id,))
        c.execute("UPDATE server_settings SET leveling_message = ? WHERE server_id = ?", (message, ctx.guild.id))
        conn.commit()
        conn.close()
        await ctx.send("Leveling up message updated.")

async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
