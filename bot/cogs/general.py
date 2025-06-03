import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)  # ms
        await ctx.send(f'Pong! Latency: {latency}ms')

    @commands.hybrid_command()
    async def info(self, ctx):
        load_dotenv()
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

        # Fetch bot user and about me
        bot_user = self.bot.user
        bot_name = bot_user.name if bot_user else "AetherX Base Bot"
        bot_about = bot_user.bio if hasattr(bot_user, 'bio') and bot_user.bio else "A simple Discord bot using discord.py"

        embed = discord.Embed(
            title=bot_name,
            description=bot_about,
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
        
        # To remove all variables loaded by dotenv (if you know their names)
        for var in ['BOT_OWNERS', 'BOT_DEVELOPERS', 'BOT_WEBSITE', 'BOT_SUPPORT_SERVER', 'BOT_INVITE_URL']:
            os.environ.pop(var, None)

    @commands.hybrid_command(name="avatar")
    async def avatar(self, ctx, user: discord.User = None):
        """Get the profile picture of a user by mention or ID."""
        user = user or ctx.author
        embed = discord.Embed(title=f"{user}'s Avatar", color=discord.Color.blue())
        embed.set_image(url=user.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="banner")
    async def banner(self, ctx, user: discord.User = None):
        """Get the banner of a user by mention or ID."""
        user = user or ctx.author
        # Fetch user to get banner (requires HTTP request)
        user = await self.bot.fetch_user(user.id)
        if user.banner:
            banner_url = user.banner.url if hasattr(user.banner, 'url') else f"https://cdn.discordapp.com/banners/{user.id}/{user.banner}.png?size=4096"
            embed = discord.Embed(title=f"{user}'s Banner", color=discord.Color.blue())
            embed.set_image(url=banner_url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{user} does not have a banner set.")

async def setup(bot):
    await bot.add_cog(General(bot))
