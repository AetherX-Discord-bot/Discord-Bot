import discord
from discord.ext import commands
from discord.ui import Button, View
from functools import partial

class Uncatagorized(commands.Cog):
    """A cog to handle uncategorized commands and provide a help command."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

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
        # If a cog name is passed, show commands for that cog, with pagination support
        if arg:
            import re
            match = re.match(r"([a-zA-Z0-9_]+)(\d+)?$", arg.strip())
            if match:
                cog_arg = match.group(1)
            else:
                cog_arg = arg
            cog = self.bot.cogs.get(cog_arg)
            if not cog:
                # Try case-insensitive match
                cog = next((c for n, c in self.bot.cogs.items() if n.lower() == cog_arg.lower()), None)
            if cog:
                commands_list = []
                for cmd in cog.get_commands():
                    if not cmd.hidden:
                        try:
                            if await cmd.can_run(ctx):
                                aliases = f" (aliases: {', '.join(cmd.aliases)})" if getattr(cmd, 'aliases', None) else ""
                                commands_list.append(f"- **{cmd.name}**{aliases} - {cmd.help or '__***No description.***__'}")
                        except Exception:
                            continue
                if commands_list:
                    max_per_page = 10
                    total_pages = (len(commands_list) + max_per_page - 1) // max_per_page
                    page = 1
                    def get_embed(page):
                        embed = discord.Embed(
                            title=f"{getattr(cog, 'qualified_name', cog_arg)} Commands (Page {page})",
                            description=getattr(cog, '__doc__', None) or "No description.",
                            color=discord.Color.green()
                        )
                        start = (page - 1) * max_per_page
                        end = start + max_per_page
                        chunk = commands_list[start:end]
                        embed.add_field(
                            name=f"Commands {start+1}-{min(end, len(commands_list))} of {len(commands_list)}",
                            value="\n".join(chunk),
                            inline=False
                        )
                        if total_pages > 1:
                            embed.set_footer(text=f"Requested by {ctx.author} | Page {page}/{total_pages}")
                        else:
                            embed.set_footer(text=f"Requested by {ctx.author}")
                        return embed
                    class HelpView(View):
                        def __init__(self, *, timeout=60):
                            super().__init__(timeout=timeout)
                            self.page = 1
                        async def update(self, interaction):
                            await interaction.response.edit_message(embed=get_embed(self.page), view=self)
                        @discord.ui.button(label='Previous', style=discord.ButtonStyle.primary, disabled=True)
                        async def previous(self, interaction: discord.Interaction, button: Button):
                            self.page -= 1
                            self.next.disabled = False
                            if self.page == 1:
                                button.disabled = True
                            await self.update(interaction)
                        @discord.ui.button(label='Next', style=discord.ButtonStyle.primary, disabled=(total_pages <= 1))
                        async def next(self, interaction: discord.Interaction, button: Button):
                            self.page += 1
                            self.previous.disabled = False
                            if self.page == total_pages:
                                button.disabled = True
                            await self.update(interaction)
                    view = HelpView()
                    if total_pages == 1:
                        view.previous.disabled = True
                        view.next.disabled = True
                    await ctx.send(embed=get_embed(1), view=view)
                    return
                else:
                    embed = discord.Embed(description=f"No commands available in cog '{cog_arg}' for you.", color=discord.Color.red())
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
                value = f"{cog_desc}\nCommands: {', '.join(shown_cmds)}{more}"
                # If too many commands, add a button for full list
                if len(commands_list) > max_per_cog:
                    value += f"\nUse `!help {cog_name}` to see all commands in this category."
                embed.add_field(
                    name=f"{getattr(cog, 'qualified_name', cog_name)}",
                    value=value,
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

    @commands.command(name="introduction", description="What to do next?", hidden=True)
    async def whattodo(self, ctx):
        """Provide a message to guide users on what to do next."""
        embed = discord.Embed(
            title="What to do next?",
            description="Use `!help <cog>` to see commands in a specific category, or `!help list` for all commands.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Setting up your profile",
            value="Use `!settings` to set up your profile."
        )
        embed.add_field(
            name="Seeing profiles",
            value="Use `!profile <user>` to see a user's profile."
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)

    # Override the default help command
    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    async def cog_load(self):
        self._original_help_command = self.bot.help_command

async def setup(bot):
    bot.help_command = None
    await bot.add_cog(Uncatagorized(bot))
