import discord
from discord.ext import commands
import sys

def is_developer_or_owner():
    async def predicate(ctx):
        config = getattr(ctx.bot, 'config', {})
        owner_ids = config.get('BOT_OWNERS', [])
        developer_ids = config.get('BOT_DEVELOPERS', [])
        all_ids = set(owner_ids + developer_ids)
        if await ctx.bot.is_owner(ctx.author):
            return True
        return ctx.author.id in all_ids
    return commands.check(predicate)

class BotManagement(commands.Cog):
    """A cog to manage the bot, including shutdown, restart, and cog management."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    @commands.hybrid_command(aliases=["die", "exit", "quit", "close", "terminate"])
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Shut down the bot (owner only)."""
        await ctx.send("Shutting down...")
        await self.bot.close()

    @commands.hybrid_command(aliases=["restartbot", "reboot", "relaunch", "reloadbot"])
    @is_developer_or_owner()
    async def restart(self, ctx):
        """Restart the bot (owner or developer only, requires process manager)."""
        await ctx.send("Restarting bot...")
        import os
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.hybrid_command(aliases=["synccommands", "syncslash", "syncglobal"])
    @is_developer_or_owner()
    async def sync(self, ctx):
        """Sync slash commands to all servers (owner or developer only)."""
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally.")

    @commands.hybrid_command(aliases=["loadcog", "loadextension"])
    @is_developer_or_owner()
    async def load(self, ctx, extension: str):
        """Load a cog (owner or developer only)."""
        try:
            await self.bot.load_extension(f"cogs.{extension}")
            await ctx.send(f"Loaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error loading cog: {e}")

    @commands.hybrid_command(aliases=["unloadcog", "unloadextension"])
    @is_developer_or_owner()
    async def unload(self, ctx, extension: str):
        """Unload a cog (owner or developer only)."""
        try:
            await self.bot.unload_extension(f"cogs.{extension}")
            await ctx.send(f"Unloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error unloading cog: {e}")

    @commands.hybrid_command(aliases=["reloadcog", "reloadextension"])
    @is_developer_or_owner()
    async def reload(self, ctx, extension: str):
        """Reload a cog (owner or developer only)."""
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            await ctx.send(f"Reloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error reloading cog: {e}")

async def setup(bot):
    await bot.add_cog(BotManagement(bot))
