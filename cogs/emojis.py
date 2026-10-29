import discord
from discord.ext import commands
import asyncio
import aiohttp
from typing import List, Dict
import re


class EmojiCloneCog(commands.Cog, name="Emoji Manager"):
    """Emoji cloning and management utilities for AetherX"""

    def __init__(self, bot):
        self.bot = bot
        self.emoji = "🎨"
        self.active_sessions = {}

    @commands.command(
        name="cloneemoji",
        aliases=["stealemoji", "addemoji"],
        brief="Clone emojis from other servers",
        help=(
            "Clone emojis from other servers to the current server.\n"
            "You can provide emoji objects, IDs, or URLs.\n"
            "**Requires:** Manage Emojis permission"
        )
    )
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def clone_emoji(self, ctx, *, emoji_input: str):
        if ctx.author.id in self.active_sessions:
            return await ctx.send("You already have an active emoji session. Please complete it first.")

        EMBED_COLOR = 0x2b2d31

        if emoji_input.lower() in ["interactive", "browse", "menu"]:
            await self.start_interactive_session(ctx)
            return

        server_match = re.match(r'server\s+(\d+)', emoji_input.lower())
        if server_match:
            server_id = int(server_match.group(1))
            await self.browse_server_emojis(ctx, server_id)
            return

        user_match = re.match(r'all\s+from\s+<@!?(\d+)>', emoji_input.lower())
        if user_match:
            user_id = int(user_match.group(1))
            await self.clone_from_user(ctx, user_id)
            return

        emojis = await self.parse_emoji_input(emoji_input)

        if not emojis:
            embed = discord.Embed(
                title="❌ No Emojis Found",
                description=(
                    "No valid emojis found in your input.\n\n"
                    "**Valid formats:**\n"
                    "• Emoji objects: `🎨` `😄`\n"
                    "• Emoji IDs: `123456789012345678`\n"
                    "• Emoji URLs: `https://cdn.discordapp.com/emojis/123456.png`\n\n"
                    "**Other commands:**\n"
                    "• `!cloneemoji interactive` - Browse servers\n"
                    "• `!cloneemoji all from @user` - Clone from user's messages\n"
                    "• `!cloneemoji server <server_id>` - Browse specific server"
                ),
                color=0x2b2d31
            )
            await ctx.send(embed=embed)
            return

        await self.process_emoji_cloning(ctx, emojis)

    async def parse_emoji_input(self, input_text: str) -> List[Dict]:
        emojis = []

        custom_emoji_pattern = r'<a?:(\w+):(\d+)>'
        matches = re.findall(custom_emoji_pattern, input_text)

        for name, emoji_id in matches:
            animated = input_text.find(f'<a:{name}:{emoji_id}') != -1
            emojis.append({
                'type': 'custom',
                'id': int(emoji_id),
                'name': name,
                'animated': animated,
                'url': f'https://cdn.discordapp.com/emojis/{emoji_id}.{"gif" if animated else "png"}'
            })

        id_pattern = r'\b(\d{17,20})\b'
        id_matches = re.findall(id_pattern, input_text)

        for emoji_id in id_matches:
            emojis.append({
                'type': 'id',
                'id': int(emoji_id),
                'url': f'https://cdn.discordapp.com/emojis/{emoji_id}.png'
            })

        url_pattern = r'https?://cdn\.discordapp\.com/emojis/(\d+)\.(png|gif|webp)'
        url_matches = re.findall(url_pattern, input_text)

        for emoji_id, ext in url_matches:
            emojis.append({
                'type': 'url',
                'id': int(emoji_id),
                'animated': ext == 'gif',
                'url': f'https://cdn.discordapp.com/emojis/{emoji_id}.{ext}'
            })

        unique_emojis = []
        seen_ids = set()
        for emoji in emojis:
            if emoji['id'] not in seen_ids:
                seen_ids.add(emoji['id'])
                unique_emojis.append(emoji)

        return unique_emojis

    async def process_emoji_cloning(self, ctx, emojis: List[Dict]):
        EMBED_COLOR = 0x2b2d31

        if len(emojis) > 10:
            embed = discord.Embed(
                title="🎨 **Bulk Emoji Cloning** 🎨",
                description=(
                    f"Found **{len(emojis)}** emojis to clone.\n\n"
                    f"**Server:** {ctx.guild.name}\n"
                    f"**Slots Available:** {ctx.guild.emoji_limit - len(ctx.guild.emojis)}\n\n"
                    f"This may take a while. Proceed?"
                ),
                color=EMBED_COLOR
            )

            view = discord.ui.View(timeout=30)

            async def confirm_callback(interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized!", ephemeral=True)
                    return

                await interaction.response.defer()
                await self.bulk_clone_emojis(ctx, emojis)
                view.stop()

            async def cancel_callback(interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized!", ephemeral=True)
                    return

                embed = discord.Embed(
                    title="❌ Operation Cancelled",
                    description="Bulk emoji cloning cancelled.",
                    color=EMBED_COLOR
                )
                await interaction.response.edit_message(embed=embed, view=None)
                view.stop()

            confirm_button = discord.ui.Button(label="✅ Clone All", style=discord.ButtonStyle.success)
            confirm_button.callback = confirm_callback

            cancel_button = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.danger)
            cancel_button.callback = cancel_callback

            view.add_item(confirm_button)
            view.add_item(cancel_button)

            message = await ctx.send(embed=embed, view=view)

            try:
                await view.wait()
            except Exception:
                pass

            for child in view.children:
                child.disabled = True
            await message.edit(view=view)
        else:
            await self.clone_single_emojis(ctx, emojis)

    async def clone_single_emojis(self, ctx, emojis: List[Dict]):
        EMBED_COLOR = 0x2b2d31

        for i, emoji_data in enumerate(emojis, 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(emoji_data['url']) as resp:
                        if resp.status != 200:
                            continue
                        emoji_bytes = await resp.read()

                embed = discord.Embed(
                    title=f"🎨 Emoji {i}/{len(emojis)}",
                    description=(
                        f"**Emoji URL:** [Click Here]({emoji_data['url']})\n"
                        f"**Type:** {'🎭 Animated' if emoji_data.get('animated') else '🖼️ Static'}\n\n"
                        f"Please enter a name for this emoji (2-32 characters, alphanumeric and underscores only):"
                    ),
                    color=EMBED_COLOR
                )

                if emoji_data.get('name'):
                    embed.add_field(name="Suggested Name", value=emoji_data['name'], inline=False)

                embed.set_footer(text="Type 'skip' to skip this emoji or 'cancel' to stop")

                await ctx.send(embed=embed)

                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel

                try:
                    name_msg = await self.bot.wait_for('message', timeout=30.0, check=check)

                    if name_msg.content.lower() == 'cancel':
                        await ctx.send("✅ Operation cancelled.")
                        return

                    if name_msg.content.lower() == 'skip':
                        await ctx.send(f"⏭️ Skipped emoji {i}")
                        continue

                    emoji_name = name_msg.content.strip()

                    if not (2 <= len(emoji_name) <= 32) or not re.match(r'^[a-zA-Z0-9_]+$', emoji_name):
                        await ctx.send("❌ Invalid emoji name. Must be 2-32 characters, alphanumeric and underscores only.")
                        continue

                    try:
                        emoji = await ctx.guild.create_custom_emoji(
                            name=emoji_name,
                            image=emoji_bytes,
                            reason=f"Cloned by {ctx.author} (ID: {ctx.author.id})"
                        )

                        success_embed = discord.Embed(
                            title="✅ Emoji Added",
                            description=(
                                f"**Name:** `:{emoji.name}:`\n"
                                f"**Preview:** {emoji}\n"
                                f"**Animated:** {'Yes' if emoji.animated else 'No'}"
                            ),
                            color=0x2ecc71
                        )
                        await ctx.send(embed=success_embed)

                    except discord.HTTPException as e:
                        error_embed = discord.Embed(
                            title="❌ Failed to Add Emoji",
                            description=f"Error: {str(e)}",
                            color=discord.Color.red()
                        )
                        await ctx.send(embed=error_embed)
                        continue

                except asyncio.TimeoutError:
                    await ctx.send("⏰ Timeout. Moving to next emoji...")
                    continue

            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Error Processing Emoji",
                    description=f"Failed to process emoji: {str(e)}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=error_embed)
                continue

    async def bulk_clone_emojis(self, ctx, emojis: List[Dict]):
        EMBED_COLOR = 0x2b2d31

        available_slots = ctx.guild.emoji_limit - len(ctx.guild.emojis)
        if available_slots <= 0:
            embed = discord.Embed(
                title="❌ No Slots Available",
                description=f"This server has reached its emoji limit ({ctx.guild.emoji_limit}).",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        emojis_to_clone = emojis[:available_slots]

        progress_embed = discord.Embed(
            title="🎨 **Bulk Cloning in Progress** 🎨",
            description=f"Cloning {len(emojis_to_clone)} emojis...\n\n`[░░░░░░░░░░] 0%`",
            color=EMBED_COLOR
        )
        progress_message = await ctx.send(embed=progress_embed)

        successful = 0
        failed = 0

        for i, emoji_data in enumerate(emojis_to_clone):
            try:
                percent = int((i / len(emojis_to_clone)) * 100)
                progress_bar = self.create_progress_bar(percent)

                progress_embed.description = (
                    f"Cloning {len(emojis_to_clone)} emojis...\n\n"
                    f"`{progress_bar} {percent}%`\n"
                    f"✅ **Successful:** {successful}\n"
                    f"❌ **Failed:** {failed}"
                )
                await progress_message.edit(embed=progress_embed)

                async with aiohttp.ClientSession() as session:
                    async with session.get(emoji_data['url']) as resp:
                        if resp.status != 200:
                            failed += 1
                            continue
                        emoji_bytes = await resp.read()

                if emoji_data.get('name'):
                    emoji_name = emoji_data['name']
                else:
                    emoji_name = f"emoji_{emoji_data['id']}"

                await ctx.guild.create_custom_emoji(
                    name=emoji_name,
                    image=emoji_bytes,
                    reason=f"Bulk cloned by {ctx.author}"
                )
                successful += 1

                await asyncio.sleep(0.5)

            except Exception:
                failed += 1
                continue

        progress_embed.title = "✅ **Bulk Cloning Complete** ✅"
        progress_embed.description = (
            f"**Results:**\n"
            f"✅ **Successful:** {successful}\n"
            f"❌ **Failed:** {failed}\n"
            f"⏭️ **Skipped:** {len(emojis) - len(emojis_to_clone)}\n\n"
            f"*Check server emoji list to see the new emojis.*"
        )
        progress_embed.color = 0x2ecc71
        await progress_message.edit(embed=progress_embed)

    def create_progress_bar(self, percent: int, length: int = 10) -> str:
        filled = int(length * (percent / 100))
        empty = length - filled
        return f"[{'█' * filled}{'░' * empty}]"

    async def start_interactive_session(self, ctx):
        EMBED_COLOR = 0x2b2d31

        mutual_servers = []
        for guild in self.bot.guilds:
            if guild.get_member(ctx.author.id):
                mutual_servers.append(guild)

        if not mutual_servers:
            embed = discord.Embed(
                title="❌ No Mutual Servers",
                description="You need to share servers with the bot to use interactive mode.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed)
            return

        self.active_sessions[ctx.author.id] = {
            'current_server_index': 0,
            'selected_emojis': [],
            'mutual_servers': mutual_servers
        }

        await self.show_server_emojis(ctx, 0)

    async def show_server_emojis(self, ctx, server_index: int):
        session = self.active_sessions[ctx.author.id]
        server = session['mutual_servers'][server_index]

        EMBED_COLOR = 0x2b2d31

        static_emojis = [e for e in server.emojis if not e.animated]
        animated_emojis = [e for e in server.emojis if e.animated]

        embed = discord.Embed(
            title=f"🎨 {server.name} Emojis",
            description=(
                f"**Static Emojis:** {len(static_emojis)}/{server.emoji_limit//2}\n"
                f"**Animated Emojis:** {len(animated_emojis)}/{server.emoji_limit//2}\n\n"
                f"*Select emojis to clone using the buttons below.*"
            ),
            color=EMBED_COLOR
        )

        sample_static = " ".join(str(e) for e in static_emojis[:10])
        sample_animated = " ".join(str(e) for e in animated_emojis[:10])

        if sample_static:
            embed.add_field(name="Sample Static", value=sample_static, inline=False)
        if sample_animated:
            embed.add_field(name="Sample Animated", value=sample_animated, inline=False)

        embed.set_footer(text=f"Page {server_index + 1}/{len(session['mutual_servers'])} | Selected: {len(session['selected_emojis'])}")

        view = self.create_server_view(ctx, server_index)
        await ctx.send(embed=embed, view=view)

    def create_server_view(self, ctx, server_index: int) -> discord.ui.View:
        view = discord.ui.View(timeout=180)
        session = self.active_sessions[ctx.author.id]

        if server_index > 0:
            async def prev_callback(interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized!", ephemeral=True)
                    return

                session['current_server_index'] -= 1
                await interaction.response.defer()
                await self.show_server_emojis(ctx, session['current_server_index'])

            prev_button = discord.ui.Button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
            prev_button.callback = prev_callback
            view.add_item(prev_button)

        if server_index < len(session['mutual_servers']) - 1:
            async def next_callback(interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("You are not authorized!", ephemeral=True)
                    return

                session['current_server_index'] += 1
                await interaction.response.defer()
                await self.show_server_emojis(ctx, session['current_server_index'])

            next_button = discord.ui.Button(label="Next ➡️", style=discord.ButtonStyle.secondary)
            next_button.callback = next_callback
            view.add_item(next_button)

        async def select_all_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not authorized!", ephemeral=True)
                return

            server = session['mutual_servers'][server_index]
            for emoji in server.emojis:
                emoji_data = {
                    'type': 'custom',
                    'id': emoji.id,
                    'name': emoji.name,
                    'animated': emoji.animated,
                    'url': str(emoji.url)
                }
                if emoji_data not in session['selected_emojis']:
                    session['selected_emojis'].append(emoji_data)

            await interaction.response.send_message(
                f"✅ Added all {len(server.emojis)} emojis from {server.name} to selection.",
                ephemeral=True
            )

        select_all_button = discord.ui.Button(label="📥 Select All", style=discord.ButtonStyle.primary)
        select_all_button.callback = select_all_callback
        view.add_item(select_all_button)

        async def browse_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not authorized!", ephemeral=True)
                return

            await interaction.response.defer()
            await self.show_detailed_emoji_list(ctx, server_index)

        browse_button = discord.ui.Button(label="🔍 Browse All", style=discord.ButtonStyle.primary)
        browse_button.callback = browse_callback
        view.add_item(browse_button)

        async def clone_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not authorized!", ephemeral=True)
                return

            if not session['selected_emojis']:
                await interaction.response.send_message("No emojis selected!", ephemeral=True)
                return

            await interaction.response.defer()
            await self.process_emoji_cloning(ctx, session['selected_emojis'])

            if ctx.author.id in self.active_sessions:
                del self.active_sessions[ctx.author.id]

        clone_button = discord.ui.Button(label="🚀 Clone Selected", style=discord.ButtonStyle.success,
                                        disabled=len(session['selected_emojis']) == 0)
        clone_button.callback = clone_callback
        view.add_item(clone_button)

        async def cancel_callback(interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("You are not authorized!", ephemeral=True)
                return

            if ctx.author.id in self.active_sessions:
                del self.active_sessions[ctx.author.id]

            embed = discord.Embed(
                title="❌ Session Cancelled",
                description="Interactive emoji session cancelled.",
                color=0x2b2d31
            )
            await interaction.response.edit_message(embed=embed, view=None)

        cancel_button = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.danger)
        cancel_button.callback = cancel_callback
        view.add_item(cancel_button)

        return view

    async def show_detailed_emoji_list(self, ctx, server_index: int):
        EMBED_COLOR = 0x2b2d31
        session = self.active_sessions[ctx.author.id]
        server = session['mutual_servers'][server_index]

        emojis = list(server.emojis)
        items_per_page = 15
        pages = max(1, (len(emojis) + items_per_page - 1) // items_per_page)

        class EmojiPaginator(discord.ui.View):
            def __init__(self, embed_color):
                super().__init__(timeout=180)
                self.current_page = 0
                self.emojis = emojis
                self.items_per_page = items_per_page
                self.total_pages = pages
                self.selected_emojis = session['selected_emojis']
                self.embed_color = embed_color

            async def create_embed(self):
                start = self.current_page * self.items_per_page
                end = start + self.items_per_page

                embed = discord.Embed(
                    title=f"🎨 {server.name} - All Emojis",
                    description=f"Page {self.current_page + 1}/{self.total_pages}",
                    color=self.embed_color
                )

                emoji_list = []
                for i, emoji in enumerate(self.emojis[start:end], start=start + 1):
                    is_selected = any(e['id'] == emoji.id for e in self.selected_emojis)
                    status = "✅" if is_selected else "⬜"
                    emoji_list.append(f"{status} {i}. {emoji} `:{emoji.name}:`")

                if emoji_list:
                    embed.add_field(name="Emojis", value="\n".join(emoji_list), inline=False)

                embed.set_footer(text=f"Total: {len(self.emojis)} | Selected: {len(self.selected_emojis)}")
                return embed

            @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary, disabled=True, row=0)
            async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Unauthorized!", ephemeral=True)

                self.current_page -= 1
                button.disabled = self.current_page == 0
                self.next.disabled = False
                await interaction.response.edit_message(embed=await self.create_embed(), view=self)

            @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary, disabled=pages <= 1, row=0)
            async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Unauthorized!", ephemeral=True)

                self.current_page += 1
                button.disabled = self.current_page == self.total_pages - 1
                self.prev.disabled = False
                await interaction.response.edit_message(embed=await self.create_embed(), view=self)

            @discord.ui.button(label="Select All", style=discord.ButtonStyle.success, row=1)
            async def select_all(self, interaction: discord.Interaction, _: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Unauthorized!", ephemeral=True)

                start = self.current_page * self.items_per_page
                end = start + self.items_per_page

                for emoji in self.emojis[start:end]:
                    emoji_data = {
                        'type': 'custom',
                        'id': emoji.id,
                        'name': emoji.name,
                        'animated': emoji.animated,
                        'url': str(emoji.url)
                    }
                    if not any(e['id'] == emoji.id for e in self.selected_emojis):
                        self.selected_emojis.append(emoji_data)

                session['selected_emojis'] = self.selected_emojis
                await interaction.response.edit_message(embed=await self.create_embed(), view=self)

            @discord.ui.button(label="Deselect All", style=discord.ButtonStyle.danger, row=1)
            async def deselect_all(self, interaction: discord.Interaction, _: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Unauthorized!", ephemeral=True)

                start = self.current_page * self.items_per_page
                end = start + self.items_per_page

                page_emoji_ids = {emoji.id for emoji in self.emojis[start:end]}
                self.selected_emojis = [e for e in self.selected_emojis if e['id'] not in page_emoji_ids]
                session['selected_emojis'] = self.selected_emojis

                await interaction.response.edit_message(embed=await self.create_embed(), view=self)

            @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, row=2)
            async def back(self, interaction: discord.Interaction, _: discord.ui.Button):
                if interaction.user != ctx.author:
                    return await interaction.response.send_message("Unauthorized!", ephemeral=True)

                await interaction.response.defer()
                for child in self.children:
                    child.disabled = True
                await interaction.message.edit(view=self)
                self.stop()
                await self_outer.show_server_emojis(ctx, server_index)

        self_outer = self
        view = EmojiPaginator(EMBED_COLOR)
        embed = await view.create_embed()
        await ctx.send(embed=embed, view=view)

    async def browse_server_emojis(self, ctx, server_id: int):
        EMBED_COLOR = 0x2b2d31
        server = self.bot.get_guild(server_id)

        if not server:
            embed = discord.Embed(
                title="❌ Server Not Found",
                description=f"Could not find server with ID `{server_id}`.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed)
            return

        if server not in self.bot.guilds:
            embed = discord.Embed(
                title="❌ Bot Not in Server",
                description="The bot must be in the server to browse its emojis.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed)
            return

        static_emojis = [e for e in server.emojis if not e.animated]
        animated_emojis = [e for e in server.emojis if e.animated]

        embed = discord.Embed(
            title=f"🎨 {server.name} Emojis",
            description=(
                f"**Static Emojis:** {len(static_emojis)}\n"
                f"**Animated Emojis:** {len(animated_emojis)}\n\n"
                f"Use `!cloneemoji <emoji1> <emoji2>` to clone specific emojis."
            ),
            color=EMBED_COLOR
        )

        if static_emojis:
            sample_static = " ".join(str(e) for e in static_emojis[:15])
            embed.add_field(name="Static Emojis", value=sample_static, inline=False)

        if animated_emojis:
            sample_animated = " ".join(str(e) for e in animated_emojis[:15])
            embed.add_field(name="Animated Emojis", value=sample_animated, inline=False)

        embed.set_footer(text=f"Server ID: {server.id}")
        await ctx.send(embed=embed)

    async def clone_from_user(self, ctx, user_id: int):
        user = self.bot.get_user(user_id)

        if not user:
            embed = discord.Embed(
                title="❌ User Not Found",
                description=f"Could not find user with ID `{user_id}`.",
                color=0x2b2d31
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="🎨 Scanning User Messages",
            description=f"Searching for emojis in {user}'s recent messages...",
            color=0x2b2d31
        )
        message = await ctx.send(embed=embed)

        found_emojis = []
        for channel in ctx.guild.text_channels:
            try:
                async for msg in channel.history(limit=100):
                    if msg.author.id == user_id:
                        emojis = await self.parse_emoji_input(msg.content)
                        for emoji in emojis:
                            if emoji not in found_emojis:
                                found_emojis.append(emoji)
            except Exception:
                continue

        embed.description = f"Found {len(found_emojis)} unique emojis from {user}'s messages."
        await message.edit(embed=embed)

        await asyncio.sleep(1)
        await self.process_emoji_cloning(ctx, found_emojis)

    @commands.command(
        name="emojilist",
        aliases=["listemojis", "serveremojis"],
        brief="List server emojis",
        help="List all emojis in the current server with pagination."
    )
    async def list_server_emojis(self, ctx):
        static_emojis = [e for e in ctx.guild.emojis if not e.animated]
        animated_emojis = [e for e in ctx.guild.emojis if e.animated]

        embed = discord.Embed(
            title=f"🎨 {ctx.guild.name} Emojis",
            description=(
                f"**Static:** {len(static_emojis)}/{ctx.guild.emoji_limit//2}\n"
                f"**Animated:** {len(animated_emojis)}/{ctx.guild.emoji_limit//2}\n"
                f"**Total:** {len(ctx.guild.emojis)}/{ctx.guild.emoji_limit}\n\n"
                f"*Use `!cloneemoji` to add more emojis.*"
            ),
            color=0x2b2d31,
            timestamp=discord.utils.utcnow()
        )

        if static_emojis:
            sample_static = " ".join(str(e) for e in static_emojis[:20])
            embed.add_field(name="Static Emojis", value=sample_static or "None", inline=False)

        if animated_emojis:
            sample_animated = " ".join(str(e) for e in animated_emojis[:20])
            embed.add_field(name="Animated Emojis", value=sample_animated or "None", inline=False)

        embed.set_footer(text=f"Server ID: {ctx.guild.id}")
        await ctx.send(embed=embed)

    @clone_emoji.error
    async def clone_emoji_error(self, ctx, error):
        EMBED_COLOR = 0x2b2d31

        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="You need **Manage Emojis** permissions to use this command!",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=10)

        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                title="❌ Bot Missing Permissions",
                description="I need **Manage Emojis** permission to add emojis!",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=10)

        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="⏰ Command on Cooldown",
                description=f"Please wait `{error.retry_after:.1f}` seconds before cloning emojis again.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed, delete_after=error.retry_after)


async def setup(bot):
    await bot.add_cog(EmojiCloneCog(bot))