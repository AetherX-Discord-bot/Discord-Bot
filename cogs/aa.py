import discord
import sqlite3
from discord.ext import commands

DB_NAME = "AetherX.db"


def _bootstrap():
    conn = sqlite3.connect(DB_NAME)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id          INTEGER PRIMARY KEY,
                bio              TEXT    NOT NULL DEFAULT '',
                favorite_color   TEXT    NOT NULL DEFAULT '#FFFFFF',
                affil            TEXT    NOT NULL DEFAULT 'User',
                allowstatusview  INTEGER NOT NULL DEFAULT 0,
                dabloons         INTEGER NOT NULL DEFAULT 0,
                inventory        TEXT    NOT NULL DEFAULT '{}',
                showlongprofile  INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
    finally:
        conn.close()


_bootstrap()


class Dabloons(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_balance(self, user_id: int) -> int:
        conn = sqlite3.connect(DB_NAME)
        try:
            cur = conn.execute(
                "SELECT dabloons FROM users WHERE user_id = ?", (user_id,)
            )
            row = cur.fetchone()
        finally:
            conn.close()
        return row[0] if row else 0


async def setup(bot):
    await bot.add_cog(Dabloons(bot))