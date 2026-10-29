import discord
from discord.ext import commands
import random
import os

class CoinflipCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="coinflip", aliases=["flip", "coin", "cf"])
    async def coinflip(self, ctx):
        """Flip a coin and get heads or tails"""
        outcome = random.choice(["Heads", "Tails"])
        
        if outcome == "Heads":
            image_path = os.path.join("Assets", "heads.png")
        else:
            image_path = os.path.join("Assets", "tails.png")
        
        embed = discord.Embed(
            title="🎲 Coin Flip",
            description=f"The coin landed on... **{outcome}**!",
            color=0x00008B
        )
        
        avatar_url = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        embed.set_footer(text=f"Flipped by {ctx.author.display_name}", icon_url=avatar_url)
        
        try:
            if os.path.exists(image_path):
                file = discord.File(image_path, filename=os.path.basename(image_path))
                embed.set_image(url=f"attachment://{os.path.basename(image_path)}")
                await ctx.send(file=file, embed=embed)
            else:
                print(f"Warning: Image not found at {image_path}")
                embed.add_field(name="ℹ️ Note", value="Coin flip images are missing. Please place `heads.png` and `tails.png` in an `Assets` folder.", inline=False)
                await ctx.send(embed=embed)
        except Exception as e:
            embed.add_field(name="⚠️ Error", value="Could not load coin flip image. Check console logs.", inline=False)
            await ctx.send(embed=embed)
            print(f"Error sending coinflip image: {e}")

async def setup(bot):
    await bot.add_cog(CoinflipCog(bot))