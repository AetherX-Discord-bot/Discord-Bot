import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, Bot, Context

class Moderation(commands.Cog):
    """A cog to handle moderation commands like kick, ban, and clear messages."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    @commands.hybrid_command()
    @has_permissions(kick_members=True)
    async def kick(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Kick a member from the server."""
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked. Reason: {reason if reason else 'No reason provided.'}")
        except Exception as e:
            await ctx.send(f"Failed to kick {member.mention}: {e}")

    @commands.hybrid_command()
    @has_permissions(ban_members=True)
    async def ban(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Ban a member from the server."""
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned. Reason: {reason if reason else 'No reason provided.'}")
        except Exception as e:
            await ctx.send(f"Failed to ban {member.mention}: {e}")

    @commands.hybrid_command()
    @has_permissions(manage_messages=True)
    async def clear(self, ctx: Context, amount: int = 5):
        """Clear a number of messages from the channel (default 5)."""
        deleted = await ctx.channel.purge(limit=amount+1)  # +1 to include the command message
        await ctx.send(f"Deleted {len(deleted)-1} messages.", delete_after=3)

    @commands.hybrid_command()
    @has_permissions(manage_guild=True)
    async def remove_bot(self, ctx: Context):
        """Remove the bot from the server."""
        if ctx.guild.me.guild_permissions.administrator:
            await ctx.send("I cannot remove myself from this server as I have administrator permissions.")
            return
        try:
            await ctx.guild.leave()
            await ctx.send("I have left the server.")
        except Exception as e:
            await ctx.send(f"Failed to leave the server: {e}")

    @commands.hybrid_command(hidden=True)
    @has_permissions(manage_guild=True)
    async def ban_bot(self, ctx: Context):
        """Ban the bot from the server."""
        if ctx.guild.me.guild_permissions.administrator:
            await ctx.send("I cannot ban myself from this server as I have administrator permissions.")
            return
        try:
            await ctx.guild.ban(ctx.guild.me, reason="Bot banned by command.")
            await ctx.send("I have been banned from the server, f u n n y  t i m e")
        except Exception as e:
            await ctx.send(f"Failed to ban the bot: {e}")

    @commands.hybrid_command(aliases=['slowmode'])
    @has_permissions(manage_channels=True)
    async def slowmode(self, ctx: Context, seconds: int = 0):
        """Set the slowmode for the channel in seconds (0 to disable)."""
        if seconds < 0:
            await ctx.send("Slowmode cannot be set to a negative value.")
            return
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            await ctx.send(f"Slowmode set to {seconds} seconds.")
        except Exception as e:
            await ctx.send(f"Failed to set slowmode: {e}")
    
    @commands.hybrid_command(aliases=['lock'])
    @has_permissions(manage_channels=True)
    async def lock_channel(self, ctx: Context):
        """Lock the current channel so only admins can send messages."""
        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
            await ctx.send(f"{ctx.channel.mention} has been locked.")
        except Exception as e:
            await ctx.send(f"Failed to lock the channel: {e}")

    @commands.hybrid_command(aliases=['unlock'])
    @has_permissions(manage_channels=True)
    async def unlock_channel(self, ctx: Context):
        """Unlock the current channel so everyone can send messages."""
        try:
            await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
            await ctx.send(f"{ctx.channel.mention} has been unlocked.")
        except Exception as e:
            await ctx.send(f"Failed to unlock the channel: {e}")

    @commands.hybrid_command(aliases=['mute'])
    @has_permissions(mute_members=True)
    async def mute_member(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Mute a member in the server."""
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I do not have permission to manage roles.")
            return
        
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            try:
                mute_role = await ctx.guild.create_role(name="Muted", reason="Mute role created by moderation command.")
                for channel in ctx.guild.channels:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
            except Exception as e:
                await ctx.send(f"Failed to create mute role: {e}")
                return
        
        try:
            await member.add_roles(mute_role, reason=reason)
            await ctx.send(f"{member.mention} has been muted. Reason: {reason if reason else 'No reason provided.'}")
        except Exception as e:
            await ctx.send(f"Failed to mute {member.mention}: {e}")

    @commands.hybrid_command(aliases=['unmute'])
    @has_permissions(mute_members=True)
    async def unmute_member(self, ctx: Context, member: discord.Member):
        """Unmute a member in the server."""
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("I do not have permission to manage roles.")
            return
        
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not mute_role:
            await ctx.send("There is no 'Muted' role in this server.")
            return
        
        try:
            await member.remove_roles(mute_role, reason="Unmuted by moderation command.")
            await ctx.send(f"{member.mention} has been unmuted.")
        except Exception as e:
            await ctx.send(f"Failed to unmute {member.mention}: {e}")

    @commands.hybrid_command(aliases=['timeout', 'tempmute'])
    @has_permissions(moderate_members=True)
    async def timeout_member(self, ctx: Context, member: discord.Member, duration: int, *, reason: str = None):
        """Timeout a member for a specified duration in seconds."""
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send("I do not have permission to moderate members.")
            return
        
        try:
            await member.timeout(duration=duration, reason=reason)
            await ctx.send(f"{member.mention} has been timed out for {duration} seconds. Reason: {reason if reason else 'No reason provided.'}")
        except Exception as e:
            await ctx.send(f"Failed to timeout {member.mention}: {e}")

    @commands.hybrid_command(aliases=['untimeout', 'untimemute'])
    @has_permissions(moderate_members=True)
    async def untimeout_member(self, ctx: Context, member: discord.Member):
        """Remove timeout from a member."""
        if not ctx.guild.me.guild_permissions.moderate_members:
            await ctx.send("I do not have permission to moderate members.")
            return
        
        try:
            await member.timeout(None, reason="Timeout removed by moderation command.")
            await ctx.send(f"{member.mention} has been removed from timeout.")
        except Exception as e:
            await ctx.send(f"Failed to remove timeout from {member.mention}: {e}")

async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
