import discord
from discord.ext import commands
from discord.ext.commands import has_permissions, Bot, Context

class Moderation(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command()
    @has_permissions(kick_members=True)
    async def kick(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Kick a member from the server."""
        try:
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked. Reason: {reason if reason else 'No reason provided.'}")
        except Exception as e:
            await ctx.send(f"Failed to kick {member.mention}: {e}")

    @commands.command()
    @has_permissions(ban_members=True)
    async def ban(self, ctx: Context, member: discord.Member, *, reason: str = None):
        """Ban a member from the server."""
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned. Reason: {reason if reason else 'No reason provided.'}")
        except Exception as e:
            await ctx.send(f"Failed to ban {member.mention}: {e}")

    @commands.command()
    @has_permissions(manage_messages=True)
    async def clear(self, ctx: Context, amount: int = 5):
        """Clear a number of messages from the channel (default 5)."""
        deleted = await ctx.channel.purge(limit=amount+1)  # +1 to include the command message
        await ctx.send(f"Deleted {len(deleted)-1} messages.", delete_after=3)

async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
