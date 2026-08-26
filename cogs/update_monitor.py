import os
import asyncio
import sqlite3
import re
from typing import cast
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import aiohttp
import discord
import feedparser
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("AETHERX_GITHUB_TOKEN")
GITLAB_TOKEN = os.getenv("AETHERX_GITLAB_TOKEN")
STEAM_API_KEY = os.getenv("AETHERX_STEAM_API_KEY")

# Debug
if STEAM_API_KEY:
    print(f"[DEBUG] STEAM_API_KEY loaded: {STEAM_API_KEY[:5]}... (first 5 chars)")
else:
    print("[DEBUG] ⚠️ STEAM_API_KEY is EMPTY - check .env file and variable name!")

DATABASE_PATH = "AetherX.db"
SOURCE_TYPES = ["github", "gitlab", "steam", "rss"]


class UpdateMonitorCog(commands.Cog, name="Update Monitor"):
    """
    Monitors GitHub, GitLab, Steam, and RSS feeds for updates.
    - API keys are loaded from environment variables (.env file).
    - No keys required (falls back gracefully).
    - Hourly background checks.
    - Auto-creates webhooks or sends as bot messages.
    - All notification embeds are Dark Blue.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DATABASE_PATH
        self.session = aiohttp.ClientSession()
        self._init_db()
        self.monitor_task.start()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                webhook_url TEXT,
                source_type TEXT NOT NULL,
                source_identifier TEXT NOT NULL,
                last_known_state TEXT,
                added_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_source ON subscriptions (source_type, source_identifier)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_guild ON subscriptions (guild_id)")
        conn.commit()
        conn.close()

    async def _db_execute(self, query: str, params: tuple = (), fetch: bool = False):
        def _execute():
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(query, params)
            result = c.fetchall() if fetch else None
            conn.commit()
            conn.close()
            return result
        return await asyncio.to_thread(_execute)

    async def _fetch_github_release(self, repo: str) -> Optional[Dict[str, Any]]:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "id": str(data["id"]),
                        "tag": data["tag_name"],
                        "name": data["name"] or data["tag_name"],
                        "body": data["body"][:500] if data["body"] else "No description provided.",
                        "url": data["html_url"],
                        "published_at": data["published_at"]
                    }
                elif resp.status == 404:
                    return None
                elif resp.status == 403 and "rate limit" in await resp.text():
                    print("[UpdateMonitor] GitHub rate limit reached. Try adding a token.")
                    return None
                else:
                    return None
        except Exception as e:
            print(f"[UpdateMonitor] GitHub fetch error: {e}")
            return None

    async def _fetch_gitlab_release(self, repo: str) -> Optional[Dict[str, Any]]:
        encoded_repo = repo.replace("/", "%2F")
        url = f"https://gitlab.com/api/v4/projects/{encoded_repo}/releases/latest"
        headers = {}
        if GITLAB_TOKEN:
            headers["PRIVATE-TOKEN"] = GITLAB_TOKEN
        try:
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "id": str(data["id"]),
                        "tag": data["tag_name"],
                        "name": data["name"] or data["tag_name"],
                        "body": data.get("description", "No description.")[:500],
                        "url": f"https://gitlab.com/{repo}/-/releases/{data['tag_name']}",
                        "published_at": data["released_at"]
                    }
                elif resp.status == 404:
                    return None
                else:
                    return None
        except Exception as e:
            print(f"[UpdateMonitor] GitLab fetch error: {e}")
            return None

    async def _fetch_steam_news(self, app_id: str) -> Optional[Dict[str, Any]]:
        steam_key = STEAM_API_KEY or os.getenv("AETHERX_STEAM_API_KEY")
        if not steam_key:
            print("[UpdateMonitor] Skipping Steam - no API key set.")
            return None

        url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
        params = {
            "appid": app_id,
            "count": 1,
            "format": "json",
            "key": steam_key
        }
        try:
            async with self.session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    news_items = data.get("appnews", {}).get("newsitems", [])
                    if not news_items:
                        return None
                    item = news_items[0]
                    clean_body = re.sub(r'<[^<]+?>', '', item.get("contents", ""))[:500]
                    return {
                        "id": item["gid"],
                        "tag": item["gid"],
                        "name": item["title"],
                        "body": clean_body or "No details provided.",
                        "url": item["url"],
                        "published_at": datetime.fromtimestamp(item["date"], tz=timezone.utc).isoformat()
                    }
                else:
                    error_text = await resp.text()
                    print(f"[UpdateMonitor] Steam API error {resp.status}: {error_text[:200]}")
                    return None
        except Exception as e:
            print(f"[UpdateMonitor] Steam fetch error: {e}")
            return None

    async def _fetch_rss_feed(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
                feed = feedparser.parse(text)
                if not feed.entries:
                    return None
                entry = feed.entries[0]
                return {
                    "id": entry.get("id") or entry.get("link") or str(datetime.now().timestamp()),
                    "tag": entry.get("id") or entry.get("link"),
                    "name": entry.get("title", "New Update"),
                    "body": (entry.get("summary") or entry.get("description") or "No details.")[:500],
                    "url": entry.get("link"),
                    "published_at": entry.get("published") or entry.get("updated") or datetime.now().isoformat()
                }
        except Exception as e:
            print(f"[UpdateMonitor] RSS fetch error: {e}")
            return None

    async def _fetch_update(self, source_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        if source_type == "github":
            return await self._fetch_github_release(identifier)
        elif source_type == "gitlab":
            return await self._fetch_gitlab_release(identifier)
        elif source_type == "steam":
            return await self._fetch_steam_news(identifier)
        elif source_type == "rss":
            return await self._fetch_rss_feed(identifier)
        return None

    async def _send_update(self, channel_id: int, webhook_url: Optional[str], embed: discord.Embed):
        try:
            if webhook_url:
                webhook = discord.Webhook.from_url(webhook_url, session=self.session)
                await webhook.send(embed=embed, username="AetherX Updates", wait=True)
            else:
                channel = self.bot.get_channel(channel_id)
                if isinstance(channel, discord.abc.Messageable):
                    await cast(discord.abc.Messageable, channel).send(embed=embed)
                else:
                    print(f"[UpdateMonitor] Channel {channel_id} not found.")
        except discord.Forbidden:
            print(f"[UpdateMonitor] Missing permissions to send to channel {channel_id}")
        except Exception as e:
            print(f"[UpdateMonitor] Send error: {e}")

    @tasks.loop(hours=1)
    async def monitor_task(self):
        await self.bot.wait_until_ready()

        print("[UpdateMonitor] Running hourly background check...")
        subscriptions = await self._db_execute(
            "SELECT id, guild_id, channel_id, webhook_url, source_type, source_identifier, last_known_state FROM subscriptions",
            fetch=True
        ) or []

        for sub_id, _, channel_id, webhook_url, src_type, identifier, last_known in subscriptions:
            update_data = await self._fetch_update(src_type, identifier)
            if not update_data:
                continue

            new_state = update_data.get("id") or update_data.get("tag") or str(update_data.get("published_at"))
            if not new_state or new_state == last_known:
                continue

            embed = discord.Embed(
                title=f"🚀 {update_data.get('name', 'New Update')}",
                description=update_data.get("body", ""),
                url=update_data.get("url"),
                color=discord.Color.dark_blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Source", value=f"`{src_type}/{identifier}`", inline=False)
            embed.set_footer(text=f"Subscription ID: {sub_id}")

            await self._send_update(channel_id, webhook_url, embed)

            await self._db_execute(
                "UPDATE subscriptions SET last_known_state = ? WHERE id = ?",
                (new_state, sub_id)
            )
            await asyncio.sleep(0.5)

    @monitor_task.before_loop
    async def before_monitor(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_group(name="update", fallback="help", description="Manage server update subscriptions.")
    async def update_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="📡 Update Monitor Help",
                description="All subscriptions are saved per server.",
                color=discord.Color.dark_blue()
            )
            embed.add_field(
                name="/update subscribe",
                value="`<type> <identifier> #channel [auto_webhook: true/false]`\n"
                      "**Types:** github, gitlab, steam, rss\n"
                      "**Auto-webhook:** If `true`, the bot creates a webhook for you.\n"
                      "**Examples:**\n"
                      "- `github DiscordBot/AetherX #updates` (bot message)\n"
                      "- `steam 730 #game-news true` (auto webhook)",
                inline=False
            )
            embed.add_field(
                name="/update list",
                value="List all subscriptions for this server.",
                inline=False
            )
            embed.add_field(
                name="/update remove",
                value="`<subscription_id>` (Get ID from list).\n"
                      "Requires `Manage Server` or being the one who added it.",
                inline=False
            )
            await ctx.send(embed=embed)

    @update_group.command(name="subscribe", description="Subscribe this server to updates from a source.")
    @app_commands.describe(
        source_type="Type of source (github, gitlab, steam, rss)",
        identifier="Repository, Steam App ID, or RSS URL",
        channel="The channel to send notifications to",
        auto_webhook="If True, the bot creates a webhook for that channel (recommended)"
    )
    async def subscribe(
        self,
        ctx: commands.Context,
        source_type: str,
        identifier: str,
        channel: discord.TextChannel,
        auto_webhook: bool = False
    ):
        if not ctx.guild:
            return await ctx.send("❌ This command must be used in a server.")

        source_type = source_type.lower()
        if source_type not in SOURCE_TYPES:
            return await ctx.send(f"❌ Invalid type. Choose: {', '.join(SOURCE_TYPES)}")

        await ctx.defer(ephemeral=True)

        test_fetch = await self._fetch_update(source_type, identifier)
        if test_fetch is None:
            return await ctx.send(
                f"❌ Could not find any updates for `{identifier}`. "
                "Check spelling or source availability.",
                ephemeral=True
            )

        webhook_url = None
        if auto_webhook:
            try:
                webhook = await channel.create_webhook(name="AetherX Updates")
                webhook_url = webhook.url
                await ctx.send(f"✅ Webhook created in {channel.mention}!", ephemeral=True)
            except discord.Forbidden:
                return await ctx.send(
                    f"❌ I don't have permission to create webhooks in {channel.mention}. "
                    "Either give me `Manage Webhooks` permission, or subscribe without auto_webhook.",
                    ephemeral=True
                )
            except Exception as e:
                return await ctx.send(f"❌ Failed to create webhook: {e}", ephemeral=True)

        await self._db_execute(
            "INSERT INTO subscriptions (guild_id, channel_id, webhook_url, source_type, source_identifier, last_known_state, added_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ctx.guild.id, channel.id, webhook_url, source_type, identifier, None, ctx.author.id)
        )

        latest_state = test_fetch.get("id") or test_fetch.get("tag")
        if latest_state:
            rows = await self._db_execute(
                "SELECT id FROM subscriptions WHERE guild_id = ? AND source_type = ? AND source_identifier = ? ORDER BY id DESC LIMIT 1",
                (ctx.guild.id, source_type, identifier),
                fetch=True
            )
            if rows:
                await self._db_execute(
                    "UPDATE subscriptions SET last_known_state = ? WHERE id = ?",
                    (str(latest_state), rows[0][0])
                )

        delivery = "🔗 Webhook (auto-created)" if auto_webhook else "🤖 Bot message"
        embed = discord.Embed(
            title="✅ Subscription Added!",
            description=f"**Source:** `{source_type}/{identifier}`\n"
                        f"**Channel:** {channel.mention}\n"
                        f"**Delivery:** {delivery}",
            color=discord.Color.dark_blue()
        )
        await ctx.send(embed=embed, ephemeral=True)

    @update_group.command(name="list", description="List all update subscriptions for this server.")
    async def list_subs(self, ctx: commands.Context):
        if not ctx.guild:
            return await ctx.send("❌ This command must be used in a server.")

        rows = await self._db_execute(
            "SELECT id, source_type, source_identifier, channel_id, webhook_url, last_known_state, added_by FROM subscriptions WHERE guild_id = ?",
            (ctx.guild.id,),
            fetch=True
        )
        if not rows:
            return await ctx.send("📭 This server has no active update subscriptions.")

        embed = discord.Embed(
            title=f"📋 Update Subscriptions for {ctx.guild.name}",
            color=discord.Color.dark_blue()
        )
        for sub_id, src_type, identifier, ch_id, webhook, state, added_by in rows:
            delivery = "🔗 Webhook" if webhook else "🤖 Bot"
            latest = state[:30] + "..." if state and len(state) > 30 else (state or "Never checked")
            user = self.bot.get_user(added_by)
            added_by_name = user.display_name if user else f"User ID: {added_by}"
            embed.add_field(
                name=f"ID: {sub_id}",
                value=f"**Source:** `{src_type}/{identifier}`\n"
                      f"**Channel:** <#{ch_id}> ({delivery})\n"
                      f"**Added by:** {added_by_name}\n"
                      f"**Last known:** `{latest}`",
                inline=False
            )
        await ctx.send(embed=embed)

    @update_group.command(name="remove", description="Remove a subscription by its ID.")
    async def remove_sub(self, ctx: commands.Context, subscription_id: int):
        if not ctx.guild:
            return await ctx.send("❌ This command must be used in a server.")

        rows = await self._db_execute(
            "SELECT id, added_by, source_type, source_identifier, webhook_url FROM subscriptions WHERE id = ? AND guild_id = ?",
            (subscription_id, ctx.guild.id),
            fetch=True
        )
        if not rows:
            return await ctx.send("❌ Subscription ID not found in this server.")

        sub = rows[0]
        if (
            ctx.author.id != sub[1]
            and (
                not isinstance(ctx.author, discord.Member)
                or not ctx.author.guild_permissions.manage_guild
            )
        ):
            return await ctx.send("❌ You don't have permission to remove this.")

        if sub[4]:
            try:
                webhooks = await ctx.guild.webhooks()
                for wh in webhooks:
                    if wh.url == sub[4]:
                        await wh.delete()
                        break
            except:
                pass

        await self._db_execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))
        await ctx.send(f"✅ Removed subscription `{sub[2]}/{sub[3]}` (ID: {subscription_id}).")

    async def cog_unload(self):
        self.monitor_task.cancel()
        await self.session.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(UpdateMonitorCog(bot))