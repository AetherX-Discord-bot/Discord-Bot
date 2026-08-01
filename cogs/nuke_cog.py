import discord
from discord.ext import commands
import asyncio
from typing import Optional

class NukeView(discord.ui.View):
    """View for nuke confirmation"""
    
    def __init__(self, ctx, cog, reason, timeout=30):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.cog = cog
        self.reason = reason
        self.value = None
        self.message: Optional[discord.Message] = None
        
    @discord.ui.button(label="🚀 NUKE IT", style=discord.ButtonStyle.danger, emoji="💥")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm nuke button"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You are not authorized to confirm this nuke!", ephemeral=True)
            return
            
        self.value = True
        self.stop()
        
        # Disable all buttons
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        
        await interaction.response.edit_message(view=self)
        await self.cog.execute_nuke(self.ctx, self.reason)
    
    @discord.ui.button(label="✖ CANCEL", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel nuke button"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You are not authorized to cancel this nuke!", ephemeral=True)
            return
            
        self.value = False
        self.stop()
        
        # Disable all buttons
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        
        embed = discord.Embed(
            title="❌ **NUKE CANCELLED** ❌",
            description="Channel nuke has been cancelled.",
            color=0x2b2d31
        )
        embed.set_footer(text=f"Cancelled by {interaction.user}")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

class SoftNukeView(discord.ui.View):
    """View for soft nuke confirmation"""
    
    def __init__(self, ctx, cog, reason, timeout=30):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.cog = cog
        self.reason = reason
        self.value = None
        self.message: Optional[discord.Message] = None
        
    @discord.ui.button(label="🧹 CLEAR MESSAGES", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm soft nuke button"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You are not authorized to confirm this action!", ephemeral=True)
            return
            
        self.value = True
        self.stop()
        
        # Disable all buttons
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        
        await interaction.response.edit_message(view=self)
        await self.cog.execute_soft_nuke(self.ctx, self.reason)
    
    @discord.ui.button(label="✖ CANCEL", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel soft nuke button"""
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("You are not authorized to cancel this action!", ephemeral=True)
            return
            
        self.value = False
        self.stop()
        
        # Disable all buttons
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        
        embed = discord.Embed(
            title="❌ **OPERATION CANCELLED** ❌",
            description="Soft nuke has been cancelled.",
            color=0x2b2d31
        )
        embed.set_footer(text=f"Cancelled by {interaction.user}")
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        
        try:
            embed = discord.Embed(
                title="⏰ **CONFIRMATION TIMED OUT** ⏰",
                description="Confirmation timed out. Operation cancelled.",
                color=0x2b2d31
            )
            if self.message is not None:
                await self.message.edit(embed=embed, view=self)
        except:
            pass

class NukeCog(commands.Cog, name="Nuke"):
    """Channel nuking utilities for AetherX"""
    
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "💥"  # Emoji for the help command
        self.active_nukes = {}  # Track active nukes to prevent multiple
        
    async def execute_nuke(self, ctx, reason):
        """Execute the nuke after confirmation"""
        channel_id = ctx.channel.id
        if channel_id in self.active_nukes:
            return
        
        self.active_nukes[channel_id] = True
        
        try:
            # AetherX-style embed colors
            EMBED_COLOR = 0x2b2d31  # Discord dark theme color
            
            # Send countdown embed
            embed = discord.Embed(
                title="🚀 **NUKE COUNTDOWN** 🚀",
                description=f"**Channel:** {ctx.channel.mention}\n**By:** {ctx.author.mention}\n\n```yaml\nWARNING: Channel will be nuked in 5 seconds...\n```",
                color=EMBED_COLOR
            )
            embed.set_footer(text=f"AetherX • Channel ID: {ctx.channel.id}")
            
            countdown_msg = await ctx.send(embed=embed)
            
            # Countdown
            for i in range(5, 0, -1):
                await asyncio.sleep(1)
                embed.description = f"**Channel:** {ctx.channel.mention}\n**By:** {ctx.author.mention}\n\n```yaml\nWARNING: Channel will be nuked in {i} seconds...\n```"
                await countdown_msg.edit(embed=embed)
            
            # Store channel properties
            channel = ctx.channel
            properties = {
                'name': channel.name,
                'position': channel.position,
                'category': channel.category,
                'overwrites': channel.overwrites,
                'slowmode_delay': channel.slowmode_delay,
                'nsfw': getattr(channel, 'nsfw', False),
                'topic': getattr(channel, 'topic', None),
                'reason': f"Nuked by {ctx.author} ({ctx.author.id}): {reason}"
            }
            
            # Handle different channel types
            if isinstance(channel, discord.TextChannel):
                properties['type'] = 'text'
            elif isinstance(channel, discord.VoiceChannel):
                properties['type'] = 'voice'
                properties['bitrate'] = channel.bitrate
                properties['user_limit'] = channel.user_limit
            elif isinstance(channel, discord.StageChannel):
                properties['type'] = 'stage'
            elif isinstance(channel, discord.CategoryChannel):
                await ctx.send("❌ Cannot nuke category channels!")
                return
            else:
                properties['type'] = 'text'
            
            # Delete the channel
            await channel.delete(reason=properties['reason'])
            
            # Recreate based on type
            new_channel = None
            if properties['type'] == 'text':
                new_channel = await ctx.guild.create_text_channel(
                    name=properties['name'],
                    category=properties['category'],
                    position=properties['position'],
                    topic=properties['topic'],
                    nsfw=properties['nsfw'],
                    slowmode_delay=properties['slowmode_delay'],
                    overwrites=properties['overwrites'],
                    reason=f"Recreated after nuke • {properties['reason']}"
                )
            elif properties['type'] == 'voice':
                new_channel = await ctx.guild.create_voice_channel(
                    name=properties['name'],
                    category=properties['category'],
                    position=properties['position'],
                    bitrate=properties['bitrate'],
                    user_limit=properties['user_limit'],
                    overwrites=properties['overwrites'],
                    reason=f"Recreated after nuke • {properties['reason']}"
                )
            elif properties['type'] == 'stage':
                new_channel = await ctx.guild.create_stage_channel(
                    name=properties['name'],
                    category=properties['category'],
                    position=properties['position'],
                    overwrites=properties['overwrites'],
                    reason=f"Recreated after nuke • {properties['reason']}"
                )
            else:
                return
            
            # Send success embed in new channel
            success_embed = discord.Embed(
                title="💥 **CHANNEL NUKED** 💥",
                description=(
                    f"**This channel has been successfully nuked!**\n\n"
                    f"**Responsible Moderator:** {ctx.author.mention}\n"
                    f"**User ID:** `{ctx.author.id}`\n"
                    f"**Reason:** `{reason}`\n\n"
                    f"*All previous messages have been cleared.*"
                ),
                color=EMBED_COLOR
            )
            success_embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            success_embed.set_footer(text="AetherX • Channel Recreation Complete")
            success_embed.timestamp = discord.utils.utcnow()
            
            await new_channel.send(embed=success_embed)
            
            # Log to audit log if available
            await self.log_nuke(ctx, properties, new_channel, reason)
            
        except Exception as e:
            # If something goes wrong, notify in DMs
            try:
                error_embed = discord.Embed(
                    title="❌ Nuke Failed",
                    description=f"An error occurred while nuking the channel:\n```{e}```",
                    color=0xe74c3c
                )
                await ctx.author.send(embed=error_embed)
            except:
                pass  # Can't even DM the user
        finally:
            # Clean up active nukes tracking
            if channel_id in self.active_nukes:
                del self.active_nukes[channel_id]
    
    async def execute_soft_nuke(self, ctx, reason):
        """Execute soft nuke after confirmation"""
        try:
            EMBED_COLOR = 0x2b2d31
            
            # Start purging
            embed = discord.Embed(
                title="🧹 **CLEANING CHANNEL** 🧹",
                description="Deleting all messages... This may take a while.",
                color=EMBED_COLOR
            )
            status_msg = await ctx.send(embed=embed)
            
            # Purge messages (excluding pins and our status message)
            def not_pinned_or_status(m):
                return not m.pinned and m.id != status_msg.id
            
            deleted = await ctx.channel.purge(
                limit=None, 
                check=not_pinned_or_status, 
                reason=f"Soft nuke by {ctx.author}: {reason}"
            )
            
            # Send completion message
            embed = discord.Embed(
                title="✅ **CHANNEL CLEARED** ✅",
                description=(
                    f"**Deleted:** `{len(deleted)}` messages\n"
                    f"**Moderator:** {ctx.author.mention}\n"
                    f"**Reason:** `{reason}`\n\n"
                    f"*Pinned messages were preserved.*"
                ),
                color=0x2ecc71
            )
            embed.set_footer(text="AetherX • Soft Nuke Complete")
            embed.timestamp = discord.utils.utcnow()
            
            await status_msg.edit(embed=embed)
            
            # Log soft nuke
            await self.log_soft_nuke(ctx, len(deleted), reason)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Soft Nuke Failed",
                description=f"An error occurred:\n```{e}```",
                color=0xe74c3c
            )
            await ctx.send(embed=embed, delete_after=10)
    
    async def log_nuke(self, ctx, properties, new_channel, reason):
        """Log nuke action to audit channel"""
        log_channel = discord.utils.get(ctx.guild.text_channels, name="audit-log") or \
                     discord.utils.get(ctx.guild.text_channels, name="mod-log") or \
                     discord.utils.get(ctx.guild.text_channels, name="logs")
        
        if log_channel:
            try:
                log_embed = discord.Embed(
                    title="📝 **CHANNEL NUKED** 📝",
                    description=(
                        f"**Channel:** `#{properties['name']}`\n"
                        f"**Type:** `{properties['type'].upper()}`\n"
                        f"**Moderator:** {ctx.author.mention}\n"
                        f"**Moderator ID:** `{ctx.author.id}`\n"
                        f"**Reason:** `{reason}`\n"
                        f"**New Channel:** {new_channel.mention}"
                    ),
                    color=0xe74c3c  # Red for destructive actions
                )
                log_embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
                log_embed.set_footer(text=f"Channel ID: {new_channel.id}")
                log_embed.timestamp = discord.utils.utcnow()
                
                await log_channel.send(embed=log_embed)
            except:
                pass
    
    async def log_soft_nuke(self, ctx, message_count, reason):
        """Log soft nuke action to audit channel"""
        log_channel = discord.utils.get(ctx.guild.text_channels, name="audit-log") or \
                     discord.utils.get(ctx.guild.text_channels, name="mod-log") or \
                     discord.utils.get(ctx.guild.text_channels, name="logs")
        
        if log_channel:
            try:
                log_embed = discord.Embed(
                    title="🧹 **CHANNEL CLEARED** 🧹",
                    description=(
                        f"**Channel:** {ctx.channel.mention}\n"
                        f"**Messages Deleted:** `{message_count}`\n"
                        f"**Moderator:** {ctx.author.mention}\n"
                        f"**Moderator ID:** `{ctx.author.id}`\n"
                        f"**Reason:** `{reason}`"
                    ),
                    color=0xf39c12  # Orange for warning actions
                )
                log_embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
                log_embed.set_footer(text=f"Channel ID: {ctx.channel.id}")
                log_embed.timestamp = discord.utils.utcnow()
                
                await log_channel.send(embed=log_embed)
            except:
                pass
    
    @commands.command(
        name="nuke",
        aliases=["purgechannel", "resetchannel"],
        brief="Nuke a channel (delete and recreate)",
        help=(
            "Deletes the current channel and recreates it with the same name and permissions.\n"
            "**Requires confirmation via buttons.**\n"
            "**Requires:** Administrator permission"
        )
    )
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)  # 30 second cooldown per guild
    async def nuke_channel(self, ctx, *, reason: Optional[str] = "No reason provided"):
        """Nukes the current channel with button confirmation"""
        
        # Prevent multiple nukes on same channel
        if ctx.channel.id in self.active_nukes:
            embed = discord.Embed(
                title="⚠️ **NUKE IN PROGRESS** ⚠️",
                description="A nuke is already in progress for this channel. Please wait.",
                color=0x2b2d31
            )
            await ctx.send(embed=embed, delete_after=10)
            return
        
        # AetherX-style embed
        EMBED_COLOR = 0x2b2d31
        
        embed = discord.Embed(
            title="⚠️ **NUKE CONFIRMATION** ⚠️",
            description=(
                f"**WARNING: This will DELETE and RECREATE this channel!**\n\n"
                f"**Channel:** {ctx.channel.mention}\n"
                f"**Initiator:** {ctx.author.mention}\n"
                f"**Reason:** `{reason}`\n\n"
                f"**⚠️ ALL MESSAGES WILL BE LOST ⚠️**\n"
                f"*This action cannot be undone!*\n\n"
                f"**Please confirm your action below:**"
            ),
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url="https://i.imgur.com/cj2KuzF.png")  # Warning icon
        embed.set_footer(text="AetherX • This action requires confirmation")
        embed.timestamp = discord.utils.utcnow()
        
        # Create and send view
        view = NukeView(ctx, self, reason)
        view.message = await ctx.send(embed=embed, view=view)
    
    @commands.command(
        name="softnuke",
        aliases=["clearchannel", "empty"],
        brief="Soft nuke (just delete messages)",
        help=(
            "Deletes all messages in the current channel without recreating it.\n"
            "**Requires confirmation via buttons.**\n"
            "**Requires:** Manage Messages permission"
        )
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def soft_nuke(self, ctx, *, reason: Optional[str] = "No reason provided"):
        """Soft nuke - delete all messages in channel with button confirmation"""
        
        EMBED_COLOR = 0x2b2d31
        
        embed = discord.Embed(
            title="⚠️ **SOFT NUKE CONFIRMATION** ⚠️",
            description=(
                f"**This will delete ALL non-pinned messages in {ctx.channel.mention}!**\n\n"
                f"**Initiator:** {ctx.author.mention}\n"
                f"**Reason:** `{reason}`\n\n"
                f"**Estimated messages to delete:** `{len(await ctx.channel.history(limit=None).flatten())}`\n\n"
                f"**Pinned messages will be preserved.**\n"
                f"*This action cannot be undone!*\n\n"
                f"**Please confirm your action below:**"
            ),
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url="https://i.imgur.com/3JvQ2Zz.png")  # Clean icon
        embed.set_footer(text="AetherX • This action requires confirmation")
        embed.timestamp = discord.utils.utcnow()
        
        # Create and send view
        view = SoftNukeView(ctx, self, reason)
        view.message = await ctx.send(embed=embed, view=view)
    
    @nuke_channel.error
    async def nuke_error(self, ctx, error):
        """Error handler for nuke command"""
        EMBED_COLOR = 0x2b2d31
        
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need **Administrator** permissions to use this command!",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            embed = discord.Embed(
                title="❌ Bot Missing Permissions",
                description=f"I need the following permissions:\n```{', '.join(missing)}```",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Command on Cooldown",
                description=f"Please wait `{error.retry_after:.1f}` seconds before nuking again.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=error.retry_after)
        
        elif isinstance(error, commands.CommandInvokeError):
            embed = discord.Embed(
                title="⚠️ Unexpected Error",
                description="An unexpected error occurred. Please try again later.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=10)
    
    @soft_nuke.error
    async def soft_nuke_error(self, ctx, error):
        """Error handler for soft nuke command"""
        EMBED_COLOR = 0x2b2d31
        
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need **Manage Messages** permissions to use this command!",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            embed = discord.Embed(
                title="❌ Bot Missing Permissions",
                description=f"I need the following permissions:\n```{', '.join(missing)}```",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Command on Cooldown",
                description=f"Please wait `{error.retry_after:.1f}` seconds before using this command again.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=error.retry_after)

async def setup(bot):
    """Load the Nuke cog"""
    await bot.add_cog(NukeCog(bot))