import discord
from discord.ext import commands
from datetime import datetime
import json
import os
import asyncio
import sys


class DevToolsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_ids = {435125886996709377, 811016330517676073}
        self.notify = {435125886996709377, 811016330517676073}
        self.log_config = {}  # {guild_id: channel_id}
        self.load_config()
        self.restart_data = {}
        # Track if restart notification has been sent
        self._restart_completed = False

    def load_config(self):
        if os.path.exists("log_config.json"):
            with open("log_config.json", "r") as f:
                self.log_config = json.load(f)

    def save_config(self):
        with open("log_config.json", "w") as f:
            json.dump(self.log_config, f)

    async def send_to_all_log_channels(self, message, author):
        """Sends note to ALL configured server channels"""
        for guild_id, channel_id in self.log_config.items():
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                embed = discord.Embed(
                    title="Dev Note",
                    description=message,
                    color=0x5865F2,
                    timestamp=datetime.utcnow()
                )
                embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
                
                # Add server info if not from DM
                if isinstance(author, discord.User):  # DM context
                    embed.set_footer(text="Submitted via DM")
                else:
                    embed.set_footer(text=f"Server: {author.guild.name} ({guild_id})")
                
                await channel.send(embed=embed)

    @commands.command(name="note")
    async def dev_note(self, ctx, *, message: str):
        """Log developer notes (Works in servers/DMs)"""
        if ctx.author.id not in self.allowed_ids:
            return await ctx.send("❌ Developer-only command!", ephemeral=True)

        # Always log to file
        log_source = "DM" if isinstance(ctx.channel, discord.DMChannel) else f"{ctx.guild.name} ({ctx.guild.id})"
        with open("Devlog.txt", "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] {ctx.author} (From: {log_source}): {message}\n")

        # Send to all configured server channels
        await self.send_to_all_log_channels(message, ctx.author)
        
        await ctx.send("📝 Note logged to ALL dev channels!", ephemeral=True)

    @commands.command(name="setlog")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Set the dev log channel for this server (Admin only)"""
        self.log_config[str(ctx.guild.id)] = channel.id
        self.save_config()
        await ctx.send(f"🔧 Dev logs will now go to {channel.mention} in this server")

    @commands.command(name="removelog")
    @commands.has_permissions(administrator=True)
    async def remove_log_channel(self, ctx):
        """Remove the dev log channel for this server (Admin only)"""
        if str(ctx.guild.id) in self.log_config:
            del self.log_config[str(ctx.guild.id)]
            self.save_config()
            await ctx.send("🔧 Dev logging disabled for this server")
        else:
            await ctx.send("ℹ️ No log channel was set for this server")
    
    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_commands(self, ctx):
        """Sync application commands globally (Owner Only)"""
        try:
            # Sync slash commands (modern approach)
            if hasattr(self.bot, 'tree'):
                await self.bot.tree.sync()
                msg = "✅ Slash commands synced globally!"
            
            # Fallback for prefix commands (legacy)
            else:
                synced = await self.bot.sync_commands()
                msg = f"✅ Synced {len(synced)} commands!"
            
            await ctx.send(msg)
        
        except Exception as e:
            await ctx.send(f"❌ Sync failed: {type(e).__name__}: {e}")

    @commands.command(name='restart')
    async def restart(self, ctx, *, reason: str = "No reason provided"):
        """Restart the bot"""
        if ctx.author.id not in self.allowed_ids:
            await ctx.send("❌ You don't have permission to use this command!")
            return

        # Store restart info in a file to persist across restarts
        restart_info = {
            'reason': reason,
            'initiator_id': ctx.author.id,
            'initiator_name': str(ctx.author),
            'time': datetime.now().isoformat()
        }
        
        # Save restart info to a file
        with open("restart_info.json", "w") as f:
            json.dump(restart_info, f)

        # DM all specified users about the restart
        for user_id in self.notify:
            try:
                user = await self.bot.fetch_user(user_id)
                time = datetime.now().strftime('%Y-%m-%d %H:%M:%S Local Time (bot hosted in EST)')
                dmembed = discord.Embed(
                    title="🔴 Restart Initiated",
                    description="AetherX's Restart command used"
                )
                dmembed.add_field(name="Initiator", value=ctx.author.mention, inline=False)
                dmembed.add_field(name="Time", value=time, inline=True)
                dmembed.add_field(name="Reason", value=reason, inline=True)
                dmembed.add_field(name="Status", value="Restarting...", inline=False)
                await user.send(embed=dmembed)
            except Exception as e:
                print(f"Couldn't DM {user_id}: {e}")

        # Confirm in channel
        embed = discord.Embed(
            title="🔄 Restarting...",
            description=f"Bot will reboot with PID {os.getpid()}",
            color=0xFFA500
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)

        # Graceful restart
        try:
            await asyncio.sleep(2)  # Give time for messages to send
            os.execv(sys.executable, ['python'] + sys.argv)
        except Exception as e:
            err_msg = f"❌ Restart failed: {type(e).__name__}: {e}"
            await ctx.send(err_msg)
            for user_id in self.notify:
                try:
                    user = await self.bot.fetch_user(user_id)
                    await user.send(err_msg)
                except Exception as ex:
                    print(f"Couldn't DM {user_id}: {ex}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Send DMs to all allowed users when bot comes online after restart"""
        # Only run once per restart
        if self._restart_completed:
            return
            
        # Check if restart_info file exists
        if os.path.exists("restart_info.json"):
            try:
                with open("restart_info.json", "r") as f:
                    restart_info = json.load(f)
                
                # Send DMs to ALL allowed users (not just notify group)
                for user_id in self.allowed_ids:
                    try:
                        user = await self.bot.fetch_user(user_id)
                        
                        # Create restart completion embed
                        embed = discord.Embed(
                            title="✅ Bot Online",
                            description="The bot has successfully restarted and is now online.",
                            color=0x00FF00,
                            timestamp=datetime.utcnow()
                        )
                        
                        # Add restart details if available
                        if 'reason' in restart_info:
                            embed.add_field(
                                name="Restart Reason",
                                value=restart_info['reason'],
                                inline=False
                            )
                        
                        if 'initiator_name' in restart_info:
                            embed.add_field(
                                name="Restart Initiated By",
                                value=restart_info['initiator_name'],
                                inline=True
                            )
                        
                        if 'time' in restart_info:
                            restart_time = datetime.fromisoformat(restart_info['time'])
                            embed.add_field(
                                name="Restart Time",
                                value=restart_time.strftime('%Y-%m-%d %H:%M:%S EST'),
                                inline=True
                            )
                        
                        embed.add_field(
                            name="Current Status",
                            value=f"✅ Online and ready\nLatency: {round(self.bot.latency * 1000)}ms",
                            inline=False
                        )
                        
                        embed.set_footer(text="Automated restart notification")
                        
                        await user.send(embed=embed)
                        print(f"Sent restart notification to {user_id}")
                        
                    except discord.Forbidden:
                        print(f"Could not DM user {user_id} (DMs closed or blocked)")
                    except discord.NotFound:
                        print(f"User {user_id} not found")
                    except Exception as e:
                        print(f"Error sending DM to {user_id}: {e}")
                
                # Clean up the restart info file
                os.remove("restart_info.json")
                
            except json.JSONDecodeError:
                print("Error reading restart_info.json - invalid format")
            except Exception as e:
                print(f"Error processing restart notification: {e}")
        
        # Mark as completed
        self._restart_completed = True
        
        # Also log to console
        print(f"✅ {self.bot.user} is online and ready!")

async def setup(bot):
    await bot.add_cog(DevToolsCog(bot))