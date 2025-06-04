import discord
from discord.ext import commands

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

    # Override the default help command
    def cog_unload(self):
        self.bot.help_command = self._original_help_command

    async def cog_load(self):
        self._original_help_command = self.bot.help_command
        self.bot.help_command = None

def setup_help_override(bot):
    bot.help_command = None

async def setup(bot):
    await bot.add_cog(Uncatagorized(bot))
