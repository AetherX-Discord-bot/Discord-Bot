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
    async def choose(self, ctx, *, choices: str = None):
        """Let the bot choose between multiple options (comma-separated)."""
        if not choices:
            embed = discord.Embed(description="Please provide at least two choices, separated by commas.", color=discord.Color.purple())
            await ctx.send(embed=embed)
            return
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

    @commands.hybrid_command(name="uwu", aliases=["IMFUCKINGDYING"])
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

    @commands.hybrid_command()
    async def eightball(self, ctx, *, question: str):
        """Ask the magic 8-ball a question."""
        responses = [
            "It is certain.", "Without a doubt.", "You may rely on it.", "Yes, definitely.",
            "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
        ]
        embed = discord.Embed(title="🎱 8-Ball", description=f"**Question:** {question}\n**Answer:** {random.choice(responses)}", color=discord.Color.purple())
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def clap(self, ctx, *, text: str):
        """Add clap emojis between words."""
        clapped = ' 👏 '.join(text.split())
        embed = discord.Embed(title="Clap Text", description=clapped, color=discord.Color.purple())
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def owo(self, ctx, *, text: str):
        """OwO-ify your message."""
        owo_text = text.replace('r', 'w').replace('l', 'w').replace('R', 'W').replace('L', 'W')
        owo_text = owo_text.replace('no', 'nyo').replace('No', 'Nyo')
        owo_text = owo_text.replace('u', 'uwu').replace('U', 'UwU')
        embed = discord.Embed(title="OwO-ified", description=owo_text + ' OwO', color=discord.Color.purple())
        if ctx.interaction is None:
            try:
                await ctx.message.delete()
            except Exception:
                pass
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Fun(bot))
