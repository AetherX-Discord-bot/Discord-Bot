import discord
from discord.ext import commands
import sqlite3
import traceback
from datetime import datetime, timezone
from contextlib import closing
from typing import Optional, List, Tuple, Dict, Set
import asyncio

# ==================== CONSTANTS & CONFIGURATION ====================
class Config:
    EMBED_COLOR = discord.Colour.from_rgb(0, 102, 204)  # Dark blueish color
    DB_PATH = 'AetherX.db'  # Updated database file path
    LOG_FILE = 'bot.log'    # Log file path
    ALLOWED_USERS = {435125886996709377, 811016330517676073, 1286383453016686705}  # Allowed user IDs - Fixed typo in first ID
    STARTUP_TIME = None  # Will be set when bot starts

# ==================== DATABASE HANDLER ====================
class DatabaseHandler:
    def __init__(self, db_path: str):
        self.connection = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self.connection.row_factory = sqlite3.Row  # Use row factory for easier access
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize database tables"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS banned_servers (
                    server_id INTEGER PRIMARY KEY,
                    banned_by INTEGER,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_owners (
                    server_id INTEGER PRIMARY KEY,
                    owner_id INTEGER,
                    owner_name TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Add startup tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS startup_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    startup_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    guild_count INTEGER
                )
            """)
            self.connection.commit()

    def ban_server(self, server_id: int, banned_by: int, reason: Optional[str]) -> None:
        """Ban a server from adding the bot"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO banned_servers (server_id, banned_by, reason) VALUES (?, ?, ?)",
                (server_id, banned_by, reason)
            )
            self.connection.commit()

    def unban_server(self, server_id: int) -> bool:
        """Unban a server from adding the bot"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute("DELETE FROM banned_servers WHERE server_id = ?", (server_id,))
            self.connection.commit()
            return cursor.rowcount > 0

    def get_banned_servers(self) -> List[sqlite3.Row]:
        """Get all banned servers as Row objects"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute("SELECT server_id, banned_by, reason, timestamp FROM banned_servers")
            return cursor.fetchall()

    def is_server_banned(self, server_id: int) -> bool:
        """Check if a server is banned"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute("SELECT 1 FROM banned_servers WHERE server_id = ?", (server_id,))
            return cursor.fetchone() is not None

    def update_server_owner(self, server_id: int, owner_id: int, owner_name: str) -> None:
        """Update server owner information"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute(
                "INSERT OR REPLACE INTO server_owners (server_id, owner_id, owner_name) VALUES (?, ?, ?)",
                (server_id, owner_id, owner_name)
            )
            self.connection.commit()

    def get_server_owner(self, server_id: int) -> Optional[Tuple[int, str]]:
        """Get server owner info from database"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute("SELECT owner_id, owner_name FROM server_owners WHERE server_id = ?", (server_id,))
            result = cursor.fetchone()
            return result if result else None

    def log_startup(self, guild_count: int) -> None:
        """Log bot startup to track restarts"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute(
                "INSERT INTO startup_tracking (startup_time, guild_count) VALUES (datetime('now'), ?)",
                (guild_count,)
            )
            self.connection.commit()

    def get_last_startup_time(self) -> Optional[datetime]:
        """Get the last startup time"""
        with closing(self.connection.cursor()) as cursor:
            cursor.execute("SELECT startup_time FROM startup_tracking ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            if result:
                return datetime.fromisoformat(result[0].replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
            return None

    def close(self) -> None:
        """Close the database connection"""
        self.connection.close()

# ==================== LOGGER ====================
class BotLogger:
    def __init__(self, log_file: str):
        self.log_file = log_file

    def log(self, message: str, level: str = "INFO") -> None:
        """Log events to file with UTF-8 encoding"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {message}\n")
        except Exception as e:
            print(f"Failed to write to log file: {e}")  # Fallback to console output

# ==================== EMBED UTILITIES ====================
class EmbedFactory:
    @staticmethod
    def create_error_embed(title: str, description: str) -> discord.Embed:
        """Create an error embed"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=discord.Colour.red()
        )
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def create_success_embed(title: str, description: str) -> discord.Embed:
        """Create a success embed"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=Config.EMBED_COLOR
        )
        embed.timestamp = discord.utils.utcnow()
        return embed

    @staticmethod
    def create_server_info_embed(guild: discord.Guild, is_banned: bool) -> discord.Embed:
        """Create a server information embed with proper owner info"""
        embed = discord.Embed(
            title=f"📊 Server Info: {guild.name}",
            color=discord.Colour.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        # Get owner with proper display
        owner = guild.owner
        owner_display = f"{owner} (ID: {guild.owner_id})" if owner else f"Unknown (ID: {guild.owner_id})"
        
        embed.add_field(name="Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="Owner", value=owner_display, inline=True)
        embed.add_field(name="Member Count", value=f"👥 {guild.member_count}", inline=True)
        embed.add_field(name="Created At", value=f"📅 {guild.created_at.strftime('%Y-%m-%d')}", inline=True)
        
        bot_join_date = guild.me.joined_at.strftime("%Y-%m-%d %H:%M:%S") if guild.me.joined_at else "Unknown"
        embed.add_field(name="Bot Added", value=bot_join_date, inline=True)
        
        status_emoji = "🚫" if is_banned else "✅"
        embed.add_field(name="Status", value=f"{status_emoji} {'BANNED' if is_banned else 'Allowed'}", inline=True)
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(text=f"Server ID: {guild.id}")
        return embed

# ==================== MAIN COG ====================
class Servers(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseHandler(Config.DB_PATH)
        self.logger = BotLogger(Config.LOG_FILE)
        self.active_interactions: Dict[int, discord.ui.View] = {}  # Track active interactions by user ID
        self.initial_guilds: Set[int] = set()  # Track guilds present at startup
        self.startup_complete = False
        self.skip_guild_remove = False  # Flag to skip guild remove notifications during startup
        Config.STARTUP_TIME = discord.utils.utcnow()  # Set global startup time

    @commands.Cog.listener()
    async def on_ready(self):
        """Handle bot startup - cache server owners and track initial guilds"""
        if not self.startup_complete:
            self.logger.log(f"Bot is ready. Connected to {len(self.bot.guilds)} guilds.")
            
            # Skip guild remove notifications during startup
            self.skip_guild_remove = True
            
            # Store initial guilds before any notifications
            self.initial_guilds = {guild.id for guild in self.bot.guilds}
            
            # Cache server owners
            self.logger.log("Caching server owners...")
            cache_tasks = []
            for guild in self.bot.guilds:
                task = self._cache_guild_owner(guild)
                cache_tasks.append(task)
            
            await asyncio.gather(*cache_tasks, return_exceptions=True)
            
            # Log startup for tracking
            self.db.log_startup(len(self.bot.guilds))
            
            # Mark startup as complete
            self.startup_complete = True
            
            # Short delay before re-enabling notifications
            await asyncio.sleep(2)
            self.skip_guild_remove = False
            
            self.logger.log(f"Startup complete. Tracking {len(self.initial_guilds)} initial guilds.")

    async def _cache_guild_owner(self, guild: discord.Guild) -> None:
        """Cache a single guild owner with error handling"""
        try:
            owner = guild.owner
            if not owner and guild.owner_id:
                try:
                    owner = await guild.fetch_member(guild.owner_id)
                except (discord.NotFound, discord.HTTPException):
                    owner = None
            
            if owner:
                self.db.update_server_owner(guild.id, owner.id, str(owner))
            else:
                self.db.update_server_owner(guild.id, guild.owner_id, "Unknown")
                
        except Exception as e:
            self.logger.log(f"Failed to cache owner for guild {guild.id}: {str(e)}", "WARNING")

    async def is_allowed_user(self, ctx: commands.Context) -> bool:
        """Check if user is in the allowed list"""
        return ctx.author.id in Config.ALLOWED_USERS

    async def notify_allowed_users(self, embed: discord.Embed, skip_author: Optional[int] = None) -> None:
        """Notify all allowed users with the given embed"""
        notification_tasks = []
        for user_id in Config.ALLOWED_USERS:
            if skip_author and user_id == skip_author:
                continue
                
            async def notify_user(uid: int):
                try:
                    user = await self.bot.fetch_user(uid)
                    if user:
                        await user.send(embed=embed)
                except discord.Forbidden:
                    self.logger.log(f"User {uid} has DMs disabled", "WARNING")
                except Exception as e:
                    self.logger.log(f"Failed to notify user {uid}: {e}", "ERROR")

            notification_tasks.append(notify_user(user_id))
        
        if notification_tasks:
            await asyncio.gather(*notification_tasks, return_exceptions=True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Handle bot joining a new server"""
        try:
            self.logger.log(f"Joined server: {guild.name} ({guild.id})", "INFO")

            # Cache owner immediately
            await self._cache_guild_owner(guild)

            # Check if server is banned
            if self.db.is_server_banned(guild.id):
                await guild.leave()
                self.logger.log(f"Left banned server: {guild.name} ({guild.id})", "INFO")
                
                # Get ban details for notification
                banned_servers = self.db.get_banned_servers()
                ban_details = next((s for s in banned_servers if s['server_id'] == guild.id), None)
                
                if ban_details:
                    banned_by = ban_details['banned_by']
                    reason = ban_details['reason']
                    
                    embed = discord.Embed(
                        title="🚫 Banned Server Join Attempt",
                        description=(
                            f"**Server:** {guild.name}\n"
                            f"**Server ID:** `{guild.id}`\n"
                            f"**Member Count:** {guild.member_count}\n"
                            f"**Owner:** {guild.owner} (ID: {guild.owner_id})\n"
                            f"**Banned by:** <@{banned_by}>\n"
                            f"**Reason:** {reason or 'No reason provided'}"
                        ),
                        color=discord.Color.red(),
                        timestamp=discord.utils.utcnow()
                    )
                    embed.set_footer(text="Automatically removed banned server")
                    
                    await self.notify_allowed_users(embed)
                return

            # Send join notification (only if not during startup)
            if self.startup_complete:
                embed = discord.Embed(
                    title="🟢 Bot Added to New Server",
                    color=discord.Color.green(),
                    description=(
                        f"**Server Name:** {guild.name}\n"
                        f"**Server ID:** `{guild.id}`\n"
                        f"**Member Count:** {guild.member_count}\n"
                        f"**Owner:** {guild.owner} (ID: {guild.owner_id})"
                    ),
                    timestamp=discord.utils.utcnow()
                )
                if guild.icon:
                    embed.set_thumbnail(url=guild.icon.url)
                
                await self.notify_allowed_users(embed)

        except Exception as e:
            self.logger.log(f"Error in on_guild_join: {e}", "ERROR")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Handle bot being removed from a server"""
        try:
            # Skip notifications during startup or if flag is set
            if self.skip_guild_remove or not self.startup_complete:
                self.logger.log(f"Ignoring guild remove during startup: {guild.name} ({guild.id})", "DEBUG")
                return
                
            # Check if this was actually a server we were in (not a startup artifact)
            if guild.id in self.initial_guilds:
                # This was a legitimate removal, not a startup artifact
                self.initial_guilds.discard(guild.id)
                
                self.logger.log(f"Left server: {guild.name} ({guild.id})", "INFO")

                embed = discord.Embed(
                    title="🔴 Bot Removed from Server",
                    color=discord.Color.red(),
                    description=(
                        f"**Server Name:** {guild.name}\n"
                        f"**Server ID:** `{guild.id}`\n"
                        f"**Member Count:** {guild.member_count}\n"
                        f"**Owner:** {guild.owner} (ID: {guild.owner_id})"
                    ),
                    timestamp=discord.utils.utcnow()
                )
                if guild.icon:
                    embed.set_thumbnail(url=guild.icon.url)
                
                await self.notify_allowed_users(embed)
            else:
                # This was likely a startup artifact - ignore
                self.logger.log(f"Ignoring startup artifact removal: {guild.name} ({guild.id})", "DEBUG")

        except Exception as e:
            self.logger.log(f"Error in on_guild_remove: {str(e)}", "ERROR")
            traceback.print_exc()

    @commands.command(name="servers", hidden=True)
    async def list_servers(self, ctx: commands.Context) -> None:
        """List all servers the bot is in with paginated compact menu"""
        if not await self.is_allowed_user(ctx):
            return await ctx.send(embed=EmbedFactory.create_error_embed(
                "Permission Denied",
                "You are not authorized to use this command."
            ))

        # Clean up any old interactions
        if ctx.author.id in self.active_interactions:
            old_view = self.active_interactions.pop(ctx.author.id)
            old_view.stop()

        servers = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        items_per_page = 10
        pages = max(1, (len(servers) + items_per_page - 1) // items_per_page)

        class Paginator(discord.ui.View):
            def __init__(self, user_id: int, *, timeout=120):
                super().__init__(timeout=timeout)
                self.current_page = 0
                self.user_id = user_id
                self.servers = servers
                self.items_per_page = items_per_page
                self.total_pages = pages
                self.cog = None
                self.message = None

            @property
            def db(self):
                return self.cog.db

            async def create_embed(self):
                start = self.current_page * self.items_per_page
                end = start + self.items_per_page
                embed = discord.Embed(
                    title=f"📋 Servers ({len(self.servers)}) - Page {self.current_page + 1}/{self.total_pages}",
                    color=Config.EMBED_COLOR,
                    timestamp=discord.utils.utcnow()
                )
                
                for i, guild in enumerate(self.servers[start:end], start=start + 1):
                    try:
                        owner_info = self.db.get_server_owner(guild.id)
                        if owner_info:
                            owner_display = f"{owner_info[1]} (ID: {owner_info[0]})"
                        else:
                            owner = guild.owner or await guild.fetch_member(guild.owner_id)
                            owner_display = f"{owner} (ID: {guild.owner_id})" if owner else f"Unknown (ID: {guild.owner_id})"
                    except:
                        owner_display = f"Unknown (ID: {guild.owner_id})"
                    
                    ban_status = "🚫 " if self.db.is_server_banned(guild.id) else ""
                    embed.add_field(
                        name=f"{i}. {ban_status}{guild.name}",
                        value=(
                            f"ID: `{guild.id}`\n"
                            f"👥 Members: {guild.member_count}\n"
                            f"👑 Owner: {owner_display}"
                        ),
                        inline=False
                    )
                
                embed.set_footer(text=f"Total Members: {sum(g.member_count for g in self.servers)}")
                return embed

            @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary, disabled=True, row=0)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("You are not allowed to use this.", ephemeral=True)
                
                self.current_page -= 1
                button.disabled = self.current_page == 0
                self.next.disabled = False
                await interaction.response.edit_message(embed=await self.create_embed(), view=self)

            @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary, disabled=pages <= 1, row=0)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("You are not allowed to use this.", ephemeral=True)
                
                self.current_page += 1
                button.disabled = self.current_page == self.total_pages - 1
                self.prev.disabled = False
                await interaction.response.edit_message(embed=await self.create_embed(), view=self)

            @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=1)
            async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("You are not allowed to use this.", ephemeral=True)
                
                await interaction.message.delete()
                self.stop()
                if self.cog and interaction.user.id in self.cog.active_interactions:
                    self.cog.active_interactions.pop(interaction.user.id)

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                
                if self.message:
                    try:
                        await self.message.edit(view=self)
                    except:
                        pass
                
                if self.cog and self.user_id in self.cog.active_interactions:
                    self.cog.active_interactions.pop(self.user_id)

        view = Paginator(ctx.author.id)
        view.cog = self
        message = await ctx.send(embed=await view.create_embed(), view=view)
        view.message = message
        self.active_interactions[ctx.author.id] = view

    @commands.command(name="banserver", hidden=True)
    async def ban_server(self, ctx: commands.Context, server_id: int, *, reason: str = None) -> None:
        """Ban a server from adding the bot"""
        if not await self.is_allowed_user(ctx):
            return await ctx.send(embed=EmbedFactory.create_error_embed(
                "Permission Denied",
                "You are not authorized to use this command."
            ))

        guild = self.bot.get_guild(server_id)
        server_name = guild.name if guild else "Unknown Server"

        self.db.ban_server(server_id, ctx.author.id, reason)

        embed = discord.Embed(
            title="🔒 Server Banned",
            description=(
                f"Server `{server_name}` (ID: `{server_id}`) can no longer add this bot.\n"
                f"**Reason:** {reason or 'No reason provided'}"
            ),
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(embed=embed)
        self.logger.log(f"Banned server {server_name} ({server_id}) for reason: {reason}", "INFO")

        if guild:
            await guild.leave()
            self.logger.log(f"Left banned server {guild.name} ({guild.id})", "INFO")

    @commands.command(name="unbanserver", hidden=True)
    async def unban_server(self, ctx: commands.Context, server_id: int) -> None:
        """Unban a server from adding the bot"""
        if not await self.is_allowed_user(ctx):
            return await ctx.send(embed=EmbedFactory.create_error_embed(
                "Permission Denied",
                "You are not authorized to use this command."
            ))

        if self.db.unban_server(server_id):
            await ctx.send(embed=EmbedFactory.create_success_embed(
                "Server Unbanned",
                f"Server ID `{server_id}` has been removed from the ban list."
            ))
            self.logger.log(f"Unbanned server {server_id}", "INFO")
        else:
            await ctx.send(embed=EmbedFactory.create_success_embed(
                "No Action Taken",
                f"Server ID `{server_id}` wasn't in the ban list."
            ))

    @commands.command(name="listbanned", hidden=True)
    async def list_banned_servers(self, ctx: commands.Context) -> None:
        """List all banned servers"""
        if not await self.is_allowed_user(ctx):
            return await ctx.send(embed=EmbedFactory.create_error_embed(
                "Permission Denied",
                "You are not authorized to use this command."
            ))

        banned_servers = self.db.get_banned_servers()

        if not banned_servers:
            return await ctx.send(embed=EmbedFactory.create_success_embed(
                "No Banned Servers",
                "There are currently no banned servers."
            ))

        embed = discord.Embed(
            title="🚫 Banned Servers",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )

        for server in banned_servers:
            server_id = server['server_id']
            banned_by = server['banned_by']
            reason = server['reason']
            timestamp = server['timestamp']
            
            guild = self.bot.get_guild(server_id)
            embed.add_field(
                name=f"Server: {guild.name if guild else 'Unknown'} (ID: {server_id})",
                value=(
                    f"Banned by: <@{banned_by}>\n"
                    f"Reason: {reason or 'No reason provided'}\n"
                    f"Date: {timestamp}"
                ),
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="infopull", hidden=True)
    async def infopull_server(self, ctx: commands.Context, server_id: int) -> None:
        """Get detailed information about a server"""
        if not await self.is_allowed_user(ctx):
            return await ctx.send(embed=EmbedFactory.create_error_embed(
                "Permission Denied",
                "You are not authorized to use this command."
            ))
        
        guild = self.bot.get_guild(server_id)
        if guild is None:
            return await ctx.send(embed=EmbedFactory.create_error_embed(
                "Error",
                f"Could not find a server with ID `{server_id}`."
            ))
        
        embed = EmbedFactory.create_server_info_embed(guild, self.db.is_server_banned(guild.id))
        await ctx.send(embed=embed)

    @commands.command(name="serverstats", hidden=True)
    async def server_stats(self, ctx: commands.Context) -> None:
        """Show bot statistics"""
        if not await self.is_allowed_user(ctx):
            return await ctx.send(embed=EmbedFactory.create_error_embed(
                "Permission Denied",
                "You are not authorized to use this command."
            ))
        
        total_members = sum(g.member_count for g in self.bot.guilds)
        total_guilds = len(self.bot.guilds)
        banned_servers = len(self.db.get_banned_servers())
        
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=Config.EMBED_COLOR,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(name="Total Servers", value=f"📁 {total_guilds}", inline=True)
        embed.add_field(name="Total Members", value=f"👥 {total_members}", inline=True)
        embed.add_field(name="Banned Servers", value=f"🚫 {banned_servers}", inline=True)
        
        # Add average members per server
        avg_members = total_members / total_guilds if total_guilds > 0 else 0
        embed.add_field(name="Avg. Members/Server", value=f"📈 {avg_members:.1f}", inline=True)
        
        # Add largest and smallest servers
        if total_guilds > 0:
            largest = max(self.bot.guilds, key=lambda g: g.member_count)
            smallest = min(self.bot.guilds, key=lambda g: g.member_count)
            embed.add_field(name="Largest Server", value=f"{largest.name}\n👥 {largest.member_count}", inline=True)
            embed.add_field(name="Smallest Server", value=f"{smallest.name}\n👥 {smallest.member_count}", inline=True)
        
        embed.set_footer(text=f"Uptime: {discord.utils.utcnow() - Config.STARTUP_TIME}")
        
        await ctx.send(embed=embed)

    def cog_unload(self) -> None:
        """Clean up when cog is unloaded"""
        for view in self.active_interactions.values():
            view.stop()
        self.active_interactions.clear()
        self.db.close()
        self.logger.log("Servers cog unloaded", "INFO")

async def setup(bot: commands.Bot) -> None:
    """Add the cog to the bot"""
    await bot.add_cog(Servers(bot))