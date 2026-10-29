import asyncio
import discord
from discord.ext import commands
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple
import json
from pathlib import Path

class CountingCog(commands.Cog, name="Counting Game"):
    """Channel counting minigame for AetherX"""
    
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🔢"
        self.embed_color = 0x2b2d31
        self.data_dir = Path("data/counting")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.channels_file = self.data_dir / "channels.json"
        self.stats_file = self.data_dir / "stats.json"
        self.rules_file = self.data_dir / "rules.json"
        
        self._initialize_data_files()
        
        self.active_channels: Dict[int, Dict] = {}
        self.user_cooldowns: Dict[Tuple[int, int], datetime] = {}
        self.load_active_channels()
    
    def _initialize_data_files(self) -> None:
        """Initialize JSON data files"""
        if not self.channels_file.exists():
            with open(self.channels_file, 'w') as f:
                json.dump({}, f)
        if not self.stats_file.exists():
            with open(self.stats_file, 'w') as f:
                json.dump({}, f)
        if not self.rules_file.exists():
            with open(self.rules_file, 'w') as f:
                json.dump({}, f)
    
    def load_active_channels(self) -> None:
        """Load active counting channels from JSON"""
        try:
            with open(self.channels_file, 'r') as f:
                channels_data = json.load(f)
            for channel_id_str, channel_data in channels_data.items():
                channel_id = int(channel_id_str)
                if channel_data.get('enabled', True):
                    self.active_channels[channel_id] = channel_data
        except (json.JSONDecodeError, FileNotFoundError):
            self.active_channels = {}
    
    def _save_channels(self, channels_dict: Dict) -> None:
        """Save channels data to JSON (expects dict with string keys)"""
        with open(self.channels_file, 'w') as f:
            json.dump(channels_dict, f, indent=2)
    
    def _save_stats(self, stats_data: Dict) -> None:
        with open(self.stats_file, 'w') as f:
            json.dump(stats_data, f, indent=2)
    
    def _save_rules(self, rules_data: Dict) -> None:
        with open(self.rules_file, 'w') as f:
            json.dump(rules_data, f, indent=2)
    
    def get_all_channels(self) -> Dict:
        """Get all channels data (int keys)"""
        try:
            with open(self.channels_file, 'r') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def get_all_stats(self) -> Dict:
        """Get all stats data (int keys)"""
        try:
            with open(self.stats_file, 'r') as f:
                data = json.load(f)
                result = {}
                for user_id_str, channels in data.items():
                    user_id = int(user_id_str)
                    result[user_id] = {}
                    for channel_id_str, stats in channels.items():
                        channel_id = int(channel_id_str)
                        result[user_id][channel_id] = stats
                return result
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    def get_all_rules(self) -> Dict:
        try:
            with open(self.rules_file, 'r') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    
    async def update_channel_data(self, channel_id: int, **kwargs) -> None:
        """Update counting channel data and save to file"""
        if not kwargs:
            return
        
        all_channels = self.get_all_channels()
        if channel_id not in all_channels:
            all_channels[channel_id] = {}
        
        all_channels[channel_id].update(kwargs)
        all_channels[channel_id]['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        channels_to_save = {str(k): v for k, v in all_channels.items()}
        self._save_channels(channels_to_save)
        
        if channel_id in self.active_channels:
            self.active_channels[channel_id].update(kwargs)
        elif kwargs.get('enabled', True):
            self.active_channels[channel_id] = all_channels[channel_id]
        elif channel_id in self.active_channels and not kwargs.get('enabled', True):
            del self.active_channels[channel_id]
    
    async def update_user_stats(self, user_id: int, channel_id: int, guild_id: int,
                               counts: int = 0, fails: int = 0, best_streak: int = 0) -> None:
        """Update user counting statistics"""
        all_stats = self.get_all_stats()
        
        if user_id not in all_stats:
            all_stats[user_id] = {}
        if channel_id not in all_stats[user_id]:
            all_stats[user_id][channel_id] = {
                'guild_id': guild_id,
                'counts': 0,
                'fails': 0,
                'best_streak': 0,
                'last_count_at': None
            }
        
        current_stats = all_stats[user_id][channel_id]
        current_stats['counts'] += counts
        current_stats['fails'] += fails
        current_stats['best_streak'] = max(current_stats['best_streak'], best_streak)
        current_stats['last_count_at'] = datetime.now(timezone.utc).isoformat()
        
        stats_to_save = {}
        for uid, channels in all_stats.items():
            stats_to_save[str(uid)] = {}
            for cid, stats in channels.items():
                stats_to_save[str(uid)][str(cid)] = stats
        
        self._save_stats(stats_to_save)
    
    @commands.group(
        name="counting",
        aliases=["count", "countinggame"],
        brief="Manage counting game",
        invoke_without_command=True
    )
    @commands.has_permissions(manage_channels=True)
    async def counting_group(self, ctx):
        """Counting game management command group"""
        await ctx.send_help(ctx.command)
    
    @counting_group.command(name="setup")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True)
    async def setup_counting(self, ctx, channel: Optional[discord.TextChannel] = None):
        """Setup counting game in a channel"""
        target_channel = channel or ctx.channel
        
        all_channels = self.get_all_channels()
        if target_channel.id in all_channels:
            embed = discord.Embed(
                title="⚠️ Channel Already Setup",
                description=f"Counting is already configured in {target_channel.mention}.",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        channel_data = {
            'guild_id': ctx.guild.id,
            'current_number': 0,
            'last_counter_id': None,
            'high_score': 0,
            'last_high_score_user_id': None,
            'fails': 0,
            'enabled': True,
            'allow_same_user': False,
            'countdown_mode': False,
            'allow_decimal': False,
            'reset_on_fail': True,
            'cooldown_seconds': 5,
            'webhook_url': None,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        all_channels[target_channel.id] = channel_data
        self._save_channels({str(k): v for k, v in all_channels.items()})

        self.active_channels[target_channel.id] = channel_data

        embed = discord.Embed(
            title="✅ Counting Game Setup Complete",
            description=(
                f"The counting game has been setup in {target_channel.mention}!\n\n"
                f"**How to play:**\n"
                f"1. Start counting from `1`\n"
                f"2. Each user must say the next number in sequence\n"
                f"3. Don't break the chain!\n\n"
                f"**Default Settings:**\n"
                f"• Cooldown: 5 seconds\n"
                f"• Reset on fail: Yes\n"
                f"• Allow same user: No\n\n"
                f"Use `!counting config` to customize settings."
            ),
            color=self.embed_color
        )
        embed.set_footer(text=f"Setup by {ctx.author}")
        
        await ctx.send(embed=embed)
        
        start_embed = discord.Embed(
            title="🔢 Counting Game Started!",
            description=(
                "**Rules:**\n"
                "1. Start counting from `1`\n"
                "2. Each user must say the next number\n"
                "3. Don't break the chain!\n"
                "4. 5-second cooldown between counts\n\n"
                "**Get ready to count!**\n"
                "First number: `1`"
            ),
            color=self.embed_color
        )
        start_embed.set_footer(text="Type '1' to start!")
        
        await target_channel.send(embed=start_embed)
    
    @counting_group.command(name="config")
    @commands.has_permissions(manage_channels=True)
    async def config_counting(self, ctx, setting: str = None, *, value: str = None):
        """Configure counting settings"""
        channel_id = ctx.channel.id
        if channel_id not in self.active_channels:
            embed = discord.Embed(
                title="❌ Channel Not Setup",
                description="This channel is not setup for counting. Use `!counting setup` first.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if not setting:
            channel_data = self.active_channels[channel_id]
            
            embed = discord.Embed(
                title="⚙️ Counting Configuration",
                description=f"Current settings for {ctx.channel.mention}",
                color=self.embed_color
            )
            
            embed.add_field(name="Current Number", value=f"`{channel_data['current_number']}`", inline=True)
            embed.add_field(name="High Score", value=f"`{channel_data['high_score']}`", inline=True)
            embed.add_field(name="Fails", value=f"`{channel_data['fails']}`", inline=True)
            embed.add_field(name="Cooldown", value=f"`{channel_data['cooldown_seconds']}s`", inline=True)
            embed.add_field(name="Same User", value=f"`{channel_data['allow_same_user']}`", inline=True)
            embed.add_field(name="Reset on Fail", value=f"`{channel_data['reset_on_fail']}`", inline=True)
            embed.add_field(name="Countdown Mode", value=f"`{channel_data['countdown_mode']}`", inline=True)
            embed.add_field(name="Allow Decimal", value=f"`{channel_data['allow_decimal']}`", inline=True)
            embed.add_field(name="Enabled", value=f"`{channel_data['enabled']}`", inline=True)
            
            if channel_data.get('webhook_url'):
                embed.add_field(name="Webhook", value="✅ Configured", inline=True)
            
            embed.set_footer(text="Use !counting config <setting> <value> to change")
            await ctx.send(embed=embed)
            return
        
        setting = setting.lower()
        valid_settings = {
            'cooldown': 'cooldown_seconds',
            'allow_same_user': 'allow_same_user',
            'reset_on_fail': 'reset_on_fail',
            'countdown_mode': 'countdown_mode',
            'allow_decimal': 'allow_decimal',
            'webhook': 'webhook_url',
            'enabled': 'enabled'
        }
        
        if setting not in valid_settings:
            embed = discord.Embed(
                title="❌ Invalid Setting",
                description=(
                    f"Invalid setting: `{setting}`\n\n"
                    "**Valid settings:**\n"
                    "• `cooldown <seconds>`\n"
                    "• `allow_same_user <true/false>`\n"
                    "• `reset_on_fail <true/false>`\n"
                    "• `countdown_mode <true/false>`\n"
                    "• `allow_decimal <true/false>`\n"
                    "• `webhook <url>`\n"
                    "• `enabled <true/false>`"
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if value is None:
            embed = discord.Embed(
                title="❌ Missing Value",
                description=f"Please provide a value for `{setting}`.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        db_setting = valid_settings[setting]
        new_value = None
        
        if setting == 'cooldown':
            try:
                new_value = int(value)
                if not 1 <= new_value <= 60:
                    raise ValueError
            except:
                embed = discord.Embed(
                    title="❌ Invalid Value",
                    description="Cooldown must be between 1 and 60 seconds.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
        
        elif setting == 'webhook':
            if value.lower() in ['none', 'remove']:
                new_value = None
            elif value.startswith('https://discord.com/api/webhooks/'):
                new_value = value
            else:
                embed = discord.Embed(
                    title="❌ Invalid Webhook URL",
                    description="Please provide a valid Discord webhook URL.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
        
        elif setting in ['allow_same_user', 'reset_on_fail', 'countdown_mode', 'allow_decimal', 'enabled']:
            if value.lower() in ['true', 'yes', 'on', 'enable', '1']:
                new_value = True
            elif value.lower() in ['false', 'no', 'off', 'disable', '0']:
                new_value = False
            else:
                embed = discord.Embed(
                    title="❌ Invalid Value",
                    description="Please use `true` or `false`.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
        
        await self.update_channel_data(channel_id, **{db_setting: new_value})
        
        embed = discord.Embed(
            title="✅ Setting Updated",
            description=f"**{setting.replace('_', ' ').title()}** set to `{new_value}`",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
    
    @counting_group.command(name="stats")
    async def counting_stats(self, ctx, user: Optional[discord.Member] = None):
        """View counting statistics"""
        target_user = user or ctx.author
        channel_id = ctx.channel.id
        
        all_stats = self.get_all_stats()
        user_stats = all_stats.get(target_user.id, {})
        channel_stats = user_stats.get(channel_id)
        
        embed = discord.Embed(
            title=f"📊 Counting Stats - {target_user.display_name}",
            color=self.embed_color,
            timestamp=discord.utils.utcnow()
        )
        
        if channel_stats:
            total_counts = channel_stats['counts']
            total_fails = channel_stats['fails']
            accuracy = (total_counts / (total_counts + total_fails)) * 100 if (total_counts + total_fails) > 0 else 0
            
            embed.add_field(
                name=f"📈 {ctx.channel.name}",
                value=(
                    f"**Counts:** `{total_counts}`\n"
                    f"**Fails:** `{total_fails}`\n"
                    f"**Accuracy:** `{accuracy:.1f}%`\n"
                    f"**Best Streak:** `{channel_stats['best_streak']}`"
                ),
                inline=True
            )
        
        server_counts = 0
        server_fails = 0
        server_best_streak = 0
        
        for cid, stats in user_stats.items():
            if stats.get('guild_id') == ctx.guild.id:
                server_counts += stats['counts']
                server_fails += stats['fails']
                server_best_streak = max(server_best_streak, stats['best_streak'])
        
        if server_counts > 0:
            total_attempts = server_counts + server_fails
            server_accuracy = (server_counts / total_attempts) * 100 if total_attempts > 0 else 0
            
            embed.add_field(
                name="🌐 Server Total",
                value=(
                    f"**Total Counts:** `{server_counts}`\n"
                    f"**Total Fails:** `{server_fails}`\n"
                    f"**Accuracy:** `{server_accuracy:.1f}%`\n"
                    f"**Best Streak:** `{server_best_streak}`"
                ),
                inline=True
            )
        
        if not channel_stats and server_counts == 0:
            embed.description = "No counting statistics available yet."
        
        if target_user.avatar:
            embed.set_thumbnail(url=target_user.avatar.url)
        elif target_user.default_avatar:
            embed.set_thumbnail(url=target_user.default_avatar.url)
        
        embed.set_footer(text="Keep counting!")
        await ctx.send(embed=embed)
    
    @counting_group.command(name="leaderboard", aliases=["lb", "top"])
    async def counting_leaderboard(self, ctx, scope: str = "channel"):
        """View counting leaderboard"""
        scope = scope.lower()
        all_stats = self.get_all_stats()
        
        leaderboard_data = {}
        
        for user_id, user_channels in all_stats.items():
            for channel_id, stats in user_channels.items():
                if scope in ["channel", "this"]:
                    if channel_id != ctx.channel.id:
                        continue
                    counts = stats['counts']
                    fails = stats['fails']
                    best_streak = stats['best_streak']
                    accuracy = (counts / (counts + fails)) * 100 if (counts + fails) > 0 else 0
                    leaderboard_data[user_id] = {
                        'counts': counts,
                        'fails': fails,
                        'accuracy': accuracy,
                        'best_streak': best_streak
                    }
                else:
                    if stats.get('guild_id') != ctx.guild.id:
                        continue
                    if user_id not in leaderboard_data:
                        leaderboard_data[user_id] = {
                            'counts': 0,
                            'fails': 0,
                            'best_streak': 0
                        }
                    leaderboard_data[user_id]['counts'] += stats['counts']
                    leaderboard_data[user_id]['fails'] += stats['fails']
                    leaderboard_data[user_id]['best_streak'] = max(
                        leaderboard_data[user_id]['best_streak'],
                        stats['best_streak']
                    )
        
        if scope not in ["channel", "this"]:
            for user_id in leaderboard_data:
                counts = leaderboard_data[user_id]['counts']
                fails = leaderboard_data[user_id]['fails']
                accuracy = (counts / (counts + fails)) * 100 if (counts + fails) > 0 else 0
                leaderboard_data[user_id]['accuracy'] = accuracy
        
        sorted_results = sorted(
            leaderboard_data.items(),
            key=lambda x: (x[1]['counts'], x[1]['accuracy']),
            reverse=True
        )[:10]
        
        if not sorted_results:
            title = f"🏆 {ctx.channel.name} Leaderboard" if scope in ["channel", "this"] else f"🏆 {ctx.guild.name} Leaderboard"
            embed = discord.Embed(
                title=title,
                description="No counting data available yet. Start counting!",
                color=self.embed_color
            )
            return await ctx.send(embed=embed)
        
        title = f"🏆 {ctx.channel.name} Leaderboard" if scope in ["channel", "this"] else f"🏆 {ctx.guild.name} Leaderboard"
        
        embed = discord.Embed(
            title=title,
            color=self.embed_color,
            timestamp=discord.utils.utcnow()
        )
        
        leaderboard_text = []
        for i, (user_id, stats) in enumerate(sorted_results, 1):
            user = ctx.guild.get_member(user_id)
            username = user.mention if user else f"User {user_id}"
            
            leaderboard_text.append(
                f"{self.get_medal(i)} **{username}**\n"
                f"**Counts:** {stats['counts']} | **Accuracy:** {stats['accuracy']:.1f}% | **Streak:** {stats['best_streak']}"
            )
        
        embed.description = "\n\n".join(leaderboard_text)
        embed.set_footer(text=f"Scope: {scope.title()}")
        await ctx.send(embed=embed)
    
    def get_medal(self, position: int) -> str:
        """Get medal emoji for position"""
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        return medals[position - 1] if position <= len(medals) else f"{position}."
    
    @counting_group.command(name="disable")
    @commands.has_permissions(manage_channels=True)
    async def disable_counting(self, ctx):
        """Disable counting in channel"""
        channel_id = ctx.channel.id
        if channel_id not in self.active_channels:
            embed = discord.Embed(
                title="❌ Channel Not Setup",
                description="This channel is not setup for counting.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        await self.update_channel_data(channel_id, enabled=False)

        if channel_id in self.active_channels:
            del self.active_channels[channel_id]
        
        embed = discord.Embed(
            title="✅ Counting Disabled",
            description=f"Counting game has been disabled in {ctx.channel.mention}.",
            color=0x2ecc71
        )
        await ctx.send(embed=embed)
    
    @counting_group.command(name="reset")
    @commands.has_permissions(manage_channels=True)
    async def reset_counting(self, ctx):
        """Reset counting progress"""
        channel_id = ctx.channel.id
        if channel_id not in self.active_channels:
            embed = discord.Embed(
                title="❌ Channel Not Setup",
                description="This channel is not setup for counting.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        view = discord.ui.View(timeout=30)
        
        async def confirm_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not authorized!", ephemeral=True)
                return
            
            await self.update_channel_data(
                channel_id,
                current_number=0,
                last_counter_id=None,
                fails=0
            )
            
            embed = discord.Embed(
                title="✅ Counting Reset",
                description=(
                    f"Counting progress has been reset in {ctx.channel.mention}!\n\n"
                    f"**Next number:** `1`\n"
                    f"**High score preserved:** `{self.active_channels[channel_id]['high_score']}`"
                ),
                color=0x2ecc71
            )
            embed.set_footer(text=f"Reset by {ctx.author}")
            await interaction.response.edit_message(embed=embed, view=None)
            view.stop()
        
        async def cancel_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not authorized!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="❌ Reset Cancelled",
                description="Counting reset has been cancelled.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            view.stop()
        
        confirm_button = discord.ui.Button(label="✅ Confirm Reset", style=discord.ButtonStyle.danger)
        confirm_button.callback = confirm_callback
        
        cancel_button = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
        cancel_button.callback = cancel_callback
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)
        
        embed = discord.Embed(
            title="⚠️ Reset Counting?",
            description=(
                f"Are you sure you want to reset counting in {ctx.channel.mention}?\n\n"
                f"**Current number:** `{self.active_channels[channel_id]['current_number']}`\n"
                f"**High score:** `{self.active_channels[channel_id]['high_score']}`\n\n"
                f"*This will reset the current count to 0.*"
            ),
            color=discord.Color.orange()
        )
        embed.set_footer(text="High score will be preserved")
        
        message = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        if not view.is_finished():
            for child in view.children:
                child.disabled = True
            await message.edit(view=view)
    
    @counting_group.command(name="info")
    async def counting_info(self, ctx):
        """Show counting information"""
        channel_id = ctx.channel.id
        if channel_id not in self.active_channels:
            embed = discord.Embed(
                title="🔢 Counting Game",
                description=(
                    "This channel is not setup for counting.\n\n"
                    "**To setup:**\n"
                    "`!counting setup` - Setup counting in this channel\n\n"
                    "**Requirements:** Manage Channels permission"
                ),
                color=self.embed_color
            )
            return await ctx.send(embed=embed)
        
        channel_data = self.active_channels[channel_id]
        
        all_stats = self.get_all_stats()
        channel_contributors = []
        for user_id, user_channels in all_stats.items():
            if channel_id in user_channels:
                stats = user_channels[channel_id]
                channel_contributors.append((user_id, stats['counts']))
        
        channel_contributors.sort(key=lambda x: x[1], reverse=True)
        top_contributors = channel_contributors[:3]
        
        embed = discord.Embed(
            title=f"🔢 Counting Game - {ctx.channel.name}",
            color=self.embed_color,
            timestamp=discord.utils.utcnow()
        )
        
        next_number = channel_data['current_number'] + 1 if not channel_data['countdown_mode'] else channel_data['current_number'] - 1
        if channel_data['countdown_mode'] and channel_data['current_number'] <= 1:
            next_number = "Game Complete!"
        
        last_counter = f"<@{channel_data['last_counter_id']}>" if channel_data['last_counter_id'] else 'None'
        status_text = (
            f"**Current Number:** `{channel_data['current_number']}`\n"
            f"**Next Number:** `{next_number}`\n"
            f"**High Score:** `{channel_data['high_score']}`\n"
            f"**Fails:** `{channel_data['fails']}`\n"
            f"**Last Counter:** {last_counter}"
        )
        
        settings_text = (
            f"**Cooldown:** `{channel_data['cooldown_seconds']}s`\n"
            f"**Same User:** `{channel_data['allow_same_user']}`\n"
            f"**Reset on Fail:** `{channel_data['reset_on_fail']}`\n"
            f"**Countdown Mode:** `{channel_data['countdown_mode']}`\n"
            f"**Allow Decimal:** `{channel_data['allow_decimal']}`"
        )
        
        if top_contributors:
            contributors_text = []
            for i, (user_id, counts) in enumerate(top_contributors, 1):
                user = ctx.guild.get_member(user_id)
                username = user.mention if user else f"User {user_id}"
                contributors_text.append(f"{self.get_medal(i)} {username} - `{counts}` counts")
            contributors = "\n".join(contributors_text)
        else:
            contributors = "No contributors yet"
        
        embed.add_field(name="📊 Current Status", value=status_text, inline=False)
        embed.add_field(name="⚙️ Settings", value=settings_text, inline=False)
        embed.add_field(name="🏆 Top Contributors", value=contributors, inline=False)
        embed.set_footer(text=f"Channel ID: {channel_id}")
        
        await ctx.send(embed=embed)
    
    @counting_group.command(name="test")
    @commands.has_permissions(manage_channels=True)
    async def test_counting(self, ctx):
        """Test counting configuration"""
        channel_id = ctx.channel.id
        if channel_id not in self.active_channels:
            embed = discord.Embed(
                title="❌ Channel Not Setup",
                description="This channel is not setup for counting.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        channel_data = self.active_channels[channel_id]
        
        test_number = channel_data['current_number'] + 1
        if channel_data['countdown_mode']:
            test_number = channel_data['current_number'] - 1 if channel_data['current_number'] > 1 else 1
        
        embed = discord.Embed(
            title="🧪 Counting Test",
            description=(
                f"**Simulated count for {ctx.author.mention}:**\n\n"
                f"**Current number:** `{channel_data['current_number']}`\n"
                f"**Expected next:** `{test_number}`\n"
                f"**Cooldown:** `{channel_data['cooldown_seconds']}s`\n"
                f"**Same user allowed:** `{channel_data['allow_same_user']}`\n\n"
                f"*This is just a test. Actual counting rules apply during gameplay.*"
            ),
            color=self.embed_color
        )
        
        rules = []
        if not channel_data['allow_same_user']:
            rules.append("❌ Cannot count twice in a row")
        if channel_data['cooldown_seconds'] > 0:
            rules.append(f"⏰ {channel_data['cooldown_seconds']}s cooldown")
        if channel_data['countdown_mode']:
            rules.append("⬇️ Counting down")
        if not channel_data['allow_decimal']:
            rules.append("🔢 Whole numbers only")
        
        if rules:
            embed.add_field(name="📜 Active Rules", value="\n".join(rules), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle counting game messages"""
        if (message.author.bot or 
            not message.guild or 
            message.content.startswith(tuple(await self.bot.get_prefix(message)))):
            return
        
        channel_id = message.channel.id
        if channel_id not in self.active_channels:
            return
        
        channel_data = self.active_channels[channel_id]
        content = message.content.strip()
        
        try:
            if channel_data['allow_decimal']:
                import re
                number_match = re.search(r'[-+]?\d*\.?\d+', content)
                if not number_match:
                    return
                number = float(number_match.group())
            else:
                number = int(content)
        except (ValueError, TypeError):
            return
        
        cooldown_key = (message.author.id, channel_id)
        if cooldown_key in self.user_cooldowns:
            time_diff = (discord.utils.utcnow() - self.user_cooldowns[cooldown_key]).total_seconds()
            if time_diff < channel_data['cooldown_seconds']:
                remaining = channel_data['cooldown_seconds'] - time_diff
                try:
                    await message.delete()
                except:
                    pass
                await message.channel.send(
                    f"{message.author.mention}, please wait {remaining:.1f}s before counting again!",
                    delete_after=3
                )
                return
        
        if not channel_data['allow_same_user'] and channel_data['last_counter_id'] == message.author.id:
            await self.handle_counting_fail(
                message, channel_data,
                f"{message.author.mention} cannot count twice in a row!"
            )
            return
        
        if channel_data['countdown_mode']:
            expected = channel_data['current_number'] - 1
            if expected < 1:
                expected = 1
        else:
            expected = channel_data['current_number'] + 1
        
        if number != expected:
            await self.handle_counting_fail(
                message, channel_data,
                f"{message.author.mention} said `{number}` but `{expected}` was expected!"
            )
            return
        
        self.user_cooldowns[cooldown_key] = discord.utils.utcnow()
        new_current = number
        
        await self.update_channel_data(
            channel_id,
            current_number=new_current,
            last_counter_id=message.author.id
        )
        
        if new_current > channel_data['high_score']:
            await self.update_channel_data(
                channel_id,
                high_score=new_current,
                last_high_score_user_id=message.author.id
            )
        
        all_stats = self.get_all_stats()
        user_channel_stats = all_stats.get(message.author.id, {}).get(channel_id, {})
        current_best = user_channel_stats.get('best_streak', 0)

        await self.update_user_stats(
            message.author.id, channel_id, message.guild.id,
            counts=1, best_streak=0
        )
        
        try:
            await message.add_reaction("✅")
        except:
            pass
        
        if new_current % 100 == 0:
            milestone_embed = discord.Embed(
                title="🎉 Counting Milestone!",
                description=f"**{message.author.mention} reached `{new_current}`!** 🎊",
                color=0x2ecc71
            )
            if message.author.avatar:
                milestone_embed.set_thumbnail(url=message.author.avatar.url)
            await message.channel.send(embed=milestone_embed)
    
    async def handle_counting_fail(self, message: discord.Message, channel_data: Dict, reason: str):
        """Handle counting failure"""
        channel_id = message.channel.id
        try:
            await message.delete()
        except:
            pass
        
        fail_embed = discord.Embed(
            title="❌ Counting Failed!",
            description=reason,
            color=discord.Color.red()
        )
        fail_embed.set_footer(text=f"Current number: {channel_data['current_number']}")
        fail_message = await message.channel.send(embed=fail_embed)
        
        await self.update_channel_data(channel_id, fails=channel_data['fails'] + 1)
        await self.update_user_stats(message.author.id, channel_id, message.guild.id, fails=1)
        
        if channel_data['reset_on_fail']:
            await self.update_channel_data(channel_id, current_number=0, last_counter_id=None)
            reset_embed = discord.Embed(
                title="🔄 Counting Reset",
                description="The count has been reset to `0`. Start again from `1`!",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=reset_embed)
        
        await asyncio.sleep(5)
        try:
            await fail_message.delete()
        except:
            pass
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Clean up when a counting channel is deleted"""
        if isinstance(channel, discord.TextChannel):
            channel_id = channel.id
            if channel_id in self.active_channels:
                del self.active_channels[channel_id]
            
            all_channels = self.get_all_channels()
            if channel_id in all_channels:
                del all_channels[channel_id]
                self._save_channels({str(k): v for k, v in all_channels.items()})
            
            all_stats = self.get_all_stats()
            changed = False
            for user_id in list(all_stats.keys()):
                if channel_id in all_stats[user_id]:
                    del all_stats[user_id][channel_id]
                    changed = True
                if not all_stats[user_id]:
                    del all_stats[user_id]
            if changed:
                stats_to_save = {}
                for uid, channels in all_stats.items():
                    stats_to_save[str(uid)] = {}
                    for cid, stats in channels.items():
                        stats_to_save[str(uid)][str(cid)] = stats
                self._save_stats(stats_to_save)
            
            all_rules = self.get_all_rules()
            if channel_id in all_rules:
                del all_rules[channel_id]
                self._save_rules({str(k): v for k, v in all_rules.items()})
    
    @counting_group.error
    async def counting_error(self, ctx, error):
        """Error handler for counting commands"""
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need **Manage Channels** permissions to use this command!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)
        elif isinstance(error, commands.BotMissingPermissions):
            missing = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            embed = discord.Embed(
                title="❌ Bot Missing Permissions",
                description=f"I need: `{', '.join(missing)}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)

async def setup(bot):
    """Load the Counting Game cog"""
    await bot.add_cog(CountingCog(bot))