import discord
from discord import app_commands
from discord.ext import commands
import aiosqlite

DB_PATH = "AetherX.db"


class StickyMessages(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stickies: dict[int, dict] = {}

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sticky_messages (
                    channel_id INTEGER PRIMARY KEY,
                    message_id INTEGER,
                    content    TEXT NOT NULL
                )
            """)
            await db.commit()

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT channel_id, message_id, content FROM sticky_messages"
            ) as cursor:
                async for channel_id, message_id, content in cursor:
                    self.stickies[channel_id] = {
                        "message_id": message_id,
                        "content": content,
                    }

    async def _save_sticky(self, channel_id: int, message_id: int, content: str):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO sticky_messages (channel_id, message_id, content)
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    message_id = excluded.message_id,
                    content    = excluded.content
                """,
                (channel_id, message_id, content),
            )
            await db.commit()

    async def _update_message_id(self, channel_id: int, message_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE sticky_messages SET message_id = ? WHERE channel_id = ?",
                (message_id, channel_id),
            )
            await db.commit()

    async def _delete_sticky(self, channel_id: int):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM sticky_messages WHERE channel_id = ?", (channel_id,)
            )
            await db.commit()

    @app_commands.command(
        name="sticky", description="Set a sticky message for this channel."
    )
    @app_commands.describe(message="The message to keep sticky in this channel.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def sticky(
        self,
        interaction: discord.Interaction,
        message: str,
    ):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        assert isinstance(channel, discord.TextChannel)

        old = self.stickies.get(channel.id)
        if old and old.get("message_id"):
            try:
                old_msg = await channel.fetch_message(old["message_id"])
                await old_msg.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        sent = await channel.send(message)

        self.stickies[channel.id] = {
            "message_id": sent.id,
            "content": message,
        }
        await self._save_sticky(channel.id, sent.id, message)

        await interaction.followup.send(
            f"✅ Sticky message set in {channel.mention}.", ephemeral=True
        )

    @app_commands.command(
        name="unsticky", description="Remove the sticky message from this channel."
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def unsticky(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.followup.send(
                "❌ This command can only be used in a channel.", ephemeral=True
            )
            return

        channel_id = channel.id

        data = self.stickies.pop(channel_id, None)

        if not data:
            await interaction.followup.send(
                "❌ There is no sticky message in this channel.", ephemeral=True
            )
            return

        try:
            msg = await channel.fetch_message(data["message_id"])
            await msg.delete()
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass

        await self._delete_sticky(channel_id)
        await interaction.followup.send("✅ Sticky message removed.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        if message.author.bot:
            return

        data = self.stickies.get(message.channel.id)
        if not data:
            return

        channel = message.channel

        if data.get("message_id"):
            try:
                old_msg = await channel.fetch_message(data["message_id"])
                await old_msg.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        try:
            new_msg = await channel.send(data["content"])
        except discord.HTTPException:
            return

        data["message_id"] = new_msg.id
        await self._update_message_id(channel.id, new_msg.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(StickyMessages(bot))