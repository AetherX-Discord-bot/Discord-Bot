import sqlite3

import discord
from discord import app_commands
from discord.ext import commands


class HoneypotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "AetherX.db"
        self.honeypot_map = {}
        self.honeypot_enabled = {}
        self.dm_on_ban = {}
        self._init_db()
        self.load_config()

    def _init_db(self):
        """Create the honeypot database table if it doesn't already exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS honeypot_config (
                        guild_id INTEGER PRIMARY KEY,
                        channel_id INTEGER NOT NULL,
                        enabled INTEGER NOT NULL DEFAULT 1,
                        dm_on_ban INTEGER NOT NULL DEFAULT 1
                    )
                    """
                )
        except sqlite3.Error as exc:
            print(f"[Honeypot] ERROR: Unable to initialize sqlite DB: {exc}")

    def load_config(self):
        """Load or reload the honeypot channel map from the database."""
        self.honeypot_map = {}
        self.honeypot_enabled = {}
        self.dm_on_ban = {}

        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT guild_id, channel_id, enabled, dm_on_ban FROM honeypot_config"
                ).fetchall()

            for guild_id, channel_id, enabled, dm_on_ban in rows:
                guild_id = int(guild_id)
                channel_id = int(channel_id)
                self.honeypot_enabled[guild_id] = bool(enabled)
                self.dm_on_ban[guild_id] = bool(dm_on_ban)

                if enabled:
                    self.honeypot_map[guild_id] = channel_id

            print(f"[Honeypot] Loaded config for {len(self.honeypot_map)} enabled guild(s).")
        except sqlite3.Error as exc:
            print(f"[Honeypot] ERROR: Unable to load honeypot config from database: {exc}")

    def upsert_honeypot_config(self, guild_id, channel_id, enabled=True, dm_on_ban=True):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO honeypot_config (guild_id, channel_id, enabled, dm_on_ban)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    enabled = excluded.enabled,
                    dm_on_ban = excluded.dm_on_ban
                """,
                (int(guild_id), int(channel_id), int(enabled), int(dm_on_ban))
            )
        self.load_config()

    def update_honeypot_state(self, guild_id, enabled):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE honeypot_config SET enabled = ? WHERE guild_id = ?",
                (int(enabled), int(guild_id))
            )
        self.load_config()

    def remove_honeypot_config(self, guild_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM honeypot_config WHERE guild_id = ?", (int(guild_id),))
        self.load_config()

    async def _send_honeypot_announce(self, channel):
        embed = discord.Embed(
            title="🚨 Honeypot Channel Active",
            description="This is a **decoy channel** designed to remove annoying bots.",
            color=discord.Color.red(),
        )
        embed.add_field(
            name="❓ What happens if I send a message here?",
            value=(
                "• You will be immediately **soft‑banned**.\n"
                "• You will be kicked from the server.\n"
                "• All your messages will be permanently purged."
            ),
            inline=False,
        )
        embed.add_field(
            name="⚙️ Why does this channel exist?",
            value=(
                "To protect this community from spam, raid bots, and malicious automation. "
                "**Legitimate users should never need to type in this channel.**"
            ),
            inline=False,
        )
        embed.set_footer(text="If you're a human, please ignore this channel completely.")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        if guild_id not in self.honeypot_map:
            return

        honeypot_channel_id = self.honeypot_map[guild_id]
        if message.channel.id != honeypot_channel_id:
            return

        if message.author.id == self.bot.owner_id:
            try:
                await message.author.send("🔒 You're the bot owner – you're exempt from the honeypot.")
            except Exception:
                pass
            return

        if self.dm_on_ban.get(guild_id, False):
            try:
                await message.author.send(
                    "🚫 You triggered the honeypot channel in **{0}** and have been soft-banned. "
                    "Please contact staff if you believe this was a mistake.".format(message.guild.name)
                )
            except Exception:
                pass

        try:
            await message.guild.ban(
                message.author,
                reason="Honeypot triggered – automated/unauthorised message.",
                delete_message_days=1,
            )
            await message.guild.unban(message.author)
            print(f"[Honeypot] Soft-banned {message.author} in {message.guild.name}.")
        except discord.Forbidden:
            print(f"[Honeypot] ERROR: Missing permissions to ban in {message.guild.name}.")
        except discord.HTTPException as exc:
            print(f"[Honeypot] Unexpected error while banning: {exc}")

    @app_commands.command(name="setup_honeypot", description="Configure a honeypot channel for this server.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.describe(channel="The channel to set as the honeypot.", dm_user="DM the user who triggers the honeypot.")
    async def setup_honeypot(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        dm_user: bool = True,
    ):
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return
        guild_id = interaction.guild.id
        self.upsert_honeypot_config(guild_id, channel.id, enabled=True, dm_on_ban=dm_user)
        await self._send_honeypot_announce(channel)
        await interaction.response.send_message(
            f"✅ {channel.mention} is now configured as the honeypot channel for this server.",
            ephemeral=True,
        )

    @app_commands.command(name="honeypot_enable", description="Enable the configured honeypot for this server.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def honeypot_enable(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return
        guild_id: int = interaction.guild.id
        if guild_id not in self.honeypot_enabled and guild_id not in self.honeypot_map:
            await interaction.response.send_message("❌ No honeypot is configured for this server.", ephemeral=True)
            return

        self.update_honeypot_state(guild_id, True)
        await interaction.response.send_message("✅ Honeypot enabled for this server.", ephemeral=True)

    @app_commands.command(name="honeypot_disable", description="Disable the honeypot without removing its configuration.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def honeypot_disable(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return
        guild_id = interaction.guild.id
        if guild_id not in self.honeypot_enabled and guild_id not in self.honeypot_map:
            await interaction.response.send_message("❌ No honeypot is configured for this server.", ephemeral=True)
            return

        self.update_honeypot_state(guild_id, False)
        await interaction.response.send_message("✅ Honeypot disabled for this server.", ephemeral=True)

    @app_commands.command(name="honeypot_remove", description="Remove the honeypot configuration for this server.")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def honeypot_remove(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)
            return
        guild_id = interaction.guild.id
        if guild_id not in self.honeypot_enabled and guild_id not in self.honeypot_map:
            await interaction.response.send_message("❌ No honeypot is configured for this server.", ephemeral=True)
            return

        self.remove_honeypot_config(guild_id)
        await interaction.response.send_message("✅ Honeypot configuration removed for this server.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(HoneypotCog(bot))