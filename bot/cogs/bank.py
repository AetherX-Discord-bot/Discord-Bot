import discord
from discord.ext import commands
import sqlite3
import os

def is_developer_or_owner():
    async def predicate(ctx):
        config = getattr(ctx.bot, 'config', {})
        owner_ids = config.get('BOT_OWNERS', [])
        developer_ids = config.get('BOT_DEVELOPERS', [])
        all_ids = set(owner_ids + developer_ids)
        if await ctx.bot.is_owner(ctx.author):
            return True
        return ctx.author.id in all_ids
    return commands.check(predicate)

def is_bank_teller_or_dev_or_owner():
    async def predicate(ctx):
        config = getattr(ctx.bot, 'config', {})
        bank_tellers = config.get('BANK_TELLERS', [])
        owner_ids = config.get('BOT_OWNERS', [])
        developer_ids = config.get('BOT_DEVELOPERS', [])
        all_ids = set(bank_tellers + owner_ids + developer_ids)
        if await ctx.bot.is_owner(ctx.author):
            return True
        return ctx.author.id in all_ids
    return commands.check(predicate)

class Bank(commands.Cog):
    """A cog for checking and managing your dabloons balance."""
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))

    @commands.hybrid_command(aliases=["bal", "money", "dabloons"])
    async def balance(self, ctx, user: discord.User = None):
        """Check your dabloons balance (or another user's)."""
        user = user or ctx.author
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user.id,))
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (user.id,))
        bal = c.fetchone()[0]
        conn.close()
        await ctx.send(f"💰 {user.display_name} has {bal:.2f} dabloons.")

    @commands.command(alias=["setdabloons"])
    @is_developer_or_owner()
    async def adminsetdabloons(self, ctx, user: discord.User, amount: float):
        """Set a user's dabloons balance."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user.id,))
        c.execute("UPDATE users SET dabloons = ? WHERE user_id = ?", (amount, user.id))
        conn.commit()
        conn.close()
        await ctx.send(f"Set {user.display_name}'s dabloons to {amount:.2f}.")

    @commands.command(alias=["setbank"])
    @is_developer_or_owner()
    async def adddabloonstobank(self, ctx, amount: float):
        """Add dabloons to the bank."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (self.bot.user.id,))
        c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (amount, self.bot.user.id))
        conn.commit()
        conn.close()
        await ctx.send(f"Added {amount:.2f} dabloons to the bank.")

    @commands.command(alias=["loanfrombank"])
    @is_bank_teller_or_dev_or_owner()
    async def loandabloonsfrombank(self, ctx, user: discord.User, amount: float):
        """Loan dabloons to a user (deducts from bank)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (self.bot.user.id,))
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user.id,))
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (self.bot.user.id,))
        bank_balance = c.fetchone()[0]
        if bank_balance < amount:
            await ctx.send("The bank does not have enough dabloons to loan.")
            conn.close()
            return
        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (amount, self.bot.user.id))
        c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (amount, user.id))
        conn.commit()
        conn.close()
        await ctx.send(f"Loaned {amount:.2f} dabloons to {user.display_name}.")

    @commands.hybrid_command(alias=["loantoother"])
    async def loandabloonstoother(self, ctx, user: discord.User, amount: float):
        """Loan dabloons to another user (deducts from your balance)."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (ctx.author.id,))
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user.id,))
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (ctx.author.id,))
        user_balance = c.fetchone()[0]
        if user_balance < amount:
            await ctx.send("You do not have enough dabloons to loan.")
            conn.close()
            return
        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (amount, ctx.author.id))
        c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (amount, user.id))
        conn.commit()
        conn.close()
        await ctx.send(f"Loaned {amount:.2f} dabloons to {user.display_name}.")

async def setup(bot):
    await bot.add_cog(Bank(bot))
