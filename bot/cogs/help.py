import discord
from discord.ext import commands
from discord.ui import Button, View
from functools import partial

class Uncatagorized(commands.Cog):
    """A cog to handle uncategorized commands and provide a help command."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})
        self.HELP_COMMAND_TYPE = self.config.get('HELP_COMMAND_TYPE', 'default')
        self.active_menus = {}  # For interactive help menu ownership

    if self.HELP_COMMAND_TYPE == 'default':
        @commands.hybrid_command(name="help", description="Show help for all cogs or commands.", hidden=True)
        async def help(self, ctx, *, arg: str = None):
            """Show help for all cogs or commands available to the user. Use '!help <cog>' to see commands in a cog, or '!help list' for all commands."""
            embed = discord.Embed(
                title=f"{self.bot.user.name} Help" if self.bot.user else "Bot Help",
                color=discord.Color.green()
            )
            # If 'list' is passed, show all commands as before
            if arg and arg.strip().lower() == "list":
                embed.description = "List of all available commands:"
                for cog_name, cog in self.bot.cogs.items():
                    commands_list = []
                    for cmd in cog.get_commands():
                        if not cmd.hidden:
                            try:
                                if await cmd.can_run(ctx):
                                    aliases = f" (aliases: {', '.join(cmd.aliases)})" if getattr(cmd, 'aliases', None) else ""
                                    commands_list.append(f"{cmd.name}{aliases} - {cmd.help or 'No description.'}")
                            except Exception:
                                continue
                    if commands_list:
                        embed.add_field(
                            name=f"{getattr(cog, 'qualified_name', cog_name)}",
                            value="\n".join(commands_list),
                            inline=False
                        )
                # Also include uncategorized commands (not in a cog)
                uncategorized = []
                for cmd in self.bot.commands:
                    if not cmd.cog and not cmd.hidden:
                        try:
                            if await cmd.can_run(ctx):
                                aliases = f" (aliases: {', '.join(cmd.aliases)})" if getattr(cmd, 'aliases', None) else ""
                                uncategorized.append(f"/{cmd.name}{aliases} - {cmd.help or 'No description.'}")
                        except Exception:
                            continue
                if uncategorized:
                    embed.add_field(name="Other", value="\n".join(uncategorized), inline=False)
                embed.set_footer(text=f"Requested by {ctx.author}")
                await ctx.send(embed=embed)
                return
            # If a cog name is passed, show commands for that cog
            if arg:
                cog = self.bot.cogs.get(arg)
                if not cog:
                    # Try case-insensitive match
                    cog = next((c for n, c in self.bot.cogs.items() if n.lower() == arg.lower()), None)
                if cog:
                    commands_list = []
                    for cmd in cog.get_commands():
                        if not cmd.hidden:
                            try:
                                if await cmd.can_run(ctx):
                                    aliases = f" (aliases: {', '.join(cmd.aliases)})" if getattr(cmd, 'aliases', None) else ""
                                    commands_list.append(f"{cmd.name}{aliases} - {cmd.help or 'No description.'}")
                            except Exception:
                                continue
                    if commands_list:
                        embed.title = f"{getattr(cog, 'qualified_name', arg)} Commands"
                        embed.description = getattr(cog, '__doc__', None) or "No description."
                        embed.add_field(name="Commands", value="\n".join(commands_list), inline=False)
                        embed.set_footer(text=f"Requested by {ctx.author}")
                        await ctx.send(embed=embed)
                        return
                    else:
                        embed = discord.Embed(description=f"No commands available in cog '{arg}' for you.", color=discord.Color.red())
                        await ctx.send(embed=embed)
                        return
                else:
                    embed = discord.Embed(description=f"Cog '{arg}' not found.", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return
            # Default: Show all cogs with at least one command the user can run
            embed.description = "Select a category below to see its commands. Use `!help <cog>` to view commands in a category."
            max_per_cog = 4
            for cog_name, cog in self.bot.cogs.items():
                commands_list = []
                for cmd in cog.get_commands():
                    if not cmd.hidden:
                        try:
                            if await cmd.can_run(ctx):
                                commands_list.append(f"{cmd.name}")
                        except Exception:
                            continue
                if commands_list:
                    cog_desc = getattr(cog, '__doc__', None) or "No description."
                    shown_cmds = commands_list[:max_per_cog]
                    more = f" (+{len(commands_list) - max_per_cog} more...)" if len(commands_list) > max_per_cog else ""
                    embed.add_field(
                        name=f"{getattr(cog, 'qualified_name', cog_name)}",
                        value=f"{cog_desc}\nCommands: {', '.join(shown_cmds)}{more}",
                        inline=False
                    )
            # Also include uncategorized commands (not in a cog)
            uncategorized = []
            for cmd in self.bot.commands:
                if not cmd.cog and not cmd.hidden:
                    try:
                        if await cmd.can_run(ctx):
                            uncategorized.append(f"{cmd.name}")
                    except Exception:
                        continue
            if uncategorized:
                shown_uncat = uncategorized[:max_per_cog]
                more = f" (+{len(uncategorized) - max_per_cog} more...)" if len(uncategorized) > max_per_cog else ""
                embed.add_field(name="Other", value=f"Commands: {', '.join(shown_uncat)}{more}", inline=False)
            embed.set_footer(text=f"Requested by {ctx.author}")
            await ctx.send(embed=embed)
    elif self.HELP_COMMAND_TYPE == 'old aetherx':
        @commands.command(name='help', aliases=['h', 'menu'])
        async def custom_help(self, ctx, *, command_name: str = None):
            """Shows interactive help menus"""
            # Helper functions for menu logic
            async def verify_ownership(interaction, active_menus):
                if interaction.message.id not in active_menus:
                    return False
                return interaction.user.id == active_menus[interaction.message.id]

            async def send_main_menu(ctx, active_menus):
                if isinstance(ctx, discord.Interaction):
                    send_method = ctx.response.edit_message
                    user = ctx.user
                else:
                    send_method = ctx.send
                    user = ctx.author
                embed = discord.Embed(
                    title=f"🍽️ {self.bot.user.name} Command Menu",
                    description="Select a category below to view commands:",
                    color=discord.Color.blue()
                )
                if self.bot.user.avatar:
                    embed.set_thumbnail(url=self.bot.user.avatar.url)
                cog_stats = []
                for cog_name, cog in self.bot.cogs.items():
                    commands_in_cog = [cmd for cmd in cog.get_commands() if not cmd.hidden]
                    if commands_in_cog:
                        cog_stats.append(f"• **{cog_name}**: {len(commands_in_cog)} commands")
                if cog_stats:
                    embed.add_field(
                        name="Available Categories",
                        value="\n".join(cog_stats),
                        inline=False
                    )
                view = View(timeout=3600)
                for cog_name, cog in self.bot.cogs.items():
                    commands_in_cog = [cmd for cmd in cog.get_commands() if not cmd.hidden]
                    if commands_in_cog:
                        button = Button(
                            label=cog_name,
                            style=discord.ButtonStyle.primary,
                            custom_id=f"help_{cog_name.lower()}"
                        )
                        async def cog_menu_callback(interaction, cog_name=cog_name):
                            await send_cog_menu(interaction, cog_name, active_menus)
                        button.callback = cog_menu_callback
                        view.add_item(button)
                close_button = Button(
                    label="Close Menu",
                    style=discord.ButtonStyle.danger,
                    custom_id="help_close"
                )
                async def close_menu(interaction):
                    if not await verify_ownership(interaction, active_menus):
                        await interaction.response.send_message("❌ This isn't your menu to interact with!", ephemeral=True)
                        return
                    if interaction.message.id in active_menus:
                        del active_menus[interaction.message.id]
                    await interaction.message.delete()
                close_button.callback = close_menu
                view.add_item(close_button)
                if isinstance(ctx, discord.Interaction):
                    message = await send_method(embed=embed, view=view)
                else:
                    message = await send_method(embed=embed, view=view)
                active_menus[message.id] = user.id

            async def send_cog_menu(interaction, cog_name, active_menus):
                if not await verify_ownership(interaction, active_menus):
                    await interaction.response.send_message("❌ This isn't your menu to interact with!", ephemeral=True)
                    return
                cog = self.bot.get_cog(cog_name)
                if not cog:
                    await interaction.response.send_message("Category not found!", ephemeral=True)
                    return
                embed = discord.Embed(
                    title=f"📜 {cog_name} Commands",
                    color=discord.Color.purple()
                )
                command_list = []
                for cmd in cog.get_commands():
                    if not cmd.hidden:
                        cmd_desc = cmd.short_doc or "No description"
                        command_list.append(f"• `{cmd.name}` - {cmd_desc}")
                if command_list:
                    embed.description = "\n".join(command_list)
                else:
                    embed.description = "No commands available in this category."
                view = View(timeout=60)
                back_button = Button(
                    label="Back to Main Menu",
                    style=discord.ButtonStyle.secondary,
                    custom_id="help_back"
                )
                async def back_callback(interaction):
                    await send_main_menu(interaction, active_menus)
                back_button.callback = back_callback
                view.add_item(back_button)
                await interaction.response.edit_message(embed=embed, view=view)

            # Track menu ownership in memory for this cog instance
            if not hasattr(self, 'active_menus'):
                self.active_menus = {}
            active_menus = self.active_menus

            if command_name:
                command = self.bot.get_command(command_name.lower())
                if command:
                    embed = discord.Embed(
                        title=f"Command: {command.name}",
                        description=command.help or "No description available.",
                        color=discord.Color.green()
                    )
                    if command.aliases:
                        embed.add_field(
                            name="Aliases",
                            value=", ".join(f"`{alias}`" for alias in command.aliases),
                            inline=False
                        )
                    await ctx.send(embed=embed)
                else:
                    embed = discord.Embed(
                        title="Not Found",
                        description=f"No command or category named '{command_name}' found.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=embed)
            else:
                await send_main_menu(ctx, active_menus)
    elif self.HELP_COMMAND_TYPE == 'none':
        @commands.hybrid_command(name="help", description="Show help for all cogs or commands.", hidden=True)
        async def help(self, ctx, *, arg: str = None):
            """This command is disabled."""
            embed = discord.Embed(
                title="Help Command Disabled",
                description="The help command is currently disabled.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    else:
        if self.HELP_COMMAND_TYPE == 'discord default':
            print("Using Discord's default help command.")
        else:
            print(f"Unknown HELP_COMMAND_TYPE: {self.HELP_COMMAND_TYPE}. Defaulting to 'Discord Default'.")


    # Override the default help command
    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    async def cog_load(self):
        self._original_help_command = self.bot.help_command

async def setup(bot):
    help_command_type = bot.config.get('HELP_COMMAND_TYPE', 'default')
    # These types override Discord's default help command
    if help_command_type in ['default', 'aetherx default', 'none']:
        if help_command_type == 'none':
            bot.help_command = None
        else:
            # For 'default' and 'aetherx default', use your custom help
            bot.help_command = Uncatagorized(bot).help
        await bot.add_cog(Uncatagorized(bot))
    else:
        # For any other value, use Discord's default help command
        print("Using Discord's default help command.")
        await bot.add_cog(Uncatagorized(bot))
