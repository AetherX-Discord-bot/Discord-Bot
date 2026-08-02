import discord
from discord import app_commands
from discord.ext import commands
from shared_data import SnipeData

class SlashSnipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="snipe",
        description="Show the most recently deleted message in this channel"
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def snipe(self, ctx: commands.Context):

        channel_id = ctx.channel.id if ctx.channel is not None else getattr(ctx, "channel_id", None)
        guild_id = ctx.guild.id if ctx.guild is not None else getattr(ctx, "guild_id", None)

        deleted = SnipeData.last_deleted.get(channel_id)

        if not deleted:
            interaction = getattr(ctx, "interaction", None)
            if interaction is not None and getattr(interaction, "response", None) is not None:
                await interaction.response.send_message("No recently deleted messages to snipe!", ephemeral=True)
            else:
                await ctx.send("No recently deleted messages to snipe!")
            return

        if guild_id is not None and channel_id is not None:
            message_link = f"https://discord.com/channels/{guild_id}/{channel_id}/{deleted['message_id']}"
        else:
            message_link = None
        
        embed = discord.Embed(
            description=deleted["content"],
            color=discord.Color.blue(),
            timestamp=deleted["timestamp"]
        )
        
        embed.set_author(
            name=f"Message deleted • {deleted['author'].display_name}",
            icon_url=deleted["author"].display_avatar.url
        )
        
        embed.add_field(
            name="Message Info",
            value=(
                f"🆔 Message ID: `{deleted['message_id']}`\n"
                f"🔗 [Jump to Message]({message_link})\n"
                f"👤 User ID: `{deleted['author'].id}`\n"
                f"⏰ Sent: <t:{int(deleted['timestamp'].timestamp())}:F>\n"
                f"🗑️ Deleted: <t:{int(deleted['deleted_at'].timestamp())}:R>"
            ),
            inline=False
        )

        if deleted["attachments"]:
            embed.add_field(
                name="Attachments",
                value=f"{len(deleted['attachments'])} attachment(s)",
                inline=False
            )

        await ctx.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SlashSnipe(bot))