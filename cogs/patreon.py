import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional
from cryptography.fernet import Fernet
from discord import app_commands
from discord.app_commands import Group
from discord.ext import commands


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "AetherX.db")


def _ensure_key() -> bytes:
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    key_path = os.path.join(root_dir, ".patreon.key")
    key = os.environ.get("AETHERX_PATREON_KEY")

    if key:
        return key.encode("utf-8") if len(key) == 44 and key.endswith("=") else key.encode("utf-8")

    if os.path.exists(key_path):
        with open(key_path, "rb") as handle:
            stored_key = handle.read().strip()
        if stored_key:
            return stored_key

    generated_key = Fernet.generate_key()
    with open(key_path, "wb") as handle:
        handle.write(generated_key)
    return generated_key


class PatreonSync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.fernet = Fernet(_ensure_key())
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS patreon_sync (
                    guild_id TEXT PRIMARY KEY,
                    guild_name TEXT,
                    patreon_page_url TEXT,
                    patreon_page_name TEXT,
                    patreon_user_id TEXT,
                    access_token TEXT,
                    refresh_token TEXT,
                    enabled INTEGER DEFAULT 1,
                    linked_at TEXT,
                    last_sync_at TEXT,
                    is_verified INTEGER DEFAULT 0
                )
                """
            )
            conn.commit()

    def _encode_secret(self, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        return self.fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def _decode_secret(self, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        try:
            return self.fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception:
            return None

    def _get_record(self, guild_id: int):
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM patreon_sync WHERE guild_id = ?",
                (str(guild_id),),
            ).fetchone()
        return row

    async def _owner_only(self, interaction) -> bool:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return False

        if interaction.user.id != guild.owner_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only the server owner (or an administrator) may configure Patreon sync.", ephemeral=True)
            return False

        return True

    patreon = app_commands.Group(name="patreon", description="Control Patreon sync for your Discord server.")

    @patreon.command(name="link")
    @app_commands.describe(
        page_url="Your Patreon page URL, for example https://www.patreon.com/yourpage",
        page_name="Optional friendly name for your Patreon page",
        patreon_user_id="Optional Patreon user ID.",
        access_token="Optional Patreon access token (stored encrypted).",
        refresh_token="Optional Patreon refresh token (stored encrypted).",
    )
    async def patreon_link(
        self,
        interaction,
        page_url: str,
        page_name: str = "",
        patreon_user_id: str = "",
        access_token: str = "",
        refresh_token: str = "",
    ):
        if not await self._owner_only(interaction):
            return

        guild = interaction.guild
        guild_name = guild.name if guild else "Unknown"
        page_name = page_name.strip() or page_url.strip().rstrip("/").split("/")[-1]

        if not page_url.startswith(("http://", "https://")):
            await interaction.response.send_message("The Patreon page URL must begin with http:// or https://.", ephemeral=True)
            return

        now = datetime.now(timezone.utc).isoformat()
        encrypted_access = self._encode_secret(access_token)
        encrypted_refresh = self._encode_secret(refresh_token)

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO patreon_sync (
                    guild_id,
                    guild_name,
                    patreon_page_url,
                    patreon_page_name,
                    patreon_user_id,
                    access_token,
                    refresh_token,
                    enabled,
                    linked_at,
                    last_sync_at,
                    is_verified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, NULL, 1)
                ON CONFLICT(guild_id) DO UPDATE SET
                    guild_name = excluded.guild_name,
                    patreon_page_url = excluded.patreon_page_url,
                    patreon_page_name = excluded.patreon_page_name,
                    patreon_user_id = excluded.patreon_user_id,
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    enabled = 1,
                    linked_at = excluded.linked_at,
                    is_verified = 1
                """,
                (
                    str(guild.id),
                    guild_name,
                    page_url.strip(),
                    page_name.strip(),
                    patreon_user_id.strip(),
                    encrypted_access,
                    encrypted_refresh,
                    now,
                ),
            )
            conn.commit()

        await interaction.response.send_message(
            f"Patreon sync is now configured for {guild_name}.\n"
            f"Page: {page_url}\n"
            "The connection is enabled and stored securely in AetherX.db.",
            ephemeral=True,
        )

    @patreon.command(name="status")
    async def patreon_status(self, interaction):
        if not await self._owner_only(interaction):
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        row = self._get_record(guild.id)
        if row is None:
            await interaction.response.send_message("No Patreon page is linked for this server yet.", ephemeral=True)
            return

        enabled = bool(row["enabled"])
        verified = bool(row["is_verified"])
        page_url = row["patreon_page_url"] or "Not set"
        page_name = row["patreon_page_name"] or "Unnamed"
        linked_at = row["linked_at"] or "Unknown"

        response = (
            f"Patreon sync status for {guild.name}:\n"
            f"Enabled: {enabled}\n"
            f"Verified: {verified}\n"
            f"Page: {page_name}\n"
            f"URL: {page_url}\n"
            f"Linked at: {linked_at}"
        )
        await interaction.response.send_message(response, ephemeral=True)

    @patreon.command(name="disable")
    async def patreon_disable(self, interaction):
        if not await self._owner_only(interaction):
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE patreon_sync SET enabled = 0 WHERE guild_id = ?",
                (str(guild.id),),
            )
            conn.commit()

        await interaction.response.send_message("Patreon sync has been disabled for this server.", ephemeral=True)

    @patreon.command(name="enable")
    async def patreon_enable(self, interaction):
        if not await self._owner_only(interaction):
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "UPDATE patreon_sync SET enabled = 1 WHERE guild_id = ?",
                (str(guild.id),),
            )
            conn.commit()

        await interaction.response.send_message("Patreon sync has been enabled for this server.", ephemeral=True)

    @patreon.command(name="unlink")
    async def patreon_unlink(self, interaction):
        if not await self._owner_only(interaction):
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM patreon_sync WHERE guild_id = ?", (str(guild.id),))
            conn.commit()

        await interaction.response.send_message("Patreon sync has been disconnected from this server.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(PatreonSync(bot))
