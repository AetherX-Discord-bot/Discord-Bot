import discord
from discord.ext import commands
from shared_data import SnipeData

class Snipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        SnipeData.record_deleted_message(message)

    @commands.command(name="snipe")
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx):
        deleted = SnipeData.last_deleted.get(ctx.channel.id)
        
        if not deleted:
            await ctx.send("No recently deleted messages to snipe!")
            return

        message_link = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{deleted['message_id']}"
        
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

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Snipe(bot))