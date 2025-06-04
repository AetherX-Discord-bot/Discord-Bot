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

async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
