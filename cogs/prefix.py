import discord
from discord.ext import commands
import sqlite3
from typing import Optional, List, Dict, Tuple
from contextlib import closing
import re

class PrefixCog(commands.Cog, name="Prefix Manager"):
    """Per-server prefix management for AetherX"""
    
    def __init__(self, bot):
        self.bot = bot
        self.emoji = "⚙️"
        self.db_path = 'AetherX.db'
        self._initialize_db()
        
        self.bot.command_prefix = self.get_prefix
        
        self.prefix_cache: Dict[int, List[str]] = {}
    
    def _initialize_db(self) -> None:
        """Initialize database table for prefixes"""
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS server_prefixes (
                        server_id INTEGER PRIMARY KEY,
                        prefixes TEXT NOT NULL DEFAULT '!',
                        updated_by INTEGER,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
    
    async def get_prefix(self, bot, message: discord.Message) -> List[str]:
        """Get prefixes for the server or DMs"""
        if not message.guild:
            return commands.when_mentioned_or('!')(bot, message)
        
        if message.guild.id in self.prefix_cache:
            return commands.when_mentioned_or(*self.prefix_cache[message.guild.id])(bot, message)
        
        prefixes = await self.get_guild_prefixes(message.guild.id)
        
        self.prefix_cache[message.guild.id] = prefixes
        
        return commands.when_mentioned_or(*prefixes)(bot, message)
    
    async def get_guild_prefixes(self, guild_id: int) -> List[str]:
        """Get prefixes for a specific guild from database"""
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.row_factory = sqlite3.Row
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "SELECT prefixes FROM server_prefixes WHERE server_id = ?",
                    (guild_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    prefix_string = result['prefixes']
                    prefixes = [p.strip() for p in prefix_string.split(',') if p.strip()]
                    return prefixes
                else:
                    return ['!']
    
    async def update_prefix_cache(self, guild_id: int) -> None:
        """Update the prefix cache for a guild"""
        prefixes = await self.get_guild_prefixes(guild_id)
        self.prefix_cache[guild_id] = prefixes
    
    def validate_prefix(self, prefix: str) -> bool:
        """Validate that a prefix is acceptable"""
        if len(prefix) > 10:
            return False
        
        dangerous_patterns = [
            r'@everyone',
            r'@here',
            r'<@!?\d+>',
            r'<@&\d+>',
            r'<#\d+>',
            r'```',
            r'`.*`',
            r'\|\|.*\|\|',
            r'http[s]?://',
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, prefix, re.IGNORECASE):
                return False
        
        if not re.match(r'^[\w\s\W]{1,10}$', prefix):
            return False
        
        return True
    
    @commands.group(
        name="prefix",
        aliases=["setprefix", "changeprefix"],
        brief="Manage server prefixes",
        help=(
            "Manage custom prefixes for this server.\n\n"
            "**Subcommands:**\n"
            "• `set <prefix>` - Set new prefix(es)\n"
            "• `add <prefix>` - Add additional prefix\n"
            "• `remove <prefix>` - Remove a prefix\n"
            "• `list` - Show current prefixes\n"
            "• `reset` - Reset to default prefix (!)\n\n"
            "**Notes:**\n"
            "• You can have up to 5 prefixes\n"
            "• Prefixes can be up to 10 characters\n"
            "• Cannot contain mentions or dangerous content"
        ),
        invoke_without_command=True
    )
    @commands.has_permissions(manage_guild=True)
    async def prefix_group(self, ctx):
        """Prefix management command group"""
        await ctx.send_help(ctx.command)
    
    @prefix_group.command(
        name="set",
        brief="Set new prefix(es) for this server",
        help=(
            "Set new prefix(es) for this server.\n"
            "You can set multiple prefixes separated by commas.\n\n"
            "**Examples:**\n"
            "`!prefix set ?`\n"
            "`!prefix set a!, b!, c!`\n"
            "`!prefix set >>, !!, a.`"
        )
    )
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def set_prefix(self, ctx, *, prefixes: str):
        """Set new prefix(es) for the server"""
        EMBED_COLOR = 0x2b2d31
        
        prefix_list = [p.strip() for p in prefixes.split(',')]
        prefix_list = [p for p in prefix_list if p]
        
        if len(prefix_list) > 5:
            embed = discord.Embed(
                title="❌ Too Many Prefixes",
                description="You can only have up to 5 prefixes per server.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        invalid_prefixes = []
        for prefix in prefix_list:
            if not self.validate_prefix(prefix):
                invalid_prefixes.append(prefix)
        
        if invalid_prefixes:
            embed = discord.Embed(
                title="❌ Invalid Prefixes",
                description=(
                    f"The following prefixes are invalid:\n"
                    f"`{'`, `'.join(invalid_prefixes)}`\n\n"
                    "**Prefix rules:**\n"
                    "• Max 10 characters\n"
                    "• Cannot contain mentions (@everyone, @here, user/role mentions)\n"
                    "• Cannot contain code blocks or spoilers\n"
                    "• Cannot be a URL"
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        warning_prefixes = []
        for prefix in prefix_list:
            common_prefixes = ['!', '?', '.', '-', '$', '>', '/']
            if prefix in common_prefixes:
                warning_prefixes.append(prefix)

        prefix_string = ','.join(prefix_list)
        
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """INSERT OR REPLACE INTO server_prefixes 
                       (server_id, prefixes, updated_by) VALUES (?, ?, ?)""",
                    (ctx.guild.id, prefix_string, ctx.author.id)
                )
                conn.commit()
        
        await self.update_prefix_cache(ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ Prefixes Updated",
            color=0x2ecc71,
            timestamp=discord.utils.utcnow()
        )
        
        embed.description = f"**New prefix(es):** `{'`, `'.join(prefix_list)}`"
        
        if warning_prefixes:
            embed.add_field(
                name="⚠️ Warning",
                value=(
                    f"Prefix(es) `{'`, `'.join(warning_prefixes)}` are commonly used by other bots.\n"
                    f"You might experience command conflicts."
                ),
                inline=False
            )
        
        embed.add_field(
            name="💡 Usage Example",
            value=f"Try: `{prefix_list[0]}help` to see if it works!",
            inline=False
        )
        
        embed.set_footer(text=f"Updated by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @prefix_group.command(
        name="add",
        brief="Add an additional prefix",
        help=(
            "Add an additional prefix to the current list.\n\n"
            "**Example:**\n"
            "If current prefixes are `!`, `?`,\n"
            "`!prefix add .` will make prefixes: `!`, `?`, `.`"
        )
    )
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def add_prefix(self, ctx, *, new_prefix: str):
        """Add a prefix to the existing list"""
        EMBED_COLOR = 0x2b2d31
        
        current_prefixes = await self.get_guild_prefixes(ctx.guild.id)
        
        if new_prefix in current_prefixes:
            embed = discord.Embed(
                title="⚠️ Prefix Already Exists",
                description=f"The prefix `{new_prefix}` is already in use.",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)
        
        if len(current_prefixes) >= 5:
            embed = discord.Embed(
                title="❌ Prefix Limit Reached",
                description="You can only have up to 5 prefixes. Remove one first.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if not self.validate_prefix(new_prefix):
            embed = discord.Embed(
                title="❌ Invalid Prefix",
                description=(
                    f"The prefix `{new_prefix}` is invalid.\n\n"
                    "**Prefix rules:**\n"
                    "• Max 10 characters\n"
                    "• Cannot contain mentions (@everyone, @here, user/role mentions)\n"
                    "• Cannot contain code blocks or spoilers\n"
                    "• Cannot be a URL"
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)

        current_prefixes.append(new_prefix)
        prefix_string = ','.join(current_prefixes)

        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """INSERT OR REPLACE INTO server_prefixes 
                       (server_id, prefixes, updated_by) VALUES (?, ?, ?)""",
                    (ctx.guild.id, prefix_string, ctx.author.id)
                )
                conn.commit()

        await self.update_prefix_cache(ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ Prefix Added",
            description=(
                f"Added prefix: `{new_prefix}`\n\n"
                f"**Current prefixes:** `{'`, `'.join(current_prefixes)}`"
            ),
            color=0x2ecc71,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Updated by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @prefix_group.command(
        name="remove",
        brief="Remove a prefix",
        help=(
            "Remove a prefix from the current list.\n\n"
            "**Example:**\n"
            "If current prefixes are `!`, `?`, `.`,\n"
            "`!prefix remove ?` will leave: `!`, `.`"
        )
    )
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def remove_prefix(self, ctx, *, prefix_to_remove: str):
        """Remove a prefix from the list"""
        EMBED_COLOR = 0x2b2d31

        current_prefixes = await self.get_guild_prefixes(ctx.guild.id)

        if prefix_to_remove not in current_prefixes:
            embed = discord.Embed(
                title="❌ Prefix Not Found",
                description=(
                    f"The prefix `{prefix_to_remove}` is not in the current list.\n\n"
                    f"**Current prefixes:** `{'`, `'.join(current_prefixes)}`"
                ),
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        if len(current_prefixes) == 1:
            embed = discord.Embed(
                title="⚠️ Cannot Remove Last Prefix",
                description=(
                    "This is the only prefix. Use `!prefix reset` to reset to default,\n"
                    "or `!prefix set <new_prefix>` to replace it."
                ),
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        current_prefixes.remove(prefix_to_remove)
        prefix_string = ','.join(current_prefixes)

        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    """INSERT OR REPLACE INTO server_prefixes 
                       (server_id, prefixes, updated_by) VALUES (?, ?, ?)""",
                    (ctx.guild.id, prefix_string, ctx.author.id)
                )
                conn.commit()

        await self.update_prefix_cache(ctx.guild.id)
        
        embed = discord.Embed(
            title="✅ Prefix Removed",
            description=(
                f"Removed prefix: `{prefix_to_remove}`\n\n"
                f"**Current prefixes:** `{'`, `'.join(current_prefixes)}`"
            ),
            color=0x2ecc71,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Updated by {ctx.author}")
        
        await ctx.send(embed=embed)
    
    @prefix_group.command(
        name="list",
        aliases=["show", "current"],
        brief="Show current prefixes",
        help="Show all currently active prefixes for this server."
    )
    async def list_prefixes(self, ctx):
        """List current prefixes for the server"""
        EMBED_COLOR = 0x2b2d31

        prefixes = await self.get_guild_prefixes(ctx.guild.id)
        
        embed = discord.Embed(
            title="⚙️ Server Prefixes",
            color=EMBED_COLOR,
            timestamp=discord.utils.utcnow()
        )
        
        if len(prefixes) == 1:
            embed.description = f"**Current prefix:** `{prefixes[0]}`"
        else:
            prefix_list = "\n".join(f"• `{prefix}`" for prefix in prefixes)
            embed.description = f"**Current prefixes:**\n{prefix_list}"

        example_prefix = prefixes[0] if prefixes else '!'
        embed.add_field(
            name="💡 Usage Examples",
            value=(
                f"`{example_prefix}help` - Show help\n"
                f"`{example_prefix}prefix list` - Show this message\n"
                f"`{example_prefix}prefix set <new>` - Change prefix"
            ),
            inline=False
        )

        if ctx.author.guild_permissions.manage_guild:
            embed.set_footer(text="You can manage prefixes with !prefix set/add/remove")
        else:
            embed.set_footer(text="Requires 'Manage Server' permission to change")
        
        await ctx.send(embed=embed)
    
    @prefix_group.command(
        name="reset",
        brief="Reset to default prefix",
        help="Reset all prefixes to the default '!' prefix."
    )
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def reset_prefix(self, ctx):
        """Reset prefixes to default"""
        EMBED_COLOR = 0x2b2d31

        view = discord.ui.View(timeout=30)
        
        async def confirm_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not authorized!", ephemeral=True)
                return

            with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute(
                        "DELETE FROM server_prefixes WHERE server_id = ?",
                        (ctx.guild.id,)
                    )
                    conn.commit()

            await self.update_prefix_cache(ctx.guild.id)
            
            embed = discord.Embed(
                title="✅ Prefixes Reset",
                description="Prefixes have been reset to default: `!`",
                color=0x2ecc71,
                timestamp=discord.utils.utcnow()
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
                description="Prefix reset has been cancelled.",
                color=EMBED_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=None)
            view.stop()
        
        confirm_button = discord.ui.Button(label="✅ Confirm Reset", style=discord.ButtonStyle.danger)
        confirm_button.callback = confirm_callback
        
        cancel_button = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
        cancel_button.callback = cancel_callback
        
        view.add_item(confirm_button)
        view.add_item(cancel_button)

        current_prefixes = await self.get_guild_prefixes(ctx.guild.id)
        
        embed = discord.Embed(
            title="⚠️ Reset Prefixes?",
            description=(
                f"Are you sure you want to reset all prefixes?\n\n"
                f"**Current prefixes:** `{'`, `'.join(current_prefixes)}`\n"
                f"**Will be reset to:** `!`\n\n"
                f"This action cannot be undone."
            ),
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="This action requires confirmation")
        
        message = await ctx.send(embed=embed, view=view)

        try:
            await view.wait()
        except:
            pass

        if not view.is_finished():
            for child in view.children:
                child.disabled = True
            await message.edit(view=view)
    
    @prefix_group.command(
        name="info",
        brief="Show prefix information",
        help="Show detailed information about prefix usage and settings."
    )
    async def prefix_info(self, ctx):
        """Show detailed prefix information"""
        EMBED_COLOR = 0x2b2d31

        prefixes = await self.get_guild_prefixes(ctx.guild.id)

        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.row_factory = sqlite3.Row
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "SELECT updated_by, updated_at FROM server_prefixes WHERE server_id = ?",
                    (ctx.guild.id,)
                )
                history = cursor.fetchone()
        
        embed = discord.Embed(
            title="⚙️ Prefix Information",
            color=EMBED_COLOR,
            timestamp=discord.utils.utcnow()
        )

        if len(prefixes) == 1:
            embed.add_field(name="Current Prefix", value=f"`{prefixes[0]}`", inline=True)
        else:
            prefix_list = "\n".join(f"• `{prefix}`" for prefix in prefixes)
            embed.add_field(name=f"Prefixes ({len(prefixes)}/5)", value=prefix_list, inline=False)

        total_commands = len(self.bot.commands)
        embed.add_field(
            name="Bot Commands",
            value=f"`{total_commands}` available commands",
            inline=True
        )

        if history:
            try:
                updated_by = self.bot.get_user(history['updated_by']) or f"User {history['updated_by']}"
                embed.add_field(
                    name="Last Updated",
                    value=f"By: {updated_by}\nAt: {history['updated_at']}",
                    inline=False
                )
            except:
                pass
        
        can_manage = ctx.author.guild_permissions.manage_guild
        status = "✅ You can manage prefixes" if can_manage else "❌ You need 'Manage Server' permission"
        embed.add_field(name="Your Permissions", value=status, inline=False)

        example_prefix = prefixes[0] if prefixes else '!'
        embed.add_field(
            name="Quick Examples",
            value=(
                f"`{example_prefix}help` - Show all commands\n"
                f"`{example_prefix}prefix list` - Show prefixes\n"
                f"`{example_prefix}prefix set <new>` - Change prefix"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Server ID: {ctx.guild.id}")
        
        await ctx.send(embed=embed)
    
    @prefix_group.command(
        name="test",
        brief="Test if prefixes work",
        help="Test if the current prefixes are working correctly."
    )
    async def test_prefix(self, ctx, *, command_to_test: str = "help"):
        """Test if prefixes are working"""
        EMBED_COLOR = 0x2b2d31

        prefixes = await self.get_guild_prefixes(ctx.guild.id)

        command = self.bot.get_command(command_to_test)
        
        if not command:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"The command `{command_to_test}` doesn't exist.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🔍 Prefix Test",
            color=EMBED_COLOR,
            timestamp=discord.utils.utcnow()
        )

        prefix_list = "\n".join(f"• `{prefix}{command_to_test}`" for prefix in prefixes)
        embed.add_field(
            name=f"Valid ways to use `{command_to_test}`:",
            value=prefix_list or "No prefixes set (using default '!')",
            inline=False
        )

        test_results = []
        for prefix in prefixes:
            test_cmd = f"{prefix}{command_to_test}"
            test_results.append(f"`{test_cmd}` - ✅ Should work")
        
        if test_results:
            embed.add_field(
                name="Test Results",
                value="\n".join(test_results),
                inline=False
            )
        
        embed.set_footer(text="Try one of these commands to test!")
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """Clean up cache when bot leaves a guild"""
        if guild.id in self.prefix_cache:
            del self.prefix_cache[guild.id]

        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "DELETE FROM server_prefixes WHERE server_id = ?",
                    (guild.id,)
                )
                conn.commit()
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Initialize cache when bot joins a guild"""
        await self.update_prefix_cache(guild.id)
    
    @set_prefix.error
    @add_prefix.error
    @remove_prefix.error
    @reset_prefix.error
    async def prefix_error(self, ctx, error):
        """Error handler for prefix commands"""
        EMBED_COLOR = 0x2b2d31
        
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need **Manage Server** permissions to change prefixes!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                title="❌ Bot Missing Permissions",
                description="I need proper permissions to execute this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)
        
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Command on Cooldown",
                description=f"Please wait `{error.retry_after:.1f}` seconds before using this command again.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=error.retry_after)
        
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Argument",
                description=f"Missing required argument: `{error.param.name}`\nUse `{ctx.prefix}help prefix {ctx.command.name}` for help.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=10)

async def setup(bot):
    """Load the Prefix Manager cog"""
    await bot.add_cog(PrefixCog(bot))