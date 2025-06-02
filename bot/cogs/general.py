import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)  # ms
        await ctx.send(f'Pong! Latency: {latency}ms')

    @commands.command()
    async def info(self, ctx):
        owner_ids = os.getenv('BOT_OWNERS', '')
        developer_ids = os.getenv('BOT_DEVELOPERS', '')
        bot_website = os.getenv('BOT_WEBSITE', None)
        bot_support = os.getenv('BOT_SUPPORT_SERVER', None)
        bot_invite = os.getenv('BOT_INVITE_URL', None)
        owner_mentions = []
        developer_mentions = []
        for oid in owner_ids.split(','):
            oid = oid.strip()
            if oid.isdigit():
                owner_mentions.append(f'<@{oid}>')
        for did in developer_ids.split(','):
            did = did.strip()
            if did.isdigit():
                developer_mentions.append(f'<@{did}>')

        embed = discord.Embed(
            title="Bot Information",
            description="A simple Discord bot using discord.py",
            color=discord.Color.blue()
        )
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms")
        embed.add_field(name="Servers", value=f"{len(self.bot.guilds)}")
        embed.add_field(name="Owners", value=(', '.join(owner_mentions) or 'N/A'), inline=False)
        embed.add_field(name="Developers", value=(', '.join(developer_mentions) or 'N/A'), inline=False)
        if bot_website:
            embed.add_field(name="Website", value=bot_website, inline=False)
        if bot_support:
            embed.add_field(name="Support Server", value=bot_support, inline=False)
        if bot_invite:
            embed.add_field(name="Invite URL", value=bot_invite, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))
