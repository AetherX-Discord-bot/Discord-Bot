import discord
from discord import app_commands
from discord.ext import commands

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="say", description="Send a message as the bot in the current channel.")
    async def say(self, ctx: commands.Context,*, message: str, attachment: discord.Attachment = None, embed: bool = False):
        """Make the bot say something"""
        if not isinstance(ctx.author, discord.Member) or not ctx.author.guild_permissions.administrator:
            if ctx.interaction is not None:
                await ctx.interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            else:
                await ctx.reply("You do not have permission to use this command.")
            return

        if ctx.interaction is not None:
            await ctx.interaction.response.defer(ephemeral=True)
        send_kwargs: dict = {}
        if ctx.message is not None and ctx.message.reference is not None:
            send_kwargs["reference"] = ctx.message.reference
            send_kwargs["mention_author"] = False
        files: list[discord.File] = []
        if attachment is not None:
            files.append(await attachment.to_file())
        elif ctx.message is not None:
            for att in ctx.message.attachments:
                files.append(await att.to_file())
        if files:
            send_kwargs["files"] = files
        if embed:
            e = discord.Embed(description=message, color=0x5865F2)
            if files:
                e.set_image(url=f"attachmen://{files[0].filename}")
                
            await ctx.channel.send(embed=e, **send_kwargs)
        else:
            
            await ctx.channel.send(message, **send_kwargs)
                

async def setup(bot):
    await bot.add_cog(Say(bot))