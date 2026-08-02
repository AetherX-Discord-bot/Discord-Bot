import discord
import sqlite3
from discord import app_commands
from discord.ext import commands
from typing import Dict, Any

class WelcomeCog(commands.Cog):
    """Welcome and goodbye system with per-guild configuration using SQLite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "AetherX.db"               # Your database file
        self.config_cache: Dict[str, dict] = {}   # guild_id_str -> settings
        self._init_db()
        self._load_all_configs()

    # -------------------- Database setup and helpers --------------------

    def _init_db(self):
        """Create the guild_config table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS guild_config (
                    guild_id INTEGER PRIMARY KEY,
                    welcome_channel_id INTEGER,
                    goodbye_channel_id INTEGER,
                    welcome_message TEXT,
                    goodbye_message TEXT,
                    welcome_enabled INTEGER DEFAULT 1,
                    goodbye_enabled INTEGER DEFAULT 1
                )
            ''')
            conn.commit()

    def _load_all_configs(self):
        """Load all guild configurations from the database into the cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('SELECT * FROM guild_config')
            for row in cursor.fetchall():
                gid = str(row['guild_id'])
                self.config_cache[gid] = {
                    "welcome_channel_id": row['welcome_channel_id'],
                    "goodbye_channel_id": row['goodbye_channel_id'],
                    "welcome_message": row['welcome_message'] or "Welcome {member.mention} to {guild.name}! 🎉",
                    "goodbye_message": row['goodbye_message'] or "**{member}** has left the server. 👋",
                    "welcome_enabled": bool(row['welcome_enabled']),
                    "goodbye_enabled": bool(row['goodbye_enabled'])
                }

    def _save_guild_config(self, guild_id: int, config: dict):
        """Insert or replace a guild's configuration in the DB and update the cache."""
        gid_str = str(guild_id)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO guild_config (
                    guild_id, welcome_channel_id, goodbye_channel_id,
                    welcome_message, goodbye_message, welcome_enabled, goodbye_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                guild_id,
                config.get("welcome_channel_id"),
                config.get("goodbye_channel_id"),
                config.get("welcome_message"),
                config.get("goodbye_message"),
                1 if config.get("welcome_enabled", True) else 0,
                1 if config.get("goodbye_enabled", True) else 0
            ))
            conn.commit()
        # Update cache
        self.config_cache[gid_str] = config

    def _get_guild_config(self, guild_id: int | None) -> dict:
        """Retrieve config for a guild; create default if absent."""
        if guild_id is None:
            raise ValueError("Guild ID is required.")
        gid_str = str(guild_id)
        if gid_str not in self.config_cache:
            default = {
                "welcome_channel_id": None,
                "goodbye_channel_id": None,
                "welcome_message": "Welcome {member.mention} to {guild.name}! 🎉",
                "goodbye_message": "**{member}** has left the server. 👋",
                "welcome_enabled": True,
                "goodbye_enabled": True
            }
            self._save_guild_config(guild_id, default)
        return self.config_cache[gid_str]

    # -------------------- Event listeners --------------------

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Send welcome message when a member joins."""
        guild_config = self._get_guild_config(member.guild.id)
        if not guild_config["welcome_enabled"] or not guild_config["welcome_channel_id"]:
            return

        channel = self.bot.get_channel(guild_config["welcome_channel_id"])
        if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return

        try:
            msg = guild_config["welcome_message"].format(
                member=member,
                guild=member.guild,
                mention=member.mention,
                name=member.name,
                display_name=member.display_name
            )
            embed = discord.Embed(
                title="👋 Welcome!",
                description=msg,
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Member #{len(member.guild.members)}")
            await channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Error sending welcome: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Send goodbye message when a member leaves."""
        guild_config = self._get_guild_config(member.guild.id)
        if not guild_config["goodbye_enabled"] or not guild_config["goodbye_channel_id"]:
            return

        channel = self.bot.get_channel(guild_config["goodbye_channel_id"])
        if not channel or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return

        try:
            msg = guild_config["goodbye_message"].format(
                member=member,
                guild=member.guild,
                mention=member.mention,
                name=member.name,
                display_name=member.display_name
            )
            embed = discord.Embed(
                title="👋 Goodbye",
                description=msg,
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Error sending goodbye: {e}")

    # -------------------- Slash commands --------------------

    @app_commands.command(name="set_welcome_channel", description="Set the channel for welcome messages.")
    @app_commands.describe(channel="The text channel to send welcome messages in.")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the welcome channel for this server."""
        guild_config = self._get_guild_config(interaction.guild_id)
        guild_config["welcome_channel_id"] = channel.id
        self._save_guild_config(interaction.guild_id, guild_config)

        embed = discord.Embed(
            title="✅ Welcome Channel Set",
            description=f"Welcome messages will now be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_goodbye_channel", description="Set the channel for goodbye messages.")
    @app_commands.describe(channel="The text channel to send goodbye messages in.")
    @app_commands.default_permissions(administrator=True)
    async def set_goodbye_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the goodbye channel for this server."""
        guild_config = self._get_guild_config(interaction.guild_id)
        guild_config["goodbye_channel_id"] = channel.id
        self._save_guild_config(interaction.guild_id, guild_config)

        embed = discord.Embed(
            title="✅ Goodbye Channel Set",
            description=f"Goodbye messages will now be sent to {channel.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_welcome_message", description="Set the custom welcome message.")
    @app_commands.describe(message="The welcome message (use {member.mention}, {guild.name}, etc.)")
    @app_commands.default_permissions(administrator=True)
    async def set_welcome_message(self, interaction: discord.Interaction, *, message: str):
        """Set the welcome message with placeholders."""
        guild_config = self._get_guild_config(interaction.guild_id)
        guild_config["welcome_message"] = message
        self._save_guild_config(interaction.guild_id, guild_config)

        preview = message.format(
            member=interaction.user,
            guild=interaction.guild,
            mention=interaction.user.mention,
            name=interaction.user.name,
            display_name=interaction.user.display_name
        )
        embed = discord.Embed(
            title="✅ Welcome Message Updated",
            description=f"Preview:\n{preview}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_goodbye_message", description="Set the custom goodbye message.")
    @app_commands.describe(message="The goodbye message (use {member.mention}, {guild.name}, etc.)")
    @app_commands.default_permissions(administrator=True)
    async def set_goodbye_message(self, interaction: discord.Interaction, *, message: str):
        """Set the goodbye message with placeholders."""
        guild_config = self._get_guild_config(interaction.guild_id)
        guild_config["goodbye_message"] = message
        self._save_guild_config(interaction.guild_id, guild_config)

        preview = message.format(
            member=interaction.user,
            guild=interaction.guild,
            mention=interaction.user.mention,
            name=interaction.user.name,
            display_name=interaction.user.display_name
        )
        embed = discord.Embed(
            title="✅ Goodbye Message Updated",
            description=f"Preview:\n{preview}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="toggle_welcome", description="Enable or disable welcome messages.")
    @app_commands.default_permissions(administrator=True)
    async def toggle_welcome(self, interaction: discord.Interaction):
        """Toggle welcome messages on/off."""
        guild_config = self._get_guild_config(interaction.guild_id)
        guild_config["welcome_enabled"] = not guild_config["welcome_enabled"]
        self._save_guild_config(interaction.guild_id, guild_config)

        status = "enabled" if guild_config["welcome_enabled"] else "disabled"
        embed = discord.Embed(
            title="✅ Welcome Toggled",
            description=f"Welcome messages are now **{status}**.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="toggle_goodbye", description="Enable or disable goodbye messages.")
    @app_commands.default_permissions(administrator=True)
    async def toggle_goodbye(self, interaction: discord.Interaction):
        """Toggle goodbye messages on/off."""
        guild_config = self._get_guild_config(interaction.guild_id)
        guild_config["goodbye_enabled"] = not guild_config["goodbye_enabled"]
        self._save_guild_config(interaction.guild_id, guild_config)

        status = "enabled" if guild_config["goodbye_enabled"] else "disabled"
        embed = discord.Embed(
            title="✅ Goodbye Toggled",
            description=f"Goodbye messages are now **{status}**.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="welcome_settings", description="Show the current welcome/goodbye settings for this server.")
    @app_commands.default_permissions(administrator=True)
    async def welcome_settings(self, interaction: discord.Interaction):
        """Display all settings."""
        guild_config = self._get_guild_config(interaction.guild_id)

        welcome_ch = interaction.guild.get_channel(guild_config["welcome_channel_id"])
        goodbye_ch = interaction.guild.get_channel(guild_config["goodbye_channel_id"])

        embed = discord.Embed(
            title="🎉 Welcome System Settings",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="📥 Welcome Channel",
            value=welcome_ch.mention if welcome_ch else "Not set",
            inline=False
        )
        embed.add_field(
            name="📤 Goodbye Channel",
            value=goodbye_ch.mention if goodbye_ch else "Not set",
            inline=False
        )
        embed.add_field(
            name="👋 Welcome Messages",
            value="✅ Enabled" if guild_config["welcome_enabled"] else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="👋 Goodbye Messages",
            value="✅ Enabled" if guild_config["goodbye_enabled"] else "❌ Disabled",
            inline=True
        )
        embed.add_field(
            name="📨 Welcome Message",
            value=f"```{guild_config['welcome_message']}```",
            inline=False
        )
        embed.add_field(
            name="📤 Goodbye Message",
            value=f"```{guild_config['goodbye_message']}```",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="test_welcome", description="Send a test welcome message as if you just joined.")
    @app_commands.default_permissions(administrator=True)
    async def test_welcome(self, interaction: discord.Interaction):
        """Test the welcome message by simulating a join."""
        guild_config = self._get_guild_config(interaction.guild_id)
        if not guild_config["welcome_channel_id"]:
            await interaction.response.send_message("❌ Welcome channel not set. Use `/set_welcome_channel` first.", ephemeral=True)
            return

        # Use the command user as the simulated member
        member = interaction.guild.get_member(interaction.user.id) or interaction.user
        if isinstance(member, discord.Member):
            await self.on_member_join(member)
        await interaction.response.send_message("✅ Test welcome message sent!", ephemeral=True)

    @app_commands.command(name="test_goodbye", description="Send a test goodbye message as if you just left.")
    @app_commands.default_permissions(administrator=True)
    async def test_goodbye(self, interaction: discord.Interaction):
        """Test the goodbye message by simulating a leave."""
        guild_config = self._get_guild_config(interaction.guild_id)
        if not guild_config["goodbye_channel_id"]:
            await interaction.response.send_message("❌ Goodbye channel not set. Use `/set_goodbye_channel` first.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id) or interaction.user
        if isinstance(member, discord.Member):
            await self.on_member_remove(member)
        await interaction.response.send_message("✅ Test goodbye message sent!", ephemeral=True)


# -------------------- Setup function for the cog --------------------

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))