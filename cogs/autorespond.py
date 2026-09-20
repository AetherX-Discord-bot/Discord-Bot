import aiosqlite
import discord
from discord.ext import commands
from discord import app_commands


class AutoResponder(commands.Cog):
    """Automatically respond to messages containing saved trigger phrases."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "AetherX.db"
        self.cache: dict[int, dict[str, str]] = {}

    async def cog_load(self):
        """Create the table and load existing triggers into cache."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS autoresponses (
                    guild_id INTEGER NOT NULL,
                    trigger TEXT NOT NULL,
                    response TEXT NOT NULL,
                    PRIMARY KEY (guild_id, trigger)
                )
                """
            )
            await db.commit()

        # Populate cache
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT guild_id, trigger, response FROM autoresponses") as cursor:
                async for guild_id, trigger, response in cursor:
                    self.cache.setdefault(guild_id, {})[trigger.lower()] = response

    # ---------- Commands ----------

    @app_commands.command(name="setup", description="Add or update an auto-response.")
    @app_commands.describe(
        trigger="The phrase to look for in messages",
        response="What the bot should reply with"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction, trigger: str, response: str):
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        trigger_key = trigger.lower().strip()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO autoresponses (guild_id, trigger, response)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, trigger) DO UPDATE SET response = excluded.response
                """,
                (interaction.guild_id, trigger_key, response),
            )
            await db.commit()

        self.cache.setdefault(interaction.guild_id, {})[trigger_key] = response

        await interaction.response.send_message(
            f"✅ Auto-response saved.\n**Trigger:** `{trigger_key}`\n**Response:** {response}",
            ephemeral=True,
        )

    @app_commands.command(name="removeauto", description="Remove an auto-response.")
    @app_commands.describe(trigger="The trigger phrase to remove")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def removeauto(self, interaction: discord.Interaction, trigger: str):
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        trigger_key = trigger.lower().strip()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM autoresponses WHERE guild_id = ? AND trigger = ?",
                (interaction.guild_id, trigger_key),
            )
            await db.commit()
            deleted = cursor.rowcount

        if deleted:
            self.cache.get(interaction.guild_id, {}).pop(trigger_key, None)
            await interaction.response.send_message(
                f"🗑️ Removed auto-response for `{trigger_key}`.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ No auto-response found for `{trigger_key}`.", ephemeral=True
            )

    @app_commands.command(name="listauto", description="List all auto-responses in this server.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def listauto(self, interaction: discord.Interaction):
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        guild_triggers = self.cache.get(interaction.guild_id, {})

        if not guild_triggers:
            await interaction.response.send_message(
                "No auto-responses configured yet.", ephemeral=True
            )
            return

        embed = discord.Embed(title="Auto-Responses", color=discord.Color.blurple())
        for trigger, response in sorted(guild_triggers.items()):
            embed.add_field(
                name=f"🔹 {trigger}",
                value=response[:1000],
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---------- Listener ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_triggers = self.cache.get(message.guild.id)
        if not guild_triggers:
            return

        content_lower = message.content.lower()
        for trigger, response in guild_triggers.items():
            if trigger in content_lower:
                try:
                    await message.reply(response, mention_author=False)
                except discord.HTTPException:
                    pass
                return  # one reply per message; remove `return` to allow multiple

    # ---------- Error handling ----------

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You need the **Manage Server** permission to use this command.",
                ephemeral=True,
            )
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoResponder(bot))