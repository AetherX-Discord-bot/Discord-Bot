import discord
from discord.ext import commands
import sqlite3
from contextlib import closing 
DB_PATH = 'AetherX.db'
class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)

    def _get_top(self, limit):
        with closing(self.db.cursor()) as cursor:
            cursor.execute("SELECT user_id, dabloons FROM users ORDER BY dabloons DESC, user_id ASC LIMIT ?", (limit,))
            return cursor.fetchall()
    def _get_rank(self, user_id):
        with closing(self.db.cursor()) as cursor:
            cursor.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row is None:
                return None
            balance = row[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE dabloons > (SELECT dabloons FROM users WHERE user_id = ?)", (user_id,))
            return cursor.fetchone()[0] + 1, balance
    async def _resolve_user(self, user_id):
        user_id = int(user_id)
        user = self.bot.get_user(user_id)
        if user is not None:
            return user
        try:
            return await self.bot.fetch_user(user_id)
        except (discord.NotFound, discord.HTTPException):
            return None
    async def _resolve_member(self, guild, user_id):
        user_id = int(user_id)
        member = guild.get_member(user_id)
        if member is not None:
            return member
        try:
            return await guild.fetch_member(user_id)
        except (discord.NotFound, discord.HTTPException):
            return None
    async def _build_global_embed(self, ctx, limit = 10):
        rows = self._get_top(limit)
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        lines = []
        for i, (user_id, balance) in enumerate(rows):
            user = await self._resolve_user(user_id)
            name = user.name if user else f"Unknown User({user_id})"
            prefix = medals.get(i, f"**#{i + 1}**")
            lines.append(f"{prefix} {name} - **{balance}** dabloons")
        em = discord.Embed(color=discord.Color.gold(), title="🌍 Global Dabloon Leaderboard", description="\n".join(lines) if lines else "No one has any dabloons yet!",)
        rank_info = self._get_rank(ctx.author.id)
        if rank_info:
            rank, balance = rank_info
            em.set_footer(text=f"Your rank: #{rank} - {balance:,} dabloons")
        else:
            em.set_footer(text="You're not on the leaderboard yet!")
        return em
    async def _build_server_embed(self, ctx, limit=10):
        rows = self._get_top(limit * 5)
        medals = {0: "🥇", 1: "🥈", 2: "🥉"}
        entries = []
        for user_id, balance in rows:
            member = await self._resolve_member(ctx.guild, user_id)
            if member is not None:
                entries.append((member, balance))
            if len(entries) >= limit:
                break
        lines = []
        for i, (member, balance) in enumerate(entries):
            prefix = medals.get(i, f"**#{i + 1}**")
            lines.append(f"{prefix} {member.display_name} — **{balance:,}** dabloons")
        em = discord.Embed(
            color=discord.Color.blurple(),
            title=f"🏠 {ctx.guild.name} Leaderboard",
            description="\n".join(lines) if lines else "No one here has any dabloons yet!",
        )
        rank_info = self._get_rank(ctx.author.id)
        if rank_info:
            rank, balance = rank_info
            em.set_footer(text=f"Your global rank: #{rank} — {balance:,} dabloons")
        return em
    @commands.hybrid_command(name="lb", aliases=["Leaderboard", "top"])
    @commands.cooldown(1,10, commands.BucketType.user)
    async def leaderboard(self, ctx, scope: str = 'global'):
        scope = scope.lower()
        if scope in ('server', 'guild', 'local'):
            if ctx.guild is None:
                return await ctx.send("the server leaderboard can only be used in a server.")
            embed = await self._build_server_embed(ctx)
        elif scope in ('global', 'all'):
            embed = await self._build_global_embed(ctx)
        else:
            return await ctx.send("Usage: `!lb [global|server]`")
        await ctx.send(embed=embed)

    def cog_unload(self):
        self.db.close()


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))