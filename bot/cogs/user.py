import discord
from discord.ext import commands
import sqlite3
import os

class User(commands.Cog):
    """A cog for user profile and settings management."""
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))

    @commands.hybrid_command(aliases=["user"])
    async def profile(self, ctx, user: discord.User = None):
        """Show your profile or another user's profile."""
        user = user or ctx.author
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO users (user_id) VALUES (?)
        """, (user.id,))
        c.execute("""
            SELECT personal_prefix, bio, profile_picture, dm_enabled, show_status, show_dabloons, dabloons, karma, xp, level
            FROM users WHERE user_id = ?
        """, (user.id,))
        row = c.fetchone()
        conn.close()
        if not row:
            await ctx.send("User not found in the database.")
            return
        (personal_prefix, bio, profile_picture, dm_enabled, show_status, show_dabloons, dabloons, karma, xp, level) = row
        embed = discord.Embed(title=f"{user.display_name}'s Profile", color=discord.Color.blue())
        embed.set_thumbnail(url=profile_picture or user.display_avatar.url)
        embed.add_field(name="Bio", value=bio or "No bio set.", inline=False)
        # Show all statuses: custom, playing, etc.
        status_text = []
        member = ctx.guild.get_member(user.id) if ctx.guild else None
        # Prefer Member object for richer presence
        target = member or user
        # Custom status (if set)
        if hasattr(target, 'activities'):
            for activity in target.activities:
                if isinstance(activity, discord.CustomActivity) and getattr(activity, 'name', None):
                    status_text.append(f"Custom: {activity.name}")
                elif isinstance(activity, discord.Game):
                    status_text.append(f"Playing: {activity.name}")
                elif isinstance(activity, discord.Streaming):
                    status_text.append(f"Streaming: {activity.name}")
                elif isinstance(activity, discord.Activity):
                    kind = str(activity.type).split('.')[-1].capitalize()
                    status_text.append(f"{kind}: {activity.name}")
        # Fallback to user status (prefer Member.status for accuracy)
        if hasattr(target, 'status'):
            pretty_status = str(target.status).replace('dnd', 'Do Not Disturb').capitalize()
            status_text.append(f"Status: {pretty_status}")
        if show_status:
            embed.add_field(name="Status", value="\n".join(status_text) or "No status", inline=True)
        if show_dabloons:
            embed.add_field(name="Dabloons", value=f"{dabloons:.2f}", inline=True)
        embed.add_field(name="Karma", value=karma, inline=True)
        embed.add_field(name="XP", value=f"{xp:.2f}", inline=True)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="DMS Allowed", value="Yes" if dm_enabled else "No", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def settings(self, ctx, setting: str = None, value: str = None):
        """View or change your user settings. Usage: settings <setting> <value>"""
        valid_settings = [
            "personal_prefix", "bio", "profile_picture", "dm_enabled", "show_status", "show_dabloons"
        ]
        if not setting:
            # Show current settings
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                INSERT OR IGNORE INTO users (user_id) VALUES (?)
            """, (ctx.author.id,))
            c.execute("""
                SELECT personal_prefix, bio, profile_picture, dm_enabled, show_status, show_dabloons
                FROM users WHERE user_id = ?
            """, (ctx.author.id,))
            row = c.fetchone()
            conn.close()
            if not row:
                await ctx.send("No settings found for your user.")
                return
            (personal_prefix, bio, profile_picture, dm_enabled, show_status, show_dabloons) = row
            embed = discord.Embed(title=f"{ctx.author.display_name}'s Settings", color=discord.Color.green())
            embed.add_field(name="Prefix", value=personal_prefix or "Default", inline=True)
            embed.add_field(name="Bio", value=bio or "No bio set.", inline=False)
            embed.add_field(name="Profile Picture", value=profile_picture or "Using your profile picture", inline=False)
            embed.add_field(name="DM Enabled", value="Yes" if dm_enabled else "No", inline=True)
            embed.add_field(name="Show Status", value="Yes" if show_status else "No", inline=True)
            embed.add_field(name="Show Dabloons", value="Yes" if show_dabloons else "No", inline=True)
            # Use buttons for settings modification
            class SettingsView(discord.ui.View):
                def __init__(self, cog, user_id, current_settings):
                    super().__init__(timeout=120)
                    self.cog = cog
                    self.user_id = user_id
                    self.current_settings = current_settings

                @discord.ui.button(label="Toggle DM Enabled", style=discord.ButtonStyle.primary)
                async def toggle_dm(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.toggle_setting(interaction, 'dm_enabled')

                @discord.ui.button(label="Toggle Show Status", style=discord.ButtonStyle.primary)
                async def toggle_status(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.toggle_setting(interaction, 'show_status')

                @discord.ui.button(label="Toggle Show Dabloons", style=discord.ButtonStyle.primary)
                async def toggle_dabloons(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.toggle_setting(interaction, 'show_dabloons')

                # Add buttons for text-based settings (prefix, bio, profile_picture)
                @discord.ui.button(label="Edit Prefix", style=discord.ButtonStyle.secondary, row=1)
                async def edit_prefix(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.prompt_text(interaction, 'personal_prefix', 'Enter your new prefix:')

                @discord.ui.button(label="Edit Bio", style=discord.ButtonStyle.secondary, row=1)
                async def edit_bio(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.prompt_text(interaction, 'bio', 'Enter your new bio:')

                @discord.ui.button(label="Edit Profile Picture", style=discord.ButtonStyle.secondary, row=1)
                async def edit_picture(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await self.prompt_text(interaction, 'profile_picture', 'Enter a direct image URL for your new profile picture:')

                async def toggle_setting(self, interaction, setting):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("You can't change another user's settings!", ephemeral=True)
                        return
                    conn = sqlite3.connect(self.cog.db_path)
                    c = conn.cursor()
                    c.execute(f"SELECT {setting} FROM users WHERE user_id = ?", (self.user_id,))
                    current = c.fetchone()[0]
                    new_value = 0 if current else 1
                    c.execute(f"UPDATE users SET {setting} = ? WHERE user_id = ?", (new_value, self.user_id))
                    conn.commit()
                    c.execute("SELECT personal_prefix, bio, profile_picture, dm_enabled, show_status, show_dabloons FROM users WHERE user_id = ?", (self.user_id,))
                    updated = c.fetchone()
                    conn.close()
                    embed = discord.Embed(title=f"{interaction.user.display_name}'s Settings", color=discord.Color.green())
                    embed.add_field(name="Prefix", value=updated[0] or "Default", inline=True)
                    embed.add_field(name="Bio", value=updated[1] or "No bio set.", inline=False)
                    embed.add_field(name="Profile Picture", value=updated[2] or "Not set", inline=False)
                    embed.add_field(name="DM Enabled", value="Yes" if updated[3] else "No", inline=True)
                    embed.add_field(name="Show Status", value="Yes" if updated[4] else "No", inline=True)
                    embed.add_field(name="Show Dabloons", value="Yes" if updated[5] else "No", inline=True)
                    await interaction.response.edit_message(embed=embed, view=self)

                async def prompt_text(self, interaction, setting, prompt):
                    if interaction.user.id != self.user_id:
                        await interaction.response.send_message("You can't change another user's settings!", ephemeral=True)
                        return
                    await interaction.response.send_modal(SettingsModal(self, setting, prompt))

            class SettingsModal(discord.ui.Modal, title="Edit Setting"):
                def __init__(self, view, setting, prompt):
                    super().__init__()
                    self.view = view
                    self.setting = setting
                    self.prompt = prompt
                    self.input = discord.ui.TextInput(label=prompt, style=discord.TextStyle.short, required=True)
                    self.add_item(self.input)

                async def on_submit(self, interaction: discord.Interaction):
                    value = self.input.value.strip()
                    conn = sqlite3.connect(self.view.cog.db_path)
                    c = conn.cursor()
                    c.execute(f"UPDATE users SET {self.setting} = ? WHERE user_id = ?", (value, self.view.user_id))
                    conn.commit()
                    c.execute("SELECT personal_prefix, bio, profile_picture, dm_enabled, show_status, show_dabloons FROM users WHERE user_id = ?", (self.view.user_id,))
                    updated = c.fetchone()
                    conn.close()
                    embed = discord.Embed(title=f"{interaction.user.display_name}'s Settings", color=discord.Color.green())
                    embed.add_field(name="Prefix", value=updated[0] or "Default", inline=True)
                    embed.add_field(name="Bio", value=updated[1] or "No bio set.", inline=False)
                    embed.add_field(name="Profile Picture", value=updated[2] or "Not set", inline=False)
                    embed.add_field(name="DM Enabled", value="Yes" if updated[3] else "No", inline=True)
                    embed.add_field(name="Show Status", value="Yes" if updated[4] else "No", inline=True)
                    embed.add_field(name="Show Dabloons", value="Yes" if updated[5] else "No", inline=True)
                    await interaction.response.edit_message(embed=embed, view=self.view)

            view = SettingsView(self, ctx.author.id, (personal_prefix, bio, profile_picture, dm_enabled, show_status, show_dabloons))
            await ctx.send(embed=embed, view=view)
            return
        if setting not in valid_settings:
            await ctx.send(f"Invalid setting. Valid settings: {', '.join(valid_settings)}")
            return
        # Convert value for boolean fields
        if setting in ["dm_enabled", "show_status", "show_dabloons"]:
            if value is None:
                await ctx.send(f"Please provide a value for {setting} (yes/no).")
                return
            value = value.lower()
            if value in ["yes", "true", "1", "on"]:
                value = 1
            elif value in ["no", "false", "0", "off"]:
                value = 0
            else:
                await ctx.send(f"Invalid value for {setting}. Use yes/no.")
                return
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (ctx.author.id,))
        c.execute(f"UPDATE users SET {setting} = ? WHERE user_id = ?", (value, ctx.author.id))
        conn.commit()
        conn.close()
        await ctx.send(f"Updated `{setting}` to `{value}`.")

async def setup(bot):
    await bot.add_cog(User(bot))
