import discord
from discord.ext import commands
import random

class Fun(commands.Cog):
    """A cog for fun and silly commands."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    @commands.hybrid_command()
    async def say(self, ctx, *, message: str):
        """Make the bot say something (shows who said it, unless secret phrase is used)."""
        secret_phrase = "sussyhiddenimposterfromamongus"
        show_footer = True
        if message.startswith(secret_phrase):
            message = message[len(secret_phrase):].lstrip()
            show_footer = False
        embed = discord.Embed(description=message, color=discord.Color.purple())
        if show_footer:
            embed.set_footer(text=f"Said by {ctx.author}")
        # Delete original message if invoked as a chat command
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def choose(self, ctx, *, choices: str):
        """Let the bot choose between multiple options (comma-separated)."""
        options = [c.strip() for c in choices.split(',') if c.strip()]
        embed = discord.Embed(color=discord.Color.purple())
        if len(options) < 2:
            embed.description = "Please provide at least two choices, separated by commas."
            await ctx.send(embed=embed)
            return
        choice = random.choice(options)
        embed.title = "Choice"
        embed.add_field(name="Options", value=", ".join(options), inline=False)
        embed.add_field(name="Selected", value=f"**{choice}**", inline=False)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def reverse(self, ctx, *, text: str):
        """Reverse the given text."""
        embed = discord.Embed(title="Reversed Text", description=text[::-1], color=discord.Color.purple())
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def uwu(self, ctx, *, text: str):
        """UwU-ify your message."""
        uwu_text = text.replace('r', 'w').replace('l', 'w').replace('R', 'W').replace('L', 'W')
        uwu_text = uwu_text.replace('no', 'nyo').replace('No', 'Nyo')
        embed = discord.Embed(title="UwU-ified", description=uwu_text + ' UwU', color=discord.Color.purple())
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def mock(self, ctx, *, text: str):
        """SaRcAsM tExT gEnErAtOr."""
        mocked = ''.join(c.upper() if i % 2 else c.lower() for i, c in enumerate(text))
        embed = discord.Embed(title="Mocked Text", description=mocked, color=discord.Color.purple())
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Fun(bot))
