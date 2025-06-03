import discord
from discord.ext import commands

class General(commands.Cog):
    """A cog to handle general commands like ping, info, avatar, and banner."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    @commands.hybrid_command()
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)  # ms
        await ctx.send(f'Pong! Latency: {latency}ms')

    @commands.hybrid_command()
    async def info(self, ctx):
        owner_ids = self.config.get('BOT_OWNERS', [])
        developer_ids = self.config.get('BOT_DEVELOPERS', [])
        bot_website = self.config.get('BOT_WEBSITE', None)
        bot_support = self.config.get('BOT_SUPPORT_SERVER', None)
        bot_invite = self.config.get('BOT_INVITE_URL', None)
        owner_mentions = [f'<@{oid}>' for oid in owner_ids]
        developer_mentions = [f'<@{did}>' for did in developer_ids]

        # Fetch bot user and about me
        bot_user = self.bot.user
        bot_name = bot_user.name if bot_user else "AetherX Base Bot"
        bot_about = getattr(bot_user, 'bio', None) or "A simple Discord bot using discord.py"

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
