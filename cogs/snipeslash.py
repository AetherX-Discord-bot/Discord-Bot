import discord
from discord import app_commands
from discord.ext import commands


class SnipeData:
    last_deleted = {}


class SlashSnipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.content and not message.attachments:
            return

        SnipeData.last_deleted[message.channel.id] = {
            "content": message.content,
            "author": message.author,
            "timestamp": message.created_at,
            "deleted_at": discord.utils.utcnow(),
            "message_id": message.id,
            "attachments": message.attachments,
        }

    @commands.hybrid_command(
        name="snipe",
        description="Show the most recently deleted message in this channel"
    )
    @commands.has_permissions(manage_messages=True)
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def snipe(self, ctx: commands.Context):

        channel_id = ctx.channel.id if ctx.channel is not None else None
        guild_id = ctx.guild.id if ctx.guild is not None else None

        deleted = SnipeData.last_deleted.get(channel_id)

        if not deleted:
            if ctx.interaction is not None:
                await ctx.interaction.response.send_message(
                    "No recently deleted messages to snipe!", ephemeral=True
                )
            else:
                await ctx.send("No recently deleted messages to snipe!")
            return

        message_link = None
        if guild_id is not None and channel_id is not None:
            message_link = (
                f"https://discord.com/channels/{guild_id}/{channel_id}/{deleted['message_id']}"
            )

        embed = discord.Embed(
            description=deleted["content"] or "*No text content*",
            color=discord.Color.blue(),
            timestamp=deleted["timestamp"]
        )

        embed.set_author(
            name=f"Message deleted • {deleted['author'].display_name}",
            icon_url=deleted["author"].display_avatar.url
        )

        info = f"🆔 Message ID: `{deleted['message_id']}`\n"
        if message_link:
            info += f"🔗 [Jump to Message]({message_link})\n"
        info += (
            f"👤 User ID: `{deleted['author'].id}`\n"
            f"⏰ Sent: <t:{int(deleted['timestamp'].timestamp())}:F>\n"
            f"🗑️ Deleted: <t:{int(deleted['deleted_at'].timestamp())}:R>"
        )

        embed.add_field(name="Message Info", value=info, inline=False)

        if deleted["attachments"]:
            embed.add_field(
                name="Attachments",
                value=f"{len(deleted['attachments'])} attachment(s)",
                inline=False
            )

        await ctx.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SlashSnipe(bot))