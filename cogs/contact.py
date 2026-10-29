import discord
from discord import app_commands
from discord.ext import commands

class Contact(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.hybrid_command(name="contact", description="Contact the bot developers")
    async def contact(self,ctx):
        e = discord.Embed(title="Contact Us", description="You can reach the bot developers through the following methods:")
        e.add_field(name="Snow", value="Email or text (if you have an ios device) snowekitsune@aether-x.org (fastest response)\n"
                    "DM https://discord.com/users/811016330517676073", inline=True)
        e.add_field(name="Androgalaxi", value="Join the support server at discord.gg/5XTPmdGaJV or the main AetherX server at disord.gg/yFY8Fnbtp9", inline=True)
        e.add_field(name="Lmutt", value="Join the main AetherX server at disord.gg/yFY8Fnbtp9", inline=True)
        await ctx.send(embed=e)


def setup(bot):
    bot.add_cog(Contact(bot))