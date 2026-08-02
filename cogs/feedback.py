import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

class Feedback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="feedback", description="Submit feedback for the bot.")
    async def feedback(self, interaction: discord.Interaction):
        """Slash command that opens a feedback modal."""

        class FeedbackModal(discord.ui.Modal, title="Submit Feedback"):
            feedback_input = discord.ui.TextInput(
                label="Your feedback",
                placeholder="Type here...",
                required=True,
                min_length=10,
                style=discord.TextStyle.paragraph 
            )

            async def on_submit(self, interaction: discord.Interaction):
                timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
                with open("feedback.txt", "a") as f:
                    f.write(f"{timestamp} - {interaction.user} ({interaction.user.id}): {self.feedback_input.value}\n")
                await interaction.response.send_message("Thank you for your feedback!", ephemeral=True)

        await interaction.response.send_modal(FeedbackModal())

async def setup(bot):
    await bot.add_cog(Feedback(bot))