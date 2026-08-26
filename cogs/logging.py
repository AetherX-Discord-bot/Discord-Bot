import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import json
from typing import Optional, Dict, Any

PRESETS = {
    "minimal": {
        "event_member_join": 1,
        "event_member_leave": 1,
        "event_message_delete": 1,
    },
    "moderation": {
        "event_member_ban": 1,
        "event_member_unban": 1,
        "event_member_kick": 1,
        "event_member_mute": 1,
        "event_member_unmute": 1,
    },
    "messages": {
        "event_message_delete": 1,
        "event_message_edit": 1,
    },
    "members": {
        "event_member_join": 1,
        "event_member_leave": 1,
        "event_member_ban": 1,
        "event_member_unban": 1,
        "event_member_kick": 1,
    },
    "all": {}
}

EVENT_COLUMNS = [
    "event_message_delete",
    "event_message_edit",
    "event_member_join",
    "event_member_leave",
    "event_member_ban",
    "event_member_unban",
    "event_member_kick",
    "event_member_mute",
    "event_member_unmute",
    "event_channel_create",
    "event_channel_delete",
    "event_channel_update",
    "event_role_create",
    "event_role_delete",
    "event_role_update",
    "event_voice_join",
    "event_voice_leave",
    "event_voice_move",
]
PRESETS["all"] = {col: 1 for col in EVENT_COLUMNS}

DB_PATH = "AetherX.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    col_defs = [
        "guild_id INTEGER PRIMARY KEY",
        "log_channel_id INTEGER",
        "preset TEXT",
        "event_channel_overrides TEXT",
    ]
    for col in EVENT_COLUMNS:
        col_defs.append(f"{col} INTEGER DEFAULT 0")
    create_query = f"CREATE TABLE IF NOT EXISTS guild_log_config ({', '.join(col_defs)})"
    c.execute(create_query)
    conn.commit()
    conn.close()

def get_config(guild_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM guild_log_config WHERE guild_id = ?", (guild_id,))
    row = c.fetchone()
    conn.close()
    if row:
        columns = [description[0] for description in c.description]
        return dict(zip(columns, row))
    return None

def init_guild(guild_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO guild_log_config (guild_id) VALUES (?)", (guild_id,))
    conn.commit()
    conn.close()

def apply_preset(guild_id: int, preset_name: str, channel_id: Optional[int] = None) -> bool:
    preset = PRESETS.get(preset_name)
    if not preset:
        return False
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    set_parts = [f"{col} = ?" for col in preset.keys()]
    values = list(preset.values())
    if channel_id is not None:
        set_parts.append("log_channel_id = ?")
        values.append(channel_id)
    set_parts.append("preset = ?")
    values.append(preset_name)
    query = f"UPDATE guild_log_config SET {', '.join(set_parts)} WHERE guild_id = ?"
    values.append(guild_id)
    c.execute(query, values)
    conn.commit()
    conn.close()
    return True

def toggle_event(guild_id: int, event_name: str, enabled: bool):
    if event_name not in EVENT_COLUMNS:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE guild_log_config SET {event_name} = ? WHERE guild_id = ?",
              (1 if enabled else 0, guild_id))
    conn.commit()
    conn.close()
    c = conn.cursor()
    c.execute("UPDATE guild_log_config SET preset = NULL WHERE guild_id = ?", (guild_id,))
    conn.commit()
    conn.close()

def set_event_channel_override(guild_id: int, event_name: str, channel_id: Optional[int]):
    config = get_config(guild_id)
    if not config:
        return
    overrides = json.loads(config.get("event_channel_overrides") or "{}")
    if channel_id is None:
        overrides.pop(event_name, None)
    else:
        overrides[event_name] = channel_id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE guild_log_config SET event_channel_overrides = ? WHERE guild_id = ?",
              (json.dumps(overrides), guild_id))
    conn.commit()
    conn.close()

def get_log_channel(guild: discord.Guild, config: Dict, event_name: str) -> Optional[discord.TextChannel]:
    overrides = json.loads(config.get("event_channel_overrides") or "{}")
    channel_id = overrides.get(event_name)
    if channel_id is None:
        channel_id = config.get("log_channel_id")
    if channel_id:
        return guild.get_channel(channel_id)
    return None

class PresetApplyView(discord.ui.View):
    """View shown after selecting a preset to allow channel selection."""
    def __init__(self, cog, guild_id: int, preset_name: str):
        super().__init__(timeout=120)
        self.cog = cog
        self.guild_id = guild_id
        self.preset_name = preset_name
        self.selected_channel = None

        self.channel_select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Select a log channel (optional)",
            min_values=0,
            max_values=1
        )
        self.add_item(self.channel_select)

        confirm = discord.ui.Button(label="Apply Preset", style=discord.ButtonStyle.success)
        async def confirm_callback(interaction: discord.Interaction):
            channel = self.channel_select.values[0] if self.channel_select.values else None
            channel_id = channel.id if channel else None
            success = apply_preset(self.guild_id, self.preset_name, channel_id)
            if success:
                msg = f"✅ Applied preset **{self.preset_name}**."
                if channel:
                    msg += f" Log channel set to {channel.mention}."
                else:
                    config = get_config(self.guild_id)
                    if config and config.get("log_channel_id"):
                        msg += " Keeping existing log channel."
                    else:
                        msg += " **No log channel set** – logs will not be sent until you set one."
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Invalid preset.", ephemeral=True)
            self.stop()
        confirm.callback = confirm_callback
        self.add_item(confirm)

        skip = discord.ui.Button(label="Skip (keep current)", style=discord.ButtonStyle.secondary)
        async def skip_callback(interaction: discord.Interaction):
            config = get_config(self.guild_id)
            current_channel = config.get("log_channel_id") if config else None
            success = apply_preset(self.guild_id, self.preset_name, current_channel)
            if success:
                msg = f"✅ Applied preset **{self.preset_name}**."
                if current_channel:
                    msg += f" Keeping existing log channel <#{current_channel}>."
                else:
                    msg += " **No log channel set** – logs will not be sent until you set one."
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Invalid preset.", ephemeral=True)
            self.stop()
        skip.callback = skip_callback
        self.add_item(skip)

class LogSetupView(discord.ui.View):
    def __init__(self, cog, guild_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.select(
        placeholder="Choose a preset or go custom...",
        options=[
            discord.SelectOption(label="Minimal", value="minimal",
                                 description="Join/leave & message delete"),
            discord.SelectOption(label="Moderation", value="moderation",
                                 description="Bans, kicks, mutes"),
            discord.SelectOption(label="Messages", value="messages",
                                 description="Edit/delete"),
            discord.SelectOption(label="Members", value="members",
                                 description="Join/leave & moderation"),
            discord.SelectOption(label="All Events", value="all",
                                 description="Everything"),
            discord.SelectOption(label="Custom Setup", value="custom",
                                 description="Fine‑tune each event individually"),
        ]
    )
    async def preset_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        if select.values[0] == "custom":
            await interaction.response.send_message("Opening custom setup...", ephemeral=True)
            config = get_config(self.guild_id)
            if not config:
                init_guild(self.guild_id)
                config = get_config(self.guild_id)
            view = EventToggleView(self.cog, self.guild_id, config)
            embed = discord.Embed(
                title="Custom Event Toggles",
                description="Select the events you want to enable in the dropdown below. "
                            "Use the channel dropdown to set a global channel, or use the button to set per‑event overrides.",
                color=discord.Color.gold()
            )
            channel_select = discord.ui.ChannelSelect(
                channel_types=[discord.ChannelType.text],
                placeholder="Set global log channel (optional)",
                min_values=0,
                max_values=1
            )
            async def channel_callback(interaction: discord.Interaction):
                if channel_select.values:
                    channel = channel_select.values[0]
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("UPDATE guild_log_config SET log_channel_id = ? WHERE guild_id = ?",
                              (channel.id, self.guild_id))
                    conn.commit()
                    conn.close()
                    await interaction.response.send_message(f"Global log channel set to {channel.mention}", ephemeral=True)
                else:
                    await interaction.response.send_message("No channel selected.", ephemeral=True)
            channel_select.callback = channel_callback
            view.add_item(channel_select)

            override_button = discord.ui.Button(label="Set per‑event override", style=discord.ButtonStyle.secondary)
            async def override_callback(interaction: discord.Interaction):
                await interaction.response.send_message("Select an event to set a custom channel for it.", ephemeral=True)
                view2 = OverrideView(self.cog, self.guild_id)
                embed2 = discord.Embed(
                    title="Per‑Event Override",
                    description="Choose an event and then pick a channel. Use the 'Clear' button to remove the override.",
                    color=discord.Color.blue()
                )
                await interaction.edit_original_response(embed=embed2, view=view2)
            override_button.callback = override_callback
            view.add_item(override_button)

            await interaction.edit_original_response(embed=embed, view=view)
        else:
            preset = select.values[0]
            embed = discord.Embed(
                title="Apply Preset",
                description=f"You selected **{preset}**. Choose a log channel below, or skip to keep the current one.",
                color=discord.Color.blue()
            )
            view = PresetApplyView(self.cog, self.guild_id, preset)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class EventToggleView(discord.ui.View):
    def __init__(self, cog, guild_id: int, config: Dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.config = config

        options = []
        for col in EVENT_COLUMNS:
            enabled = config.get(col, 0) == 1
            label = col.replace("event_", "").replace("_", " ").title()
            options.append(
                discord.SelectOption(
                    label=label,
                    value=col,
                    description="Enabled" if enabled else "Disabled",
                    default=enabled,
                    emoji="✅" if enabled else "❌"
                )
            )
        select = discord.ui.Select(
            placeholder="Toggle events (select to enable, deselect to disable)",
            options=options,
            min_values=0,
            max_values=len(options)
        )
        async def select_callback(interaction: discord.Interaction):
            enabled_events = select.values
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            for col in EVENT_COLUMNS:
                val = 1 if col in enabled_events else 0
                c.execute(f"UPDATE guild_log_config SET {col} = ? WHERE guild_id = ?",
                          (val, self.guild_id))
            c.execute("UPDATE guild_log_config SET preset = NULL WHERE guild_id = ?", (self.guild_id,))
            conn.commit()
            conn.close()
            await interaction.response.send_message("✅ Event toggles updated.", ephemeral=True)
        select.callback = select_callback
        self.add_item(select)

class OverrideView(discord.ui.View):
    def __init__(self, cog, guild_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.selected_event = None

        event_select = discord.ui.Select(
            placeholder="Choose an event",
            options=[
                discord.SelectOption(
                    label=col.replace("event_", "").replace("_", " ").title(),
                    value=col
                ) for col in EVENT_COLUMNS
            ]
        )
        async def event_callback(interaction: discord.Interaction):
            self.selected_event = event_select.values[0]
            await interaction.response.send_message(
                f"Selected: **{self.selected_event}**. Now choose a channel using the channel selector below.",
                ephemeral=True
            )
        event_select.callback = event_callback
        self.add_item(event_select)

        channel_select = discord.ui.ChannelSelect(
            channel_types=[discord.ChannelType.text],
            placeholder="Pick a text channel for this event",
            min_values=0,
            max_values=1
        )
        async def channel_callback(interaction: discord.Interaction):
            if self.selected_event is None:
                await interaction.response.send_message("Please select an event first.", ephemeral=True)
                return
            if channel_select.values:
                channel = channel_select.values[0]
                set_event_channel_override(self.guild_id, self.selected_event, channel.id)
                await interaction.response.send_message(
                    f"✅ {self.selected_event} will now log to {channel.mention}",
                    ephemeral=True
                )
            else:
                set_event_channel_override(self.guild_id, self.selected_event, None)
                await interaction.response.send_message(
                    f"✅ Override for {self.selected_event} removed.",
                    ephemeral=True
                )
        channel_select.callback = channel_callback
        self.add_item(channel_select)

        clear_button = discord.ui.Button(label="Clear all overrides", style=discord.ButtonStyle.danger)
        async def clear_callback(interaction: discord.Interaction):
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("UPDATE guild_log_config SET event_channel_overrides = '{}' WHERE guild_id = ?",
                      (self.guild_id,))
            conn.commit()
            conn.close()
            await interaction.response.send_message("✅ All per‑event overrides cleared.", ephemeral=True)
        clear_button.callback = clear_callback
        self.add_item(clear_button)

class Logging(commands.Cog):
    """AetherX Logging System"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        init_db()

    @app_commands.command(name="log", description="Configure the logging system for this server.")
    @app_commands.default_permissions(manage_guild=True)
    async def log(self, interaction: discord.Interaction):
        init_guild(interaction.guild_id)
        embed = discord.Embed(
            title="📜 AetherX Logging Configuration",
            description="Select a preset below to quickly enable a set of events, "
                        "or choose **Custom Setup** to toggle individual events and set per‑event channels.",
            color=discord.Color.blue()
        )
        view = LogSetupView(self, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def send_log(self, guild: discord.Guild, event_name: str, embed: discord.Embed):
        config = get_config(guild.id)
        if not config or not config.get(event_name, 0):
            return
        channel = get_log_channel(guild, config, event_name)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
            return
        embed = discord.Embed(
            title="Message Deleted",
            description=f"**Author:** {message.author.mention}\n"
                        f"**Channel:** {message.channel.mention}\n"
                        f"**Content:** {message.content or '*(no content)*'}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"ID: {message.id}")
        await self.send_log(message.guild, "event_message_delete", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.guild is None or before.content == after.content:
            return
        embed = discord.Embed(
            title="Message Edited",
            description=f"**Author:** {before.author.mention}\n"
                        f"**Channel:** {before.channel.mention}\n"
                        f"**Before:** {before.content[:1000]}\n"
                        f"**After:** {after.content[:1000]}",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"ID: {before.id}")
        await self.send_log(before.guild, "event_message_edit", embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} (`{member.id}`)",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Account Created", value=discord.utils.format_dt(member.created_at, style='R'))
        await self.send_log(member.guild, "event_member_join", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        is_kick = False
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 10:
                    is_kick = True
                    break
        except:
            pass
        event_name = "event_member_kick" if is_kick else "event_member_leave"
        title = "Member Kicked" if is_kick else "Member Left"
        color = discord.Color.dark_red() if is_kick else discord.Color.dark_gray()
        embed = discord.Embed(
            title=title,
            description=f"{member.mention} (`{member.id}`)",
            color=color,
            timestamp=discord.utils.utcnow()
        )
        if is_kick:
            embed.add_field(name="Kicked by", value=entry.user.mention if entry.user else "Unknown")
            embed.add_field(name="Reason", value=entry.reason or "No reason provided")
        await self.send_log(guild, event_name, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        embed = discord.Embed(
            title="Member Banned",
            description=f"{user.mention} (`{user.id}`)",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        try:
            async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    embed.add_field(name="Banned by", value=entry.user.mention if entry.user else "Unknown")
                    embed.add_field(name="Reason", value=entry.reason or "No reason provided")
                    break
        except:
            pass
        await self.send_log(guild, "event_member_ban", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        embed = discord.Embed(
            title="Member Unbanned",
            description=f"{user.mention} (`{user.id}`)",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await self.send_log(guild, "event_member_unban", embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.timed_out_until != after.timed_out_until:
            if after.timed_out_until is not None and (before.timed_out_until is None or after.timed_out_until > before.timed_out_until):
                embed = discord.Embed(
                    title="Member Muted",
                    description=f"{after.mention} (`{after.id}`)",
                    color=discord.Color.orange(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Until", value=discord.utils.format_dt(after.timed_out_until, style='R'))
                await self.send_log(after.guild, "event_member_mute", embed)
            elif before.timed_out_until is not None and after.timed_out_until is None:
                embed = discord.Embed(
                    title="Member Unmuted",
                    description=f"{after.mention} (`{after.id}`)",
                    color=discord.Color.green(),
                    timestamp=discord.utils.utcnow()
                )
                await self.send_log(after.guild, "event_member_unmute", embed)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(
            title="Channel Created",
            description=f"{channel.mention} (`{channel.id}`)\n**Type:** {channel.type}",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await self.send_log(channel.guild, "event_channel_create", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        embed = discord.Embed(
            title="Channel Deleted",
            description=f"**Name:** {channel.name}\n**Type:** {channel.type}\n**ID:** `{channel.id}`",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        await self.send_log(channel.guild, "event_channel_delete", embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        embed = discord.Embed(
            title="Channel Updated",
            description=f"{after.mention} (`{after.id}`)\n**Type:** {after.type}",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        if before.name != after.name:
            embed.add_field(name="Name Change", value=f"{before.name} → {after.name}", inline=False)
        await self.send_log(after.guild, "event_channel_update", embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        embed = discord.Embed(
            title="Role Created",
            description=f"{role.mention} (`{role.id}`)",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        await self.send_log(role.guild, "event_role_create", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        embed = discord.Embed(
            title="Role Deleted",
            description=f"**Name:** {role.name}\n**ID:** `{role.id}`",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        await self.send_log(role.guild, "event_role_delete", embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        embed = discord.Embed(
            title="Role Updated",
            description=f"{after.mention} (`{after.id}`)",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        if before.name != after.name:
            embed.add_field(name="Name Change", value=f"{before.name} → {after.name}", inline=False)
        await self.send_log(after.guild, "event_role_update", embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="Voice Join",
                description=f"{member.mention} joined {after.channel.mention}",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            await self.send_log(guild, "event_voice_join", embed)
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="Voice Leave",
                description=f"{member.mention} left {before.channel.mention}",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            await self.send_log(guild, "event_voice_leave", embed)
        elif before.channel != after.channel and after.channel is not None:
            embed = discord.Embed(
                title="Voice Move",
                description=f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}",
                color=discord.Color.gold(),
                timestamp=discord.utils.utcnow()
            )
            await self.send_log(guild, "event_voice_move", embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Logging(bot))