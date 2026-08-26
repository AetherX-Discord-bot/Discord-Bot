import discord
from typing import Optional
from discord.ext import commands
from discord.ui import View, Button

class AboutCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._original_help = bot.help_command

    @commands.command(
        name="about",
        description="Shows information about the bot"
    )
    async def about(self, ctx: commands.Context):
        about_embed = discord.Embed(
            title="AetherX Bot Information",
            description="AetherX is a custom Discord bot designed by Androgalaxi and snowekitsune.\n\nInvite the bot to your server using [this link](https://discord.com/oauth2/authorize?client_id=1067646246254284840&permissions=582056601447606&integration_type=0&scope=bot) or the link below.",
            color=0x7289da
        )

        about_embed.add_field(
            name="Developers",
            value="[Androgalaxi](https://discord.com/users/435125886996709377), [lmutt090](https://discord.com/users/1286383453016686705), and [snowekitsune](https://discord.com/users/811016330517676073)",
            inline=False
        )
        about_embed.add_field(
            name="Bot Version",
            value="0.3.1-alpha",
            inline=False
        )
        about_embed.add_field(
            name="Bot Invite Link",
            value="[Invite AetherX](https://discord.com/oauth2/authorize?client_id=1067646246254284840&permissions=582056601447606&integration_type=0&scope=bot)",
            inline=False
        )
        about_embed.add_field(
            name="Support Server",
            value="[Join the Support Server](https://discord.gg/yFY8Fnbtp9)",
            inline=False
        )
        about_embed.add_field(
            name="Terms of Service",
            value="[View Terms of Service](https://aether-x.org/TOS/)",
            inline=False
        )
        about_embed.add_field(
            name="Privacy Policy",
            value="[View Privacy Policy](https://aether-x.org/PrivPOL/)",
            inline=False
        )

        about_embed.set_footer(
            text="AetherX - Created by Androgalaxi, lmutt090, snowekitsune, and many other wonderful people"
        )

        await ctx.send(embed=about_embed)

    @commands.command(name="help", description="Show help for all cogs or commands.", hidden=True)
    async def help(self, ctx, *, arg: Optional[str] = None):
        """Show help for all cogs or commands available to the user. Use '$help <cog>' to see commands in a cog, or '$help list' for all commands."""
        embed = discord.Embed(
            title=f"{self.bot.user.name} Help" if self.bot.user else "Bot Help",
            color=discord.Color.green()
        )
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
        if arg:
            import re
            match = re.match(r"([a-zA-Z0-9_]+)(\d+)?$", arg.strip())
            if match:
                cog_arg = match.group(1)
            else:
                cog_arg = arg
            cog = self.bot.cogs.get(cog_arg)
            if not cog:
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
        embed.description = "Select a category below to see its commands. Use `$help <cog>` to view commands in a category."

        cogs_available = []
        for cog_name, cog in self.bot.cogs.items():
            commands_list = []
            for cmd in cog.get_commands():
                if not cmd.hidden:
                    try:
                        if await cmd.can_run(ctx):
                            commands_list.append(cmd)
                    except Exception:
                        continue
            if commands_list:
                cogs_available.append((cog_name, cog, commands_list))

        if not cogs_available:
            embed.description = "No commands available."
            embed.set_footer(text=f"Requested by {ctx.author}")
            await ctx.send(embed=embed)
            return

        options = []
        for cog_name, cog, commands_list in cogs_available[:25]:
            desc = (getattr(cog, '__doc__', '') or '').strip()
            options.append(discord.SelectOption(label=cog_name, description=(desc[:97] + '...') if desc and len(desc) > 100 else desc or None, value=cog_name))

        class HelpSelect(discord.ui.Select):
            def __init__(self, options, ctx, cogs_map):
                super().__init__(placeholder='Choose a category...', min_values=1, max_values=1, options=options)
                self.ctx = ctx
                self.cogs_map = cogs_map

            async def callback(self, interaction: discord.Interaction):
                selected = self.values[0]
                cog, commands_list = self.cogs_map[selected]
                lines = []
                for cmd in commands_list:
                    aliases = f" (aliases: {', '.join(cmd.aliases)})" if getattr(cmd, 'aliases', None) else ""
                    lines.append(f"**{cmd.name}**{aliases} - {cmd.help or 'No description.'}")

                cog_embed = discord.Embed(
                    title=f"{getattr(cog, 'qualified_name', selected)} Commands",
                    description=getattr(cog, '__doc__', None) or 'No description.',
                    color=discord.Color.green()
                )
                cog_embed.add_field(name=f"Commands ({len(lines)})", value='\n'.join(lines)[:1024] or 'No commands.', inline=False)
                cog_embed.set_footer(text=f"Requested by {self.ctx.author}")

                back_view = View()
                class BackButton(Button):
                    def __init__(self):
                        super().__init__(label='Back', style=discord.ButtonStyle.secondary)
                    async def callback(self, interaction: discord.Interaction):
                        await interaction.response.edit_message(embed=embed, view=view)
                back_view.add_item(BackButton())

                await interaction.response.edit_message(embed=cog_embed, view=back_view)

        cogs_map = {name: (cog, cmds) for name, cog, cmds in cogs_available}

        select = HelpSelect(options, ctx, cogs_map)
        view = View()
        view.add_item(select)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed, view=view)

    async def cog_load(self):
        self._original_help = self.bot.help_command
        self.bot.help_command = None

    async def cog_unload(self):
        self.bot.help_command = self._original_help

async def setup(bot: commands.Bot):
    await bot.add_cog(AboutCog(bot))