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
            embed = discord.Embed(description=f"{member.mention} has been kicked. Reason: {reason if reason else 'No reason provided.'}", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to kick {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.hybrid_command()
    @has_permissions(ban_members=True)
    async def ban(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Ban a member from the server."""
        try:
            await member.ban(reason=reason)
            embed = discord.Embed(description=f"{member.mention} has been banned. Reason: {reason if reason else 'No reason provided.'}", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to ban {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.hybrid_command()
    @has_permissions(manage_messages=True)
    async def clear(self, ctx: Context, amount: int = 5):
        """Clear a number of messages from the channel (default 5)."""
        deleted = await ctx.channel.purge(limit=amount+1)  # +1 to include the command message
        embed = discord.Embed(description=f"Deleted {len(deleted)-1} messages.", color=discord.Color.orange())
        await ctx.send(embed=embed, delete_after=3)

    @commands.hybrid_command()
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

    @commands.hybrid_command(hidden=True)
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

    @commands.hybrid_command(aliases=['chillchat', 'chill'])
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

    @commands.hybrid_command(aliases=['lock'])
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

    @commands.hybrid_command(aliases=['unlock'])
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

    @commands.hybrid_command(aliases=['mute'])
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
            embed = discord.Embed(description=f"{member.mention} has been muted. Reason: {reason if reason else 'No reason provided.'}", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to mute {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['unmute'])
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

    @commands.hybrid_command(aliases=['timeout', 'tempmute'])
    @has_permissions(moderate_members=True)
    async def timeout_member(self, ctx: Context, member: discord.Member, duration: int, *, reason: str = None):
        """Timeout a member for a specified duration in seconds."""
        if not ctx.guild.me.guild_permissions.moderate_members:
            embed = discord.Embed(description="I do not have permission to moderate members.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        try:
            await member.timeout(duration=duration, reason=reason)
            embed = discord.Embed(description=f"{member.mention} has been timed out for {duration} seconds. Reason: {reason if reason else 'No reason provided.'}", color=discord.Color.orange())
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(description=f"Failed to timeout {member.mention}: {e}", color=discord.Color.red())
            await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=['untimeout', 'untimemute'])
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

async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
