import discord
from discord.ext import commands
from typing import List
import datetime

class ServerList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_users = {435125886996709377, 1286383453016686705, 811016330517676073}
        self.active_views = {}

    async def is_allowed(self, ctx: commands.Context) -> bool:
        """Check if user is allowed to use listservers command"""
        return ctx.author.id in self.allowed_users

    @commands.command(name="sinfo")
    async def server_info(self, ctx: commands.Context):
        """Show information about the current server"""
        guild = ctx.guild
        
        if not guild:
            await ctx.send("❌ This command must be used in a server, not a DM!")
            return
        
        try:
            # Try to fetch owner information
            owner = guild.owner
            if owner is None and guild.owner_id is not None:
                owner = await guild.fetch_member(guild.owner_id)
            owner_name = str(owner) if owner else f"Unknown (ID: {guild.owner_id})"

            # Create embed
            embed = discord.Embed(
                title=f"📊 Server Information: {guild.name}",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            # Basic info
            embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
            embed.add_field(name="👑 Owner", value=owner_name, inline=True)
            embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
            
            # Counts
            text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
            voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
            categories = len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])
            
            embed.add_field(name="📝 Channels", value=f"Text: {text_channels}\nVoice: {voice_channels}\nCategories: {categories}", inline=True)
            embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
            embed.add_field(name="😄 Emojis", value=len(guild.emojis), inline=True)
            
            # Boosting info
            embed.add_field(name="🚀 Boosts", value=guild.premium_subscription_count, inline=True)
            embed.add_field(name="⭐ Boost Level", value=guild.premium_tier, inline=True)
            
            # Dates
            created_at = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
            embed.add_field(name="📅 Created", value=created_at, inline=True)
            
            # Features
            if guild.features:
                features = ", ".join(guild.features) if len(guild.features) <= 5 else f"{len(guild.features)} features"
                embed.add_field(name="✨ Features", value=features, inline=False)
            
            # Server icon
            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)
            
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")
            print(f"Error in sinfo command: {e}")

    @commands.command(name="listservers", aliases=['ls'])
    async def list_servers(self, ctx: commands.Context):
        """List all servers with pagination (restricted)"""
        if not await self.is_allowed(ctx):
            return await ctx.send("You don't have permission to use this command.")

        # Clean up any previous interaction
        if ctx.author.id in self.active_views:
            old_view = self.active_views.pop(ctx.author.id)
            old_view.stop()

        servers = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        items_per_page = 8
        total_pages = (len(servers) + items_per_page - 1) // items_per_page

        class ServerPaginator(discord.ui.View):
            def __init__(self, user_id: int, servers: List[discord.Guild], active_views: dict, *, timeout=180):
                super().__init__(timeout=timeout)
                self.current_page = 0
                self.user_id = user_id
                self.servers = servers
                self.items_per_page = items_per_page
                self.total_pages = total_pages
                self.active_views = active_views

            async def create_embed(self):
                start = self.current_page * self.items_per_page
                end = start + self.items_per_page
                current_servers = self.servers[start:end]

                embed = discord.Embed(
                    title=f"Server List ({len(self.servers)}) - Page {self.current_page + 1}/{self.total_pages}",
                    color=discord.Color.blue()
                )

                for i, guild in enumerate(current_servers, start=start + 1):
                    try:
                        owner = guild.owner
                        if owner is None and guild.owner_id is not None:
                            owner = await guild.fetch_member(guild.owner_id)
                        owner_display = f"{owner}" if owner else f"Unknown (ID: {guild.owner_id})"
                    except:
                        owner_display = f"Unknown (ID: {guild.owner_id})"

                    embed.add_field(
                        name=f"{i}. {guild.name}",
                        value=(
                            f"ID: {guild.id}\n"
                            f"Members: {guild.member_count}\n"
                            f"Owner: {owner_display}"
                        ),
                        inline=False
                    )

                embed.set_footer(text=f"Total Members Across All Servers: {sum(g.member_count for g in self.servers if g.member_count)}")
                return embed

            async def update_buttons(self):
                self.prev_page.disabled = self.current_page == 0
                self.next_page.disabled = self.current_page >= self.total_pages - 1
                self.page_info.label = f"Page {self.current_page + 1}/{self.total_pages}"

            @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary)
            async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("This isn't your menu!", ephemeral=True)

                self.current_page -= 1
                await self.update_buttons()
                await interaction.response.edit_message(
                    embed=await self.create_embed(),
                    view=self
                )

            @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, disabled=True)
            async def page_info(self, interaction: discord.Interaction, button: discord.ui.Button):
                pass

            @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
            async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("This isn't your menu!", ephemeral=True)

                self.current_page += 1
                await self.update_buttons()
                await interaction.response.edit_message(
                    embed=await self.create_embed(),
                    view=self
                )

            @discord.ui.button(label="❌", style=discord.ButtonStyle.danger)
            async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.id != self.user_id:
                    return await interaction.response.send_message("This isn't your menu!", ephemeral=True)

                if interaction.message:
                    await interaction.message.delete()
                self.stop()
                self.active_views.pop(self.user_id, None)

            async def on_timeout(self):
                if self.user_id in self.active_views:
                    self.active_views.pop(self.user_id)

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                return interaction.user.id == self.user_id

        # Initialize view
        view = ServerPaginator(ctx.author.id, servers, self.active_views)
        await view.update_buttons()
        message = await ctx.send(embed=await view.create_embed(), view=view)
        self.active_views[ctx.author.id] = view

    async def cog_unload(self):
        """Clean up on cog unload"""
        for view in self.active_views.values():
            view.stop()
        self.active_views.clear()

async def setup(bot):
    await bot.add_cog(ServerList(bot))