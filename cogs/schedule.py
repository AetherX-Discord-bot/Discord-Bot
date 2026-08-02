import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import pytz
from typing import Optional
import sqlite3
import aiosqlite

class ScheduleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_scheduled_messages.start()
        
    async def cog_unload(self):
        self.check_scheduled_messages.cancel()

    async def init_db(self):
        """Initialize database table for scheduled messages"""
        async with aiosqlite.connect('AetherX.db') as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    scheduled_time TIMESTAMP NOT NULL,
                    timezone TEXT NOT NULL,
                    ping_role_id INTEGER,
                    author_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.init_db()

    @commands.hybrid_command(
        name="schedule-announcement",
        description="Schedule a message to be sent at a specific time"
    )
    @app_commands.choices(
        timezone=[
            app_commands.Choice(name="EST", value="America/New_York"),
            app_commands.Choice(name="PST", value="America/Los_Angeles"),
            app_commands.Choice(name="CST", value="America/Chicago"),
            app_commands.Choice(name="GMT", value="Europe/London"),
            app_commands.Choice(name="CET", value="Europe/Paris"),
            app_commands.Choice(name="AEST", value="Australia/Sydney"),
        ]
    )
    async def schedule_announcement(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        message: str,
        datetime: str,
        timezone: app_commands.Choice[str],
        ping_role: Optional[discord.Role] = None
    ):
        """Schedule an announcement for a specific time"""
        # Permission check
        author = ctx.author
        if not isinstance(author, discord.Member) or not author.guild_permissions.manage_messages:
            await ctx.send("❌ You need the 'Manage Messages' permission to use this command.", delete_after=10)
            return

        interaction = getattr(ctx, "interaction", None)

        guild = ctx.guild or (interaction.guild if interaction else None)
        if guild is None:
            if interaction:
                await interaction.response.send_message("❌ This command must be used in a guild.", ephemeral=True)
            else:
                await ctx.send("❌ This command must be used in a guild.")
            return

        bot_member = guild.me or guild.get_member(self.bot.user.id)
        if bot_member is None:
            everyone_role = getattr(guild, 'default_role', None)
            if everyone_role is None:
                from typing import cast
                class _Fake:
                    pass
                bot_permissions = channel.permissions_for(cast(discord.Role, _Fake()))
            else:
                bot_permissions = channel.permissions_for(everyone_role)
        else:
            bot_permissions = channel.permissions_for(bot_member)
        if not bot_permissions.send_messages:
            if interaction:
                await interaction.response.send_message(f"❌ I don't have permission to send messages in {channel.mention}.", ephemeral=True)
            else:
                await ctx.send(f"❌ I don't have permission to send messages in {channel.mention}.")
            return

        try:
            scheduled_time = self.parse_datetime(datetime, timezone.value)
            
            if scheduled_time <= discord.utils.utcnow():
                if interaction:
                    await interaction.response.send_message("❌ Please select a future date and time.", ephemeral=True)
                else:
                    await ctx.send("❌ Please select a future date and time.")
                return

            async with aiosqlite.connect('AetherX.db') as db:
                await db.execute('''
                    INSERT INTO scheduled_messages 
                    (guild_id, channel_id, message, scheduled_time, timezone, ping_role_id, author_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    guild.id,
                    channel.id,
                    message,
                    scheduled_time.isoformat(),
                    timezone.value,
                    ping_role.id if ping_role else None,
                    ctx.author.id
                ))
                await db.commit()

            local_time = scheduled_time.astimezone(pytz.timezone(timezone.value))
            time_str = local_time.strftime('%Y-%m-%d %H:%M %Z')
            
            response = (
                f"✅ Message scheduled for **{time_str}** in {channel.mention}.\n"
                f"**Preview:** {message[:100]}{'...' if len(message) > 100 else ''}"
            )
            if ping_role:
                response += f"\n**Will ping:** {ping_role.mention}"

            if interaction:
                await interaction.response.send_message(response, ephemeral=True)
            else:
                await ctx.send(response)

        except ValueError as e:
            if interaction:
                await interaction.response.send_message(f"❌ Invalid date/time format: {str(e)}\nUse: YYYY-MM-DD HH:MM (24h format)", ephemeral=True)
            else:
                await ctx.send(f"❌ Invalid date/time format: {str(e)}\nUse: YYYY-MM-DD HH:MM (24h format)")
        except Exception as e:
            if interaction:
                await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
            else:
                await ctx.send(f"❌ An error occurred: {str(e)}")

    def parse_datetime(self, datetime_str: str, timezone_str: str) -> datetime:
        """Parse datetime string with timezone and return UTC datetime"""
        try:
            naive_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            
            tz = pytz.timezone(timezone_str)
            localized_dt = tz.localize(naive_dt)
            
            utc_dt = localized_dt.astimezone(pytz.UTC)
            
            return utc_dt
        except ValueError:
            raise ValueError("Invalid datetime format. Use: YYYY-MM-DD HH:MM")

    @tasks.loop(minutes=1)
    async def check_scheduled_messages(self):
        """Check every minute for due messages"""
        try:
            now = discord.utils.utcnow()
            
            async with aiosqlite.connect('AetherX.db') as db:
                async with db.execute(
                    'SELECT * FROM scheduled_messages WHERE scheduled_time <= ?',
                    (now.isoformat(),)
                ) as cursor:
                    due_messages = await cursor.fetchall()

                for msg in due_messages:
                    try:
                        channel = self.bot.get_channel(msg[2])  # channel_id
                        if channel:
                            final_message = msg[3]
                            
                            if msg[6]:
                                final_message = f"<@&{msg[6]}> {final_message}"
                            
                            await channel.send(final_message)
                        
                        await db.execute('DELETE FROM scheduled_messages WHERE id = ?', (msg[0],))
                        await db.commit()
                        
                    except Exception as e:
                        print(f"Failed to send scheduled message {msg[0]}: {e}")
                        
        except Exception as e:
            print(f"Error in scheduled message check: {e}")

    @check_scheduled_messages.before_loop
    async def before_check_scheduled_messages(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="list-scheduled",
        description="List all scheduled messages for this server"
    )
    async def list_scheduled(self, interaction: discord.Interaction):
        """List scheduled messages for this server"""
        async with aiosqlite.connect('AetherX.db') as db:
            async with db.execute(
                'SELECT * FROM scheduled_messages WHERE guild_id = ? ORDER BY scheduled_time',
                (interaction.guild_id,)
            ) as cursor:
                scheduled_messages = await cursor.fetchall()

        if not scheduled_messages:
            await interaction.response.send_message("No scheduled messages for this server.", ephemeral=True)
            return

        embed = discord.Embed(title="📅 Scheduled Messages", color=0x00ff00)
        
        for msg in scheduled_messages:
            channel = self.bot.get_channel(msg[2])
            scheduled_time = datetime.fromisoformat(msg[4])
            local_time = scheduled_time.astimezone(pytz.timezone(msg[5]))
            time_str = local_time.strftime('%Y-%m-%d %H:%M %Z')
            
            preview = msg[3][:50] + "..." if len(msg[3]) > 50 else msg[3]
            channel_mention = channel.mention if channel else "Unknown Channel"
            
            embed.add_field(
                name=f"ID: {msg[0]} | {time_str}",
                value=f"Channel: {channel_mention}\nPreview: {preview}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="cancel-scheduled",
        description="Cancel a scheduled message"
    )
    @app_commands.describe(message_id="The ID of the message to cancel")
    async def cancel_scheduled(self, interaction: discord.Interaction, message_id: int):
        """Cancel a scheduled message"""
        async with aiosqlite.connect('AetherX.db') as db:
            async with db.execute(
                'SELECT * FROM scheduled_messages WHERE id = ? AND guild_id = ?',
                (message_id, interaction.guild_id)
            ) as cursor:
                message = await cursor.fetchone()

            if not message:
                await interaction.response.send_message(
                    "❌ No scheduled message found with that ID in this server.",
                    ephemeral=True
                )
                return

            await db.execute('DELETE FROM scheduled_messages WHERE id = ?', (message_id,))
            await db.commit()

        await interaction.response.send_message(
            "✅ Scheduled message cancelled successfully.",
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(ScheduleCog(bot))