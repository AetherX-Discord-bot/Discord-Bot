import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import time

class AFKCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afk_users = {}
        self.cooldowns = {}

    @commands.hybrid_command(name="afk", description="Set an AFK status with a custom message")
    async def afk(self, ctx: commands.Context, reason: str = "AFK", persistent: bool = False):
        """Slash command to set AFK status"""
        user = ctx.author
        
        if user.id in self.cooldowns and self.cooldowns[user.id] > time.time():
            remaining = int(self.cooldowns[user.id] - time.time())
            return await ctx.send(
                f"⏳ You can set AFK again in {remaining} seconds",
                ephemeral=True
            )

        self.afk_users[user.id] = {
            "reason": reason,
            "start_time": time.time(),
            "original_nick": user.display_name,
            "persistent": persistent
        }
        
        try:
            guild = ctx.guild
            if guild:
                member = None
                if isinstance(ctx.author, discord.Member):
                    member = ctx.author
                else:
                    member = guild.get_member(user.id)
                    if member is None:
                        try:
                            member = await guild.fetch_member(user.id)
                        except:
                            member = None

                if member:
                    await member.edit(nick=f"[AFK] {user.display_name[:26]}"[:32])
        except:
            pass

        persistent_text = "Persistent notifications" if persistent else "Temporary notifications (10s)"
        embed = discord.Embed(
            title="🚀 AFK Status Activated",
            description=f"{user.mention} is now AFK: **{reason}**\n"
                       f"🔔 {persistent_text}",
            color=0x9C84EF
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)
        self.cooldowns[user.id] = time.time() + 30

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        replied_user = None
        if message.reference and message.reference.resolved:
            try:
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                replied_user = replied_message.author
            except:
                pass
        
        users_to_check = list(message.mentions)
        if replied_user and replied_user not in users_to_check:
            users_to_check.append(replied_user)
        
        for user in users_to_check:
            if user.id in self.afk_users:
                afk_data = self.afk_users[user.id]
                duration = self.format_duration(time.time() - afk_data["start_time"])
                
                embed = discord.Embed(
                    description=f"ℹ️ {user.mention} is AFK: **{afk_data['reason']}**\n"
                              f"⌛ Duration: {duration}",
                    color=0xED8796
                )
                
                if afk_data["persistent"]:
                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send(embed=embed, delete_after=10)

        if message.author.id in self.afk_users:
            afk_data = self.afk_users.pop(message.author.id)
            duration = self.format_duration(time.time() - afk_data["start_time"])
            
            try:
                await message.author.edit(nick=afk_data["original_nick"])
            except:
                pass

            embed = discord.Embed(
                title="🎉 Welcome Back!",
                description=f"You were AFK for {duration}",
                color=0xA6DA95
            )
            welcome = await message.channel.send(message.author.mention, embed=embed)
            await asyncio.sleep(10)
            await welcome.delete()

    def format_duration(self, seconds: float) -> str:
        """Converts seconds to human-readable time"""
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"

async def setup(bot):
    await bot.add_cog(AFKCog(bot))