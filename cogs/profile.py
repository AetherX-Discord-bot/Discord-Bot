import discord
from discord.ext import commands
import sqlite3
import logging

DB_NAME = "AetherX.db"


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_connection(self):
        try:
            conn = sqlite3.connect(DB_NAME)
            logging.info("Connected to AetherX.db successfully.")
            return conn
        except sqlite3.Error as e:
            logging.error(f"Failed to connect to AetherX.db {e}")
            return None

    @commands.command(name="profile")
    async def profile(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        conn = self.get_db_connection()
        if not conn:
            await ctx.send("Database connection failed. Contact Lmutt090.")
            return
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT bio, favorite_color, affil, allowstatusview, dabloons, inventory, showlongprofile FROM users WHERE user_id = ?", (user.id,))
            result = cursor.fetchone()
            if result is None:
                cursor.execute("""
                    INSERT INTO users (user_id, bio, favorite_color, affil, allowstatusview, dabloons, inventory, showlongprofile)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user.id, "", "#FFFFFF", "User", False, 0, "{}", 0))
                conn.commit()
                bio, favorite_color, affil, allowstatusview, dabloons, inventory, showlongprofile = "", "#FFFFFF", "User", False, 0, "{}", 0
            else:
                bio, favorite_color, affil, allowstatusview, dabloons, inventory, showlongprofile = result
                bio = (bio or "").replace("\\n", "\n")
                inventory = inventory or "{}"

            embed = discord.Embed(title=f"{user.name}'s Profile", color=int(favorite_color.replace("#", ""), 16))
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name="**Bio**", value=bio or "No bio set.", inline=False)
            embed.add_field(name="**Affiliation**", value=affil, inline=False)
            await ctx.send(embed=embed)
        finally:
            conn.close()

    @commands.command(name="settings")
    async def settings(self, ctx):
        conn = self.get_db_connection()
        if not conn:
            await ctx.send("Database connection failed. Contact Lmutt090.")
            return
        cursor = conn.cursor()
        cursor.execute("SELECT bio, favorite_color, affil, allowstatusview FROM users WHERE user_id = ?", (ctx.author.id,))
        result = cursor.fetchone()
        if result is None:
            cursor.execute("INSERT INTO users (user_id, bio, favorite_color, affil, allowstatusview) VALUES (?, ?, ?, ?, ?)",
                           (ctx.author.id, "", "#FFFFFF", "User", False))
            conn.commit()
            bio, color, affil, status_view = "", "#FFFFFF", "User", False
        else:
            bio, color, affil, status_view = result
        conn.close()

        view = SettingsView(ctx.author.id, bio, color, affil, status_view)
        await ctx.send("Here are your settings:", view=view)


class SettingsView(discord.ui.View):
    def __init__(self, user_id, bio, color, affil, status):
        super().__init__(timeout=120)
        self.add_item(ToggleStatusButton(user_id, status))
        self.add_item(ChangeBioButton(user_id))
        self.add_item(ChangeColorButton(user_id))


class ToggleStatusButton(discord.ui.Button):
    def __init__(self, user_id, current_status):
        label = f"Status View: {'Enabled' if current_status else 'Disabled'}"
        super().__init__(label=label, style=discord.ButtonStyle.green if current_status else discord.ButtonStyle.red)
        self.user_id = user_id
        self.current_status = current_status

    async def callback(self, interaction: discord.Interaction):
        new_status = not self.current_status
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET allowstatusview = ? WHERE user_id = ?", (int(new_status), self.user_id))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"Status View is now {'Enabled' if new_status else 'Disabled'}.", ephemeral=True)


class ChangeBioModal(discord.ui.Modal):
    new_bio = discord.ui.TextInput(label="Enter your new bio", style=discord.TextStyle.paragraph, max_length=200)

    def __init__(self, user_id):
        super().__init__(title="Change Bio")
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET bio = ? WHERE user_id = ?", (self.new_bio.value, self.user_id))
        conn.commit()
        conn.close()
        await interaction.response.send_message("Your bio has been updated.", ephemeral=True)


class ChangeBioButton(discord.ui.Button):
    def __init__(self, user_id):
        super().__init__(label="Change Bio", style=discord.ButtonStyle.blurple)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ChangeBioModal(self.user_id))


class ChangeColorModal(discord.ui.Modal, title="Change Favorite Color"):
    new_color = discord.ui.TextInput(label="Enter hex color (e.g. #FF0000)", style=discord.TextStyle.short, max_length=7)

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        val = self.new_color.value.strip()
        if not val.startswith("#") or len(val) != 7:
            await interaction.response.send_message("Invalid hex color.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET favorite_color = ? WHERE user_id = ?", (val, self.user_id))
        conn.commit()
        conn.close()
        await interaction.response.send_message("Your favorite color has been updated.", ephemeral=True)


class ChangeColorButton(discord.ui.Button):
    def __init__(self, user_id):
        super().__init__(label="Change Favorite Color", style=discord.ButtonStyle.blurple)
        self.user_id = user_id

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ChangeColorModal(self.user_id))


async def setup(bot):
    await bot.add_cog(Profile(bot))