import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import traceback
from contextlib import closing

DB_PATH = 'AetherX.db'


class Slots(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)

    @commands.command(name='slots')
    async def slots(self, ctx, bet: int = None):
        try:
            if bet is None:
                await ctx.send("Please specify a bet amount. Example: `!slots 5`")
                return

            is_special_user = ctx.author.id == 1286383453016686705

            if is_special_user:
                if bet > -1:
                    await ctx.send("The maximum bet is -1. Start collecting your debt boyo.")
                    return
            else:
                if bet < 5:
                    await ctx.send("The minimum bet is 5 dabloons.")
                    return

            max_multiplier = 5
            max_bet = (2**63 - 1) // max_multiplier
            if abs(bet) > max_bet:
                await ctx.send("Bet amount is too large!")
                return

            user_id = ctx.author.id

            with closing(self.db.cursor()) as cursor:
                cursor.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()

                if not row:
                    dabloons = 0
                    cursor.execute("INSERT INTO users (user_id, dabloons) VALUES (?, ?)", (user_id, dabloons))
                    self.db.commit()
                else:
                    dabloons = row[0]

                if is_special_user:
                    if dabloons > bet:
                        await ctx.send("Get more debt, then try")
                        return
                else:
                    if dabloons < bet:
                        await ctx.send("You don't have enough dabloons!")
                        return

                symbols = ['🍎', '🍌', '🍒', '🍇', '🍉']
                loading_symbols = ['🌀', '🎰', '💫', '✨']

                embed = discord.Embed(color=discord.Color.gold(), title=f"{ctx.author.name}'s Slot Machine 🎰")
                embed.description = f"**[ {random.choice(loading_symbols)} | {random.choice(loading_symbols)} | {random.choice(loading_symbols)} ]**"
                embed.set_footer(text="Spinning...")

                message = await ctx.send(embed=embed)

                for i in range(3):
                    await asyncio.sleep(0.5)
                    embed.description = f"**[ {random.choice(symbols)} | {random.choice(symbols)} | {random.choice(symbols)} ]**"
                    await message.edit(embed=embed)
                    await asyncio.sleep(0.5)

                slot1, slot2, slot3 = random.choices(symbols, k=3)
                embed.description = f"**[ {slot1} | {slot2} | {slot3} ]**"

                if slot1 == slot2 == slot3:
                    winnings = bet * max_multiplier
                    embed.add_field(name="🎉 JACKPOT! 🎉", value=f"You won **{winnings}** dabloons!", inline=False)
                elif len({slot1, slot2, slot3}) == 2:
                    winnings = bet * 2
                    embed.add_field(name="✨ Nice win! ✨", value=f"You won **{winnings}** dabloons!", inline=False)
                else:
                    winnings = 0
                    embed.add_field(name="❌ You lost!", value="Better luck next time!", inline=False)

                try:
                    if is_special_user:
                        cursor.execute(
                            "UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?",
                            (winnings, user_id)
                        )
                    else:
                        cursor.execute(
                            "UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?",
                            (winnings - bet, user_id)
                        )

                    self.db.commit()

                    cursor.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
                    new_dabloons = cursor.fetchone()[0]
                    embed.set_footer(text=f"New balance: {new_dabloons} dabloons")

                    await message.edit(embed=embed)

                except sqlite3.Error:
                    await ctx.send("Error updating balance. Please try again.")
                    traceback.print_exc()

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
            traceback.print_exc()

    def cog_unload(self):
        self.db.close()


async def setup(bot):
    await bot.add_cog(Slots(bot))