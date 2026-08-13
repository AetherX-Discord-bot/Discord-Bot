import sqlite3
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands


DB_PATH = "AetherX.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ticket_settings (
                guild_id INTEGER PRIMARY KEY,
                setup_channel_id INTEGER,
                category_id INTEGER,
                admin_channel_id INTEGER,
                staff_role_id INTEGER,
                embed_title TEXT,
                embed_description TEXT,
                button_label TEXT,
                embed_color INTEGER DEFAULT 5814783
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                channel_id INTEGER,
                category_id INTEGER,
                reason TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT,
                closed_at TEXT,
                closed_by INTEGER,
                transcript_path TEXT
            )
            """
        )
        conn.commit()


def get_setting(guild_id: int, key: str):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM ticket_settings WHERE guild_id = ?",
            (guild_id,),
        ).fetchone()
    if not row:
        return None
    return row[key]


def save_setting(guild_id: int, setup_channel_id: int, category_id: int, admin_channel_id: int, embed_title: str, embed_description: str, button_label: str, embed_color: int):
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO ticket_settings (
                guild_id, setup_channel_id, category_id, admin_channel_id,
                embed_title, embed_description, button_label, embed_color
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                setup_channel_id=excluded.setup_channel_id,
                category_id=excluded.category_id,
                admin_channel_id=excluded.admin_channel_id,
                embed_title=excluded.embed_title,
                embed_description=excluded.embed_description,
                button_label=excluded.button_label,
                embed_color=excluded.embed_color
            """,
            (guild_id, setup_channel_id, category_id, admin_channel_id, embed_title, embed_description, button_label, embed_color),
        )
        conn.commit()


def get_ticket_by_channel(channel_id: int):
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT * FROM tickets WHERE channel_id = ? ORDER BY id DESC LIMIT 1",
            (channel_id,),
        ).fetchone()


def update_ticket_status(channel_id: int, status: str, closed_by: Optional[int] = None):
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE tickets SET status = ?, closed_by = ?, closed_at = ? WHERE channel_id = ?",
            (status, closed_by, datetime.utcnow().isoformat(), channel_id),
        )
        conn.commit()


def create_ticket_record(guild_id: int, user_id: int, channel_id: int, category_id: Optional[int], reason: str):
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO tickets (guild_id, user_id, channel_id, category_id, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'open', ?)
            """,
            (guild_id, user_id, channel_id, category_id, reason, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_transcript_text(channel: discord.TextChannel) -> str:
    messages = []
    async def gather():
        async for message in channel.history(oldest_first=True, limit=None):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = message.author.display_name
            content = message.content or "[No text content]"
            messages.append(f"[{timestamp}] {author}: {content}")
    import asyncio
    asyncio.get_event_loop().run_until_complete(gather())
    return "\n".join(messages) if messages else "No messages in this ticket channel."


class TicketReasonModal(discord.ui.Modal, title="Open a Ticket"):
    def __init__(self, guild: discord.Guild, author: discord.User | discord.Member):
        super().__init__(timeout=None)
        self.guild = guild
        self.author = author
        self.reason = discord.ui.TextInput(
            label="Ticket Reason",
            placeholder="Describe the issue or request",
            min_length=3,
            max_length=500,
            required=True,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("Only the ticket creator can submit this form.", ephemeral=True)
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        row = self.get_settings(guild.id)
        if not row:
            await interaction.response.send_message("Ticket setup has not been configured for this server yet.", ephemeral=True)
            return

        category_channel = guild.get_channel(row["category_id"]) if row["category_id"] else None
        category = category_channel if isinstance(category_channel, discord.CategoryChannel) else None
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False, connect=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
        }

        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_channels or role.permissions.manage_guild:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, manage_channels=True)

        channel_name = f"ticket-{interaction.user.name.lower()}"
        if len(channel_name) > 90:
            channel_name = f"ticket-{interaction.user.name.lower()[:80]}"

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket created by {interaction.user} for: {self.reason.value}",
        )

        embed = discord.Embed(
            title="Ticket Opened",
            description=f"{interaction.user.mention} opened a ticket.\n\nReason: {self.reason.value}",
            color=discord.Color.green(),
        )
        embed.add_field(name="Status", value="Open", inline=False)
        embed.set_footer(text="Use the button below to close this ticket when you are done.")

        await ticket_channel.send(f"{interaction.user.mention}", embed=embed, view=TicketOwnerView())
        create_ticket_record(guild.id, interaction.user.id, ticket_channel.id, category.id if category else None, self.reason.value)

        await interaction.response.send_message(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

        admin_channel = guild.get_channel(row["admin_channel_id"]) if row["admin_channel_id"] else None
        if admin_channel and isinstance(admin_channel, discord.TextChannel):
            admin_embed = discord.Embed(
                title="New Ticket Created",
                description=f"A new ticket was opened by {interaction.user.mention}.",
                color=discord.Color.blurple(),
            )
            admin_embed.add_field(name="Reason", value=self.reason.value, inline=False)
            admin_embed.add_field(name="Channel", value=ticket_channel.mention, inline=False)
            await admin_channel.send(embed=admin_embed, view=AdminTicketActions(ticket_channel.id))

    def get_settings(self, guild_id: int):
        with get_db_connection() as conn:
            return conn.execute(
                "SELECT * FROM ticket_settings WHERE guild_id = ?",
                (guild_id,),
            ).fetchone()


class TicketOpenButton(discord.ui.Button):
    def __init__(self, label: str):
        super().__init__(label=label, style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user is None:
            await interaction.response.send_message("You must be a member of this server to open a ticket.", ephemeral=True)
            return
        if interaction.guild is None:
            await interaction.response.send_message("This button can only be used in a server.", ephemeral=True)
            return
        await interaction.response.send_modal(TicketReasonModal(interaction.guild, interaction.user))


class TicketOwnerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton())


class CloseTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close Ticket", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("This button can only be used in a ticket channel.", ephemeral=True)
            return

        member = interaction.user
        if member is None or interaction.guild is None:
            await interaction.response.send_message("Could not determine user context.", ephemeral=True)
            return

        guild_member = interaction.guild.get_member(member.id)
        if guild_member is None:
            await interaction.response.send_message("Could not retrieve member information.", ephemeral=True)
            return

        ticket = get_ticket_by_channel(channel.id)
        if not ticket:
            await interaction.response.send_message("No ticket record was found for this channel.", ephemeral=True)
            return

        if member.id != ticket["user_id"] and not guild_member.guild_permissions.manage_channels:
            await interaction.response.send_message("Only the ticket creator or a moderator can close this ticket.", ephemeral=True)
            return

        try:
            await channel.edit(name=f"closed-{channel.name}")
        except discord.Forbidden:
            pass

        try:
            await channel.set_permissions(guild_member, view_channel=False, send_messages=False, read_message_history=False)
        except discord.Forbidden:
            pass

        update_ticket_status(channel.id, "closed", member.id)

        try:
            await channel.send(
                embed=discord.Embed(
                    title="Ticket Closed",
                    description=f"This ticket has been closed by {member.mention}. The ticket channel has been renamed and the ticket creator was removed from access.",
                    color=discord.Color.orange(),
                )
            )
        except discord.Forbidden:
            pass

        row = get_settings_for_guild(interaction.guild.id)
        if row and row["admin_channel_id"]:
            admin_channel = interaction.guild.get_channel(row["admin_channel_id"])
            if isinstance(admin_channel, discord.TextChannel):
                admin_embed = discord.Embed(
                    title="Ticket Closed",
                    description=f"Ticket channel {channel.mention} has been closed.",
                    color=discord.Color.orange(),
                )
                admin_embed.add_field(name="Reason", value=ticket["reason"], inline=False)
                admin_embed.add_field(name="Closed By", value=member.mention, inline=False)
                await admin_channel.send(embed=admin_embed, view=AdminTicketActions(channel.id))

        await interaction.response.send_message("Ticket closed successfully.", ephemeral=True)


class AdminTicketActions(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id

    @discord.ui.button(label="Get Transcript", style=discord.ButtonStyle.secondary)
    async def transcript_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member or (not member.guild_permissions.manage_channels and not member.guild_permissions.administrator):
            await interaction.response.send_message("You do not have permission to access the transcript.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("This ticket channel could not be found.", ephemeral=True)
            return

        transcript = get_transcript_text(channel)
        file = discord.File(fp=__import__('io').BytesIO(transcript.encode("utf-8")), filename=f"ticket-{channel.id}-transcript.txt")
        await interaction.response.send_message(file=file, ephemeral=True)

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member or (not member.guild_permissions.manage_channels and not member.guild_permissions.administrator):
            await interaction.response.send_message("You do not have permission to delete tickets.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Are you sure you want to delete this ticket channel?",
            view=DeleteTicketConfirm(self.channel_id),
            ephemeral=True,
        )


class DeleteTicketConfirm(discord.ui.View):
    def __init__(self, channel_id: int):
        super().__init__(timeout=60)
        self.channel_id = channel_id

    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a guild.", ephemeral=True)
            return

        member = interaction.guild.get_member(interaction.user.id)
        if not member or (not member.guild_permissions.manage_channels and not member.guild_permissions.administrator):
            await interaction.response.send_message("Only staff can delete this ticket.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(self.channel_id)
        if channel is None:
            await interaction.response.send_message("This ticket channel was already deleted.", ephemeral=True)
            return

        try:
            await channel.delete(reason=f"Ticket deleted by {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to delete this ticket channel.", ephemeral=True)
            return

        update_ticket_status(self.channel_id, "deleted", interaction.user.id)
        await interaction.response.send_message("Ticket channel deleted.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket deletion cancelled.", ephemeral=True)


def get_settings_for_guild(guild_id: int):
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT * FROM ticket_settings WHERE guild_id = ?",
            (guild_id,),
        ).fetchone()


class TicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    @app_commands.command(name="setup_tickets", description="Set up the ticket embed and buttons for your server.")
    @app_commands.describe(
        channel="Channel to send the ticket embed in",
        category="Category where temporary ticket channels are created",
        admin_channel="Channel where admin ticket actions are sent",
        title="Ticket embed title",
        description="Ticket embed description",
        button_label="Label for the ticket button",
    )
    async def setup_tickets(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        category: discord.CategoryChannel,
        admin_channel: discord.TextChannel,
        title: str,
        description: str,
        button_label: str = "Open Ticket",
    ):
        if not interaction.guild or not interaction.permissions.manage_channels:
            await interaction.response.send_message("You need Manage Channels to configure tickets.", ephemeral=True)
            return

        save_setting(
            interaction.guild.id,
            channel.id,
            category.id,
            admin_channel.id,
            title,
            description,
            button_label,
            5814783,
        )

        embed = discord.Embed(title=title, description=description, color=discord.Color(5814783))
        view = discord.ui.View(timeout=None)
        view.add_item(TicketOpenButton(button_label))

        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"Ticket setup complete in {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCog(bot))
