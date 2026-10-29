import discord
from discord.ext import commands
import sqlite3
import time
import random
from contextlib import closing
import logging
from typing import Optional, Tuple


class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = self._get_connection("AetherX.db")
        self.cooldowns = {}

    def _get_connection(self, db_path: str):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.commit()
        return conn

    def _init_server_table(self, guild_id: int):
        if not isinstance(guild_id, int):
            raise ValueError("guild_id must be an integer")
        with closing(self.db.cursor()) as cursor:
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS server_{guild_id} (
                    user_id INTEGER PRIMARY KEY,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    last_message_time INTEGER DEFAULT 0
                )
            """)
            self.db.commit()

    def _get_user_data(self, user_id: int, guild_id: int) -> Optional[Tuple[int, int]]:
        self._init_server_table(guild_id)
        with closing(self.db.cursor()) as cursor:
            cursor.execute(f"""
                SELECT xp, level FROM server_{guild_id}
                WHERE user_id = ?
            """, (user_id,))
            return cursor.fetchone()

    def _update_user_data(self, user_id: int, xp: int, level: int, guild_id: int) -> bool:
        try:
            self._init_server_table(guild_id)
            with closing(self.db.cursor()) as cursor:
                cursor.execute(f"SELECT 1 FROM server_{guild_id} WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    cursor.execute(f"""
                        UPDATE server_{guild_id}
                        SET xp = ?, level = ?
                        WHERE user_id = ?
                    """, (xp, level, user_id))
                else:
                    cursor.execute(f"""
                        INSERT INTO server_{guild_id} (user_id, xp, level)
                        VALUES (?, ?, ?)
                    """, (user_id, xp, level))
                self.db.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"Database error in _update_user_data: {e}")
            return False

    def _xp_for_level(self, level: int) -> int:
        return 100 * (max(level, 1) ** 2)

    def _award_dabloons(self, user_id: int, amount: int):
        try:
            with closing(self.db.cursor()) as cursor:
                cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
                if cursor.fetchone():
                    cursor.execute(
                        "UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?",
                        (amount, user_id),
                    )
                    self.db.commit()
                else:
                    logging.error(f"{user_id} is not in users; no dabloons awarded")
        except sqlite3.Error as e:
            logging.error(f"Database error in _award_dabloons: {e}")

    def add_xp(self, user_id: int, guild_id: int, amount: int) -> Tuple[Optional[int], Optional[int]]:
        try:
            server_data = self._get_user_data(user_id, guild_id)
            levels_gained = 0
            if server_data:
                xp, level = server_data
                new_xp = xp + amount
                new_level = level
                while new_xp >= self._xp_for_level(new_level):
                    new_xp -= self._xp_for_level(new_level)
                    new_level += 1
                    levels_gained += 1
            else:
                new_xp = amount
                new_level = 1

            if not self._update_user_data(user_id, new_xp, new_level, guild_id):
                return None, None

            if levels_gained > 0:
                self._award_dabloons(user_id, 10 * levels_gained)

            return new_level, new_xp
        except sqlite3.Error as e:
            logging.error(f"Database error in add_xp: {e}", exc_info=True)
            return None, None
        except Exception as e:
            logging.error(f"Error in add_xp: {e}", exc_info=True)
            return None, None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id
        current_time = time.time()
        key = (guild_id, user_id)

        last_time = self.cooldowns.get(key, 0)
        if current_time - last_time < 60:
            return

        try:
            xp_gain = random.randint(10, 20)
            new_level, new_xp = self.add_xp(user_id, guild_id, xp_gain)
            if new_level is not None:
                self.cooldowns[key] = current_time
                with closing(self.db.cursor()) as cursor:
                    cursor.execute(f"""
                        UPDATE server_{guild_id} SET last_message_time = ?
                        WHERE user_id = ?
                    """, (int(current_time), user_id))
                    self.db.commit()
        except Exception as e:
            logging.error(f"Error in on_message XP handling: {e}", exc_info=True)

    @commands.command(name="rank")
    @commands.guild_only()
    async def rank(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        if user is None:
            user = ctx.author if isinstance(ctx.author, discord.Member) else None
        if user is None:
            await ctx.send("❌ Unable to determine the member's rank.")
            return

        try:
            data = self._get_user_data(user.id, ctx.guild.id)
            if data:
                xp, level = data
                needed_xp = self._xp_for_level(level)
                embed = discord.Embed(title=f"{user.display_name}'s Rank", color=discord.Color.blue())
                embed.add_field(name="Level", value=level, inline=True)
                embed.add_field(name="XP", value=f"{xp}/{needed_xp}", inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)
            else:
                embed = discord.Embed(
                    title=f"{user.display_name}'s Rank",
                    description="No XP data yet! Keep chatting to earn XP.",
                    color=discord.Color.dark_grey(),
                )
            await ctx.send(embed=embed)
        except Exception as e:
            logging.error(f"Error in rank command: {e}", exc_info=True)
            await ctx.send("❌ An error occurred while fetching rank data.")

    @commands.command(name="xpgive")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def xpgive(self, ctx: commands.Context, user: discord.Member, amount: int):
        if amount <= 0:
            await ctx.send("❌ Amount must be positive!")
            return

        try:
            new_level, new_xp = self.add_xp(user.id, ctx.guild.id, amount)
            if new_level is not None:
                embed = discord.Embed(
                    title=f"🎉 {user.display_name} gained {amount} XP!",
                    color=discord.Color.green(),
                )
                embed.add_field(name="New Level", value=new_level, inline=True)
                embed.add_field(
                    name="XP",
                    value=f"{new_xp}/{self._xp_for_level(new_level)}",
                    inline=True,
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to update XP.")
        except Exception as e:
            logging.error(f"Error in xpgive command: {e}", exc_info=True)
            await ctx.send("❌ An error occurred while giving XP.")

    def cog_unload(self):
        self.db.close()


async def setup(bot):
    await bot.add_cog(XP(bot))