import discord
from discord.ext import commands
import sys
import sqlite3
import os

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
        # Always resolve the database path relative to the workspace root
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))

    def is_server_whitelisted(self, server_id):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT whitelisted_status FROM servers WHERE server_id = ?", (server_id,))
            row = c.fetchone()
            conn.close()
            return bool(row and row[0])
        except Exception:
            return False

    def is_server_blacklisted(self, server_id):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT blacklisted_status FROM servers WHERE server_id = ?", (server_id,))
            row = c.fetchone()
            conn.close()
            return bool(row and row[0])
        except Exception:
            return False

    @commands.command(aliases=["die", "exit", "quit", "close", "terminate"])
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Shut down the bot (owner only)."""
        await ctx.send("Shutting down...")
        await self.bot.close()

    @commands.command(aliases=["restartbot", "reboot", "relaunch", "reloadbot"])
    @is_developer_or_owner()
    async def restart(self, ctx):
        """Restart the bot."""
        embed = discord.Embed(
            title="Bot Restarting",
            description=f"Restart initiated by {ctx.author.mention} ({ctx.author.id}). Notifying all developers and owners...",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        # Notify all devs and owners
        notified = []
        config = getattr(self, 'config', getattr(self.bot, 'config', {}))
        owner_ids = config.get('BOT_OWNERS', [])
        developer_ids = config.get('BOT_DEVELOPERS', [])
        all_ids = set(owner_ids + developer_ids)
        for user_id in all_ids:
            try:
                user = await self.bot.fetch_user(user_id)
                if user:
                    notify_embed = discord.Embed(
                        title="Bot Restart Notification",
                        description=f"The bot is being restarted by {ctx.author.mention} ({ctx.author.id}) at their request.",
                        color=discord.Color.orange()
                    )
                    await user.send(embed=notify_embed)
                    notified.append(user_id)
            except Exception:
                continue  # Skip if failed to notify
        import os
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @commands.command(aliases=["synccommands", "syncslash", "syncglobal"])
    @is_developer_or_owner()
    async def sync(self, ctx):
        """Sync slash commands to all servers."""
        synced = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally.")

    @commands.command(aliases=["loadcog", "loadextension"])
    @is_developer_or_owner()
    async def load(self, ctx, extension: str):
        """Load a cog."""
        try:
            await self.bot.load_extension(f"cogs.{extension}")
            await ctx.send(f"Loaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error loading cog: {e}")

    @commands.command(aliases=["unloadcog", "unloadextension"])
    @is_developer_or_owner()
    async def unload(self, ctx, extension: str):
        """Unload a cog."""
        try:
            await self.bot.unload_extension(f"cogs.{extension}")
            await ctx.send(f"Unloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error unloading cog: {e}")

    @commands.command(aliases=["reloadcog", "reloadextension"])
    @is_developer_or_owner()
    async def reload(self, ctx, extension: str):
        """Reload a cog."""
        try:
            await self.bot.reload_extension(f"cogs.{extension}")
            await ctx.send(f"Reloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error reloading cog: {e}")

    @commands.command(aliases=["servers", "guilds", "listservers"])
    @is_developer_or_owner()
    async def serverlist(self, ctx):
        """Show a list of servers the bot is in."""
        guilds = self.bot.guilds
        if not guilds:
            await ctx.send("I'm not in any servers!")
            return
        embed = discord.Embed(title="Servers I'm In", color=discord.Color.blue())
        for g in guilds:
            embed.add_field(name=g.name, value=f"ID: {g.id}", inline=False)
        embed.set_footer(text=f"Total servers: {len(guilds)}")
        await ctx.send(embed=embed)

    @commands.command(aliases=["guilddetails"]) 
    @is_developer_or_owner()
    async def serverdetails(self, ctx, server_id: int):
        """Show detailed info about a server by its ID."""
        guild = discord.utils.get(self.bot.guilds, id=server_id)
        if not guild:
            await ctx.send(f"I'm not in a server with ID {server_id}.")
            return
        owner = guild.owner or await self.bot.fetch_user(guild.owner_id)
        # Determine bot access status
        whitelisted = self.is_server_whitelisted(server_id)
        blacklisted = self.is_server_blacklisted(server_id)
        if blacklisted:
            access_status = "Blacklisted (No Access)"
        elif whitelisted:
            access_status = "Whitelisted (Full Access)"
        else:
            access_status = "Default (Normal Access)"
        embed = discord.Embed(title=f"Server Details: {guild.name}", color=discord.Color.purple())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.add_field(name="Server ID", value=guild.id)
        embed.add_field(name="Owner", value=f"{owner} ({owner.id})")
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Created At", value=guild.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        embed.add_field(name="Boosts", value=guild.premium_subscription_count)
        embed.add_field(name="Channels", value=len(guild.channels))
        embed.add_field(name="Bot Access Status", value=access_status, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command(aliases=["forceleave", "kickself"])
    @is_developer_or_owner()
    async def forceremovebot(self, ctx, server_id: int):
        """Force the bot to leave a server by its ID. (Will not work on whitelisted servers)"""
        if self.is_server_whitelisted(server_id):
            await ctx.send(f"Cannot force remove: Server {server_id} is whitelisted.")
            return
        guild = discord.utils.get(self.bot.guilds, id=server_id)
        if not guild:
            await ctx.send(f"I'm not in a server with ID {server_id}.")
            return
        try:
            await guild.leave()
            await ctx.send(f"Successfully left the server: {guild.name} (ID: {guild.id})")
        except Exception as e:
            await ctx.send(f"Failed to leave the server: {e}")

    @commands.command(aliases=["customloadcog", "customloadextension", "cloadcog", "cloadextension"])
    @is_developer_or_owner()
    async def customload(self, ctx, extension: str):
        """Load a cog."""
        try:
            await self.bot.load_extension(f"custom cogs.{extension}")
            await ctx.send(f"Loaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error loading cog: {e}")

    @commands.command(aliases=["customunloadcog", "customunloadextension", "cunloadcog", "cunloadextension"])
    @is_developer_or_owner()
    async def customunload(self, ctx, extension: str):
        """Unload a cog."""
        try:
            await self.bot.unload_extension(f"custom cogs.{extension}")
            await ctx.send(f"Unloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error unloading cog: {e}")

    @commands.command(aliases=["customreloadcog", "customreloadextension", "creloadcog", "creloadextension"])
    @is_developer_or_owner()
    async def customreload(self, ctx, extension: str):
        """Reload a cog."""
        try:
            await self.bot.reload_extension(f"custom cogs.{extension}")
            await ctx.send(f"Reloaded cog: {extension}")
        except Exception as e:
            await ctx.send(f"Error reloading cog: {e}")

    @commands.command()
    @is_developer_or_owner()
    async def whitelist(self, ctx, server_id: int):
        """Toggle whitelisting for a server by its ID. Cannot be both whitelisted and blacklisted."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Check blacklist status
            c.execute("SELECT blacklisted_status FROM servers WHERE server_id = ?", (server_id,))
            blacklisted = c.fetchone()
            if blacklisted and blacklisted[0]:
                await ctx.send(f"Cannot whitelist: Server {server_id} is currently blacklisted. Remove from blacklist first.")
                conn.close()
                return
            c.execute("SELECT whitelisted_status FROM servers WHERE server_id = ?", (server_id,))
            row = c.fetchone()
            if row and row[0]:
                # Already whitelisted, remove whitelist
                c.execute("UPDATE servers SET whitelisted_status = 0 WHERE server_id = ?", (server_id,))
                conn.commit()
                conn.close()
                await ctx.send(f"Server {server_id} has been removed from the whitelist.")
            else:
                # Not whitelisted, add whitelist
                c.execute("INSERT OR IGNORE INTO servers (server_id, whitelisted_status) VALUES (?, 1)", (server_id,))
                c.execute("UPDATE servers SET whitelisted_status = 1 WHERE server_id = ?", (server_id,))
                conn.commit()
                conn.close()
                await ctx.send(f"Server {server_id} has been whitelisted.")
        except Exception as e:
            await ctx.send(f"Failed to toggle whitelist for server: {e}")

    @commands.command()
    @is_developer_or_owner()
    async def blacklist(self, ctx, server_id: int):
        """Toggle blacklisting for a server by its ID. Cannot be both blacklisted and whitelisted. The bot will immediately leave if present when blacklisted."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Check whitelist status
            c.execute("SELECT whitelisted_status FROM servers WHERE server_id = ?", (server_id,))
            whitelisted = c.fetchone()
            if whitelisted and whitelisted[0]:
                await ctx.send(f"Cannot blacklist: Server {server_id} is currently whitelisted. Remove from whitelist first.")
                conn.close()
                return
            c.execute("SELECT blacklisted_status FROM servers WHERE server_id = ?", (server_id,))
            row = c.fetchone()
            if row and row[0]:
                # Already blacklisted, remove blacklist
                c.execute("UPDATE servers SET blacklisted_status = 0 WHERE server_id = ?", (server_id,))
                conn.commit()
                conn.close()
                await ctx.send(f"Server {server_id} has been removed from the blacklist.")
            else:
                # Not blacklisted, add blacklist
                c.execute("INSERT OR IGNORE INTO servers (server_id, blacklisted_status) VALUES (?, 1)", (server_id,))
                c.execute("UPDATE servers SET blacklisted_status = 1 WHERE server_id = ?", (server_id,))
                conn.commit()
                conn.close()
                guild = discord.utils.get(self.bot.guilds, id=server_id)
                if guild:
                    await guild.leave()
                    await ctx.send(f"Server {server_id} has been blacklisted and the bot has left the server.")
                else:
                    await ctx.send(f"Server {server_id} has been blacklisted. The bot is not currently in that server.")
        except Exception as e:
            await ctx.send(f"Failed to toggle blacklist for server: {e}")

async def setup(bot):
    await bot.add_cog(BotManagement(bot))
