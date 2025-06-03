import discord
from discord.ext import commands
import sys

class BotManagement(commands.Cog):
    """A cog to manage the bot, including shutdown, restart, and cog management."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    def is_developer_or_owner(self, user_id):
        owner_ids = self.config.get('BOT_OWNERS', [])
        developer_ids = self.config.get('BOT_DEVELOPERS', [])
        all_ids = set(owner_ids + developer_ids)
        return user_id in all_ids

    def developer_or_owner_check(self):
        async def predicate(ctx):
            if await ctx.bot.is_owner(ctx.author):
                return True
            return self.is_developer_or_owner(ctx.author.id)
        return commands.check(predicate)

    @commands.hybrid_command()
    @commands.check(lambda self, ctx: self.is_developer_or_owner(ctx.author.id))
    async def shutdown(self, ctx):
        """Shut down the bot (owner or developer only)."""
        await ctx.send("Shutting down...")
        await self.bot.close()

    @commands.hybrid_command()
    @commands.check(lambda self, ctx: self.is_developer_or_owner(ctx.author.id))
    async def restart(self, ctx):
        """Restart the bot (owner or developer only, requires process manager)."""
        await ctx.send("Restarting bot...")
        sys.execv(sys.executable, ['python'] + sys.argv)

    @commands.hybrid_command()
    @commands.check(lambda self, ctx: self.is_developer_or_owner(ctx.author.id))
    async def sync(self, ctx):
        """Sync slash commands to all servers (owner or developer only)."""
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally.")

    @commands.hybrid_command()
    @commands.check(lambda self, ctx: self.is_developer_or_owner(ctx.author.id))
    async def load(self, ctx, extension: str):
        """Load a cog (owner or developer only)."""
        try:
            await self.bot.load_extension(f"cogs.{extension}")
            await ctx.send(f"Loaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error loading cog: {e}")

    @commands.hybrid_command()
    @commands.check(lambda self, ctx: self.is_developer_or_owner(ctx.author.id))
    async def unload(self, ctx, extension: str):
        """Unload a cog (owner or developer only)."""
        try:
            await self.bot.unload_extension(f"cogs.{extension}")
            await ctx.send(f"Unloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error unloading cog: {e}")

    @commands.hybrid_command()
    @commands.check(lambda self, ctx: self.is_developer_or_owner(ctx.author.id))
    async def reload(self, ctx, extension: str):
        """Reload a cog (owner or developer only)."""
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            await ctx.send(f"Reloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error reloading cog: {e}")

async def setup(bot):
    await bot.add_cog(BotManagement(bot))
