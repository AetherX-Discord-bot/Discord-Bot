import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import asyncio
from typing import Optional
import json

class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'AetherX.db'
        self._initialize_db()
        
        self.temp_channels = {}
        self._pending_deletions = set()  
        
    def _initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
    
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tempvoice_setups (
                    guild_id TEXT PRIMARY KEY,
                    creator_channel_id TEXT,
                    category_id TEXT,
                    staff_role_id TEXT,
                    user_id TEXT,
                    tmpvcsettings TEXT
                )
            """)

            conn.commit()

    async def _update_tmpvc_permissions(self, channel):
        guild = channel.guild
        guild_id = str(guild.id)
        channel_id = str(channel.id)

        overwrites = channel.overwrites

        for target, perms in overwrites.items():
            if not isinstance(target, discord.Member):
                continue

            if target.id == guild.owner_id:
                continue

            has_explicit = perms.connect is not None or perms.view_channel is not None
            if not has_explicit:
                continue

            user_id_str = str(target.id)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT tmpvcsettings FROM tempvoice_setups WHERE user_id = ?",
                    (user_id_str,)
                )
                row = cursor.fetchone()

                if row and row[0]:
                    try:
                        db_data = json.loads(row[0])
                    except json.JSONDecodeError:
                        db_data = {}
                else:
                    db_data = {}

                if guild_id not in db_data:
                    db_data[guild_id] = {}

                old_value = db_data[guild_id].get(channel_id)
                new_value = True

                if old_value != new_value:
                    db_data[guild_id][channel_id] = new_value

                    cursor.execute(
                        "INSERT OR REPLACE INTO tempvoice_setups (user_id, tmpvcsettings) VALUES (?, ?)",
                        (user_id_str, json.dumps(db_data))
                    )
                    conn.commit()

    
    tempvoice = app_commands.Group(name="tempvoice", description="Temporary voice channel management")
    
    @tempvoice.command(name="setup", description="Setup a temporary voice channel system (Admin only)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def tempvoice_setup(
        self,
        interaction: discord.Interaction,
        creator_channel: discord.VoiceChannel,
        category: discord.CategoryChannel,
        staff_role: Optional[discord.Role] = None
    ):
        await interaction.response.defer(ephemeral=True)
        guild = getattr(interaction, "guild", None)
        if guild is None:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return
        guild_id_str = str(guild.id)
        if creator_channel is None or category is None:
            await interaction.followup.send(
                "Please provide a valid creator channel and category.",
                ephemeral=True
            )
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT guild_id FROM tempvoice_setups WHERE guild_id = ?",
                (guild_id_str,)
            )
            existing = cursor.fetchone() is not None
            if existing:
                cursor.execute(
                    """
                    UPDATE tempvoice_setups
                    SET creator_channel_id = ?, category_id = ?, staff_role_id = ?
                    WHERE guild_id = ?
                    """,
                    (
                        str(creator_channel.id),
                        str(category.id),
                        str(staff_role.id) if staff_role else None,
                        guild_id_str,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO tempvoice_setups (guild_id, creator_channel_id, category_id, staff_role_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        guild_id_str,
                        str(creator_channel.id),
                        str(category.id),
                        str(staff_role.id) if staff_role else None,
                    ),
                )

            conn.commit()

        embed = discord.Embed(
            title="✅ Temporary Voice System Setup Complete",
            description=(
                f"**Creator Channel:** {creator_channel.mention}\n"
                f"**Category:** {category.mention}\n"
                f"tempvoice_setups can now join {creator_channel.mention} to create their own temporary voice channel!\n"
                f"*Note: New channels will be open for anyone to join by default.*"
            ),
            color=discord.Color.green(),
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @tempvoice.command(name="disable", description="Disable temporary voice channel system (Admin only)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def tempvoice_disable(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild_id = str(interaction.guild_id)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT creator_channel_id FROM tempvoice_setups WHERE guild_id = ?",
                (guild_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                embed = discord.Embed(
                    title="❌ Temporary Voice System Not Found",
                    description="The temporary voice system is not currently set up for this server.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            cursor.execute(
                "DELETE FROM tempvoice_setups WHERE guild_id = ?",
                (guild_id,)
            )
            conn.commit()
        

        deleted_channels = 0
        
        if guild_id in self.temp_channels:
            temp_channel_ids = list(self.temp_channels[guild_id].keys())
            
            for temp_channel_id in temp_channel_ids:
                try:
                    channel = self.bot.get_channel(int(temp_channel_id))
                    if channel and isinstance(channel, discord.VoiceChannel):
                        await channel.delete(reason="Temp voice system disabled")
                        deleted_channels += 1
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(f"Error deleting channel {temp_channel_id}: {e}")
            
            try:
                del self.temp_channels[guild_id]
            except KeyError:
                pass
        

        guild = getattr(interaction, "guild", None)
        channels_to_delete = []
        for g_id, channels in list(self.temp_channels.items()):
            for ch_id in list(channels.keys()):
                try:
                    channel = self.bot.get_channel(int(ch_id))
                    if channel and guild is not None and channel.guild.id == guild.id:
                        channels_to_delete.append((g_id, ch_id))
                except:
                    pass
        
        for g_id, ch_id in channels_to_delete:
            if g_id in self.temp_channels and ch_id in self.temp_channels[g_id]:
                del self.temp_channels[g_id][ch_id]
            if g_id in self.temp_channels and not self.temp_channels[g_id]:
                del self.temp_channels[g_id]
        
        embed = discord.Embed(
            title="✅ Temporary Voice System Disabled",
            description=f"System disabled and {deleted_channels} temporary voice channels were cleaned up.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @tempvoice.command(name="status", description="Check temporary voice system status")
    async def tempvoice_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = getattr(interaction, "guild", None)
        if guild is None:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return
        guild_id_str = str(guild.id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT creator_channel_id, category_id, staff_role_id FROM tempvoice_setups WHERE guild_id = ?",
                (guild_id_str,)
            )
            result = cursor.fetchone()
        
        if not result:
            active_channels = len(self.temp_channels.get(guild_id_str, {}))
            
            if active_channels > 0:
                embed = discord.Embed(
                    title="⚠️ Temporary Voice System Partially Disabled",
                    description=(
                        "System is disabled but there are still active temporary channels.\n"
                        f"Active channels: {active_channels}\n"
                        "Run `/tempvoice disable` again to clean them up."
                    ),
                    color=discord.Color.orange()
                )
            else:
                embed = discord.Embed(
                    title="❌ Temporary Voice System Not Setup",
                    description="Use `/tempvoice setup` to configure the system.",
                    color=discord.Color.red()
                )
        else:
            creator_channel_id, category_id, staff_role_id = result
            
            guild = interaction.guild
            if not guild:
                embed = discord.Embed(
                    title="⚠️ Temporary Voice System Configuration Error",
                    description="Could not access guild information from the interaction.",
                    color=discord.Color.orange()
                )
            else:
                creator_channel = guild.get_channel(int(creator_channel_id)) if creator_channel_id else None
                category = guild.get_channel(int(category_id)) if category_id else None
                staff_role = guild.get_role(int(staff_role_id)) if staff_role_id else None

                active_channels = len(self.temp_channels.get(guild_id_str, {}))

                embed = discord.Embed(
                    title="✅ Temporary Voice System Active",
                    color=discord.Color.green()
                )
                embed.add_field(name="Creator Channel", value=creator_channel.mention if creator_channel else "Not found", inline=True)
                embed.add_field(name="Category", value=category.mention if category else "Not found", inline=True)
                embed.add_field(name="Staff Role", value=staff_role.mention if staff_role else "Not set", inline=True)
                embed.add_field(name="Active Channels", value=str(active_channels), inline=True)
                embed.add_field(name="Default Permissions", value="Open to all members", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT creator_channel_id, category_id, staff_role_id FROM tempvoice_setups WHERE guild_id = ?",
                (str(member.guild.id),)
            )
            result = cursor.fetchone()
        
        if not result:
            return
        
        creator_channel_id, category_id, staff_role_id = result
        
        if after.channel and str(after.channel.id) == creator_channel_id:
            await self.create_temp_channel(member, after.channel, category_id, staff_role_id)

        if before.channel and self.is_temp_channel(member.guild.id, before.channel.id):
            await self.check_temp_channel_empty(before.channel)
        
        if before.channel and self.is_temp_channel(member.guild.id, before.channel.id):
            guild_id_str = str(member.guild.id)
            channel_id_str = str(before.channel.id)
            if guild_id_str in self.temp_channels and channel_id_str in self.temp_channels[guild_id_str]:
                if self.temp_channels[guild_id_str][channel_id_str] == str(member.id):
                    await asyncio.sleep(1)
                    channel = member.guild.get_channel(before.channel.id)
                    if channel:
                        remaining_members = [m for m in channel.members if not m.bot]
                        if remaining_members:
                            new_owner = remaining_members[0]
                            self.temp_channels[guild_id_str][channel_id_str] = str(new_owner.id)
    
    async def create_temp_channel(self, member, creator_channel, category_id, staff_role_id):
        guild = member.guild
        guild_id = str(guild.id)
        category = guild.get_channel(int(category_id))

        if not category:
            return

        channel_name = f"{member.display_name}'s Room"
        

        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    connect=True,
                    view_channel=True,
                    speak=True
                ),
                member: discord.PermissionOverwrite(
                    manage_channels=True,
                    mute_members=True,
                    deafen_members=True,
                    move_members=True
                )
            }

            if staff_role_id:
                staff_role = guild.get_role(int(staff_role_id))
                if staff_role:
                    overwrites[staff_role] = discord.PermissionOverwrite(
                        manage_channels=True,
                        mute_members=True,
                        deafen_members=True,
                        move_members=True
                    )

            overwrites[guild.me] = discord.PermissionOverwrite(
                connect=True,
                view_channel=True,
                manage_channels=True,
                manage_roles=True
            )

            temp_channel = await category.create_voice_channel(
                name=channel_name,
                overwrites=overwrites,
                reason=f"Temporary voice channel for {member}"
            )
            
            await member.move_to(temp_channel)
            
            if guild_id not in self.temp_channels:
                self.temp_channels[guild_id] = {}
            self.temp_channels[guild_id][str(temp_channel.id)] = str(member.id)

            user_id_str = str(member.id)

            if member.id != guild.owner_id:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()

                    cursor.execute(
                        "SELECT tmpvcsettings FROM tempvoice_setups WHERE user_id = ?",
                        (user_id_str,)
                    )
                    row = cursor.fetchone()

                    if row and row[0]:
                        try:
                            db_data = json.loads(row[0])
                        except json.JSONDecodeError:
                            db_data = {}
                    else:
                        db_data = {}

                    if guild_id not in db_data:
                        db_data[guild_id] = {}

                    db_data[guild_id][str(temp_channel.id)] = True

                    cursor.execute(
                        "INSERT OR REPLACE INTO tempvoice_setups (user_id, tmpvcsettings) VALUES (?, ?)",
                        (user_id_str, json.dumps(db_data))
                    )
                    conn.commit()

        except Exception as e:
            print(f"Error creating temp channel: {e}")

    
    async def update_channel_permissions(self, channel, owner, old_owner=None):
        guild = channel.guild
        guild_id = str(guild.id)
        channel_id = str(channel.id)

        def save_user_settings(user):
            if user is None:
                return
            if user.id == guild.owner_id:
                return

            user_id_str = str(user.id)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT tmpvcsettings FROM tempvoice_setups WHERE user_id = ?",
                    (user_id_str,)
                )
                row = cursor.fetchone()

                if row and row[0]:
                    try:
                        db_data = json.loads(row[0])
                    except json.JSONDecodeError:
                        db_data = {}
                else:
                    db_data = {}

                if guild_id not in db_data:
                    db_data[guild_id] = {}

                old_value = db_data[guild_id].get(channel_id)
                new_value = True

                if old_value != new_value:
                    db_data[guild_id][channel_id] = new_value

                    cursor.execute(
                        "INSERT OR REPLACE INTO tempvoice_setups (user_id, tmpvcsettings) VALUES (?, ?)",
                        (user_id_str, json.dumps(db_data))
                    )
                    conn.commit()

        try:
            save_user_settings(old_owner)
            save_user_settings(owner)

            await channel.set_permissions(
                owner,
                manage_channels=True,
                mute_members=True,
                deafen_members=True,
                move_members=True
            )

        except Exception as e:
            print(f"Error updating channel permissions: {e}")

    
    def is_temp_channel(self, guild_id, channel_id):
        guild_id_str = str(guild_id)
        channel_id_str = str(channel_id)
        return (guild_id_str in self.temp_channels and 
                channel_id_str in self.temp_channels[guild_id_str])
    
    async def check_temp_channel_empty(self, channel):
        channel_id_str = str(channel.id)
        if channel_id_str in self._pending_deletions:
            return
        
        self._pending_deletions.add(channel_id_str)
        
        try:
            await asyncio.sleep(2)
            
            fresh_channel = channel.guild.get_channel(channel.id)
            if not fresh_channel:
                return
            
            guild_id_str = str(channel.guild.id)
            if (guild_id_str not in self.temp_channels or 
                channel_id_str not in self.temp_channels[guild_id_str]):
                return
            
            human_members = [m for m in fresh_channel.members if not m.bot]
            
            if len(human_members) == 0:
                try:
                    await self._update_tmpvc_permissions(fresh_channel)
                    await fresh_channel.delete(reason="Temporary voice channel empty")
                    
                    if guild_id_str in self.temp_channels:
                        if channel_id_str in self.temp_channels[guild_id_str]:
                            del self.temp_channels[guild_id_str][channel_id_str]
                        if not self.temp_channels[guild_id_str]:
                            del self.temp_channels[guild_id_str]
                            
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(f"Error deleting temp channel {channel_id_str}: {e}")
        finally:
            self._pending_deletions.discard(channel_id_str)
            
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if isinstance(channel, discord.VoiceChannel):
            guild_id_str = str(channel.guild.id)
            channel_id_str = str(channel.id)
            if (guild_id_str in self.temp_channels and 
                channel_id_str in self.temp_channels[guild_id_str]):
                del self.temp_channels[guild_id_str][channel_id_str]
                if not self.temp_channels[guild_id_str]:
                    try:
                        del self.temp_channels[guild_id_str]
                    except KeyError:
                        pass

async def setup(bot):
    await bot.add_cog(TempVoice(bot))
    await bot.tree.sync()