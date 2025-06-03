import discord
from discord.ext import commands
import os
import sys
from dotenv import load_dotenv

def is_developer_or_owner():
    async def predicate(ctx):
        # To remove all variables loaded by dotenv (if you know their names)
        for var in ['BOT_OWNERS', 'BOT_DEVELOPERS']:
            os.environ.pop(var, None)
        load_dotenv()
        if await ctx.bot.is_owner(ctx.author):
            return True
        developer_ids = os.getenv('BOT_DEVELOPERS', '')
        developer_ids = [int(d.strip()) for d in developer_ids.split(',') if d.strip().isdigit()]
        return ctx.author.id in developer_ids
    return commands.check(predicate)

class BotManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @is_developer_or_owner()
    async def shutdown(self, ctx):
        """Shut down the bot (owner or developer only)."""
        await ctx.send("Shutting down...")
        await self.bot.close()

    @commands.hybrid_command()
    @is_developer_or_owner()
    async def restart(self, ctx):
        """Restart the bot (owner or developer only, requires process manager)."""
        await ctx.send("Restarting bot...")
        os.execv(sys.executable, ['python'] + sys.argv)

    @commands.hybrid_command()
    @is_developer_or_owner()
    async def sync(self, ctx):
        """Sync slash commands to all servers (owner or developer only)."""
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally.")

    @commands.hybrid_command()
    @is_developer_or_owner()
    async def load(self, ctx, extension: str):
        """Load a cog (owner or developer only)."""
        try:
            await self.bot.load_extension(f"cogs.{extension}")
            await ctx.send(f"Loaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error loading cog: {e}")

    @commands.hybrid_command()
    @is_developer_or_owner()
    async def unload(self, ctx, extension: str):
        """Unload a cog (owner or developer only)."""
        try:
            await self.bot.unload_extension(f"cogs.{extension}")
            await ctx.send(f"Unloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error unloading cog: {e}")

    @commands.hybrid_command()
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
