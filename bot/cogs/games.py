import discord
from discord.ext import commands
import random
import sqlite3
import os

class Games(commands.Cog):
    """A cog to handle various games like coinflip, roll, and blackjack."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    @commands.hybrid_command(aliases=["cf"])
    async def coinflip(self, ctx):
        """Flip a coin!"""
        result = random.choice(["Heads", "Tails"])
        if result == "Heads":
            db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
            user_id = ctx.author.id
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
            c.execute("UPDATE users SET dabloons = dabloons + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
        await ctx.send(f"🪙 The coin landed on: **{result}**!")

    @commands.hybrid_command(name="roll")
    async def roll(self, ctx, sides: int = 6):
        """Roll a die with a specified number of sides (default 6)."""
        if sides < 2:
            await ctx.send("Please provide a number of sides greater than 1.")
            return
        result = random.randint(1, sides)
        await ctx.send(f"🎲 You rolled a **{result}** (1-{sides})!")

    @commands.hybrid_command(aliases=["bj"])
    async def blackjack(self, ctx, *, mode: str = None):
        """Play a game of Blackjack against the bot. Use 'constant' to play repeatedly until you say stop. Costs 10 dabloons to play, win 20 dabloons if you win."""
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        user_id = ctx.author.id
        constant_mode = (mode is not None and mode.strip().lower() == "constant")
        keep_playing = True
        while keep_playing:
            # Check and deduct 10 dabloons
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
            c.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
            bal = c.fetchone()[0]
            if bal < 10:
                await ctx.send("You need at least 10 dabloons to play Blackjack!")
                conn.close()
                return
            c.execute("UPDATE users SET dabloons = dabloons - 10 WHERE user_id = ?", (user_id,))
            c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (self.bot.user.id,))
            c.execute("UPDATE users SET dabloons = dabloons + 10 WHERE user_id = ?", (self.bot.user.id,))
            conn.commit()
            conn.close()
            deck = [str(n) for n in range(2, 11)] + list('JQKA')
            deck = deck * 4
            random.shuffle(deck)
            card_values = {**{str(n): n for n in range(2, 11)}, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}
            def hand_value(hand):
                value = sum(card_values[c] for c in hand)
                # Adjust for Aces
                aces = hand.count('A')
                while value > 21 and aces:
                    value -= 10
                    aces -= 1
                return value
            player = [deck.pop(), deck.pop()]
            dealer = [deck.pop(), deck.pop()]
            msg = await ctx.send(f"Your hand: {', '.join(player)} (Total: {hand_value(player)})\nDealer shows: {dealer[0]}")
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['hit', 'stand', 'stop']
            while hand_value(player) < 21:
                await ctx.send("Type `hit` to draw or `stand` to hold." + (" Type `stop` to end constant mode." if constant_mode else ""))
                try:
                    reply = await self.bot.wait_for('message', check=check, timeout=30)
                except Exception:
                    await ctx.send("Timed out! Game ended.")
                    return
                if reply.content.lower() == 'stop' and constant_mode:
                    await ctx.send("Constant mode stopped.")
                    return
                if reply.content.lower() == 'hit':
                    player.append(deck.pop())
                    await ctx.send(f"Your hand: {', '.join(player)} (Total: {hand_value(player)})")
                else:
                    break
            if hand_value(player) > 21:
                await ctx.send("You busted! Dealer wins.")
            else:
                await ctx.send(f"Dealer's hand: {', '.join(dealer)} (Total: {hand_value(dealer)})")
                while hand_value(dealer) < 17:
                    dealer.append(deck.pop())
                    await ctx.send(f"Dealer draws: {dealer[-1]} (Total: {hand_value(dealer)})")
                if hand_value(dealer) > 21 or hand_value(player) > hand_value(dealer):
                    await ctx.send("You win!")
                    # Award 20 dabloons
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    c.execute("UPDATE users SET dabloons = dabloons + 20 WHERE user_id = ?", (user_id,))
                    c.execute("UPDATE users SET dabloons = dabloons - 20 WHERE user_id = ?", (self.bot.user.id,))
                    conn.commit()
                    conn.close()
                elif hand_value(player) < hand_value(dealer):
                    await ctx.send("Dealer wins!")
                else:
                    await ctx.send("It's a tie!")
            if not constant_mode:
                break
            await ctx.send("Starting a new game! Type `stop` at any time to end constant mode.")

    @commands.hybrid_command(aliases=["luckynumbers"])
    async def slots(self, ctx, *, ammount: float = None):
        """Play a slot machine game. Costs 10+ dabloons to play, win more if you hit rare combos!"""
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        user_id = ctx.author.id
        if ammount is None:
            ammount = 10.0
        if ammount < 10:
            embed = discord.Embed(description="You need to bet at least 10 dabloons to play!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
        c.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
        bal = c.fetchone()[0]
        if bal < ammount:
            embed = discord.Embed(description="You do not have enough dabloons to play!", color=discord.Color.red())
            await ctx.send(embed=embed)
            conn.close()
            return
        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (ammount, user_id))
        c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (self.bot.user.id,))
        c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (ammount, self.bot.user.id))
        conn.commit()
        conn.close()

        # Symbol rarity: weights for each symbol
        symbols = ["🍒", "🍋", "🍊", "🍉", "⭐", "💎"]
        weights = [30, 25, 20, 15, 7, 3]  # Common to rare
        result = random.choices(symbols, weights=weights, k=3)
        slot_str = f"🎰 {result[0]} {result[1]} {result[2]}"

        # Payout logic
        payout = 0
        tier = None
        if result[0] == result[1] == result[2]:
            if result[0] == "💎":
                payout = ammount * 10
                tier = "💎 JACKPOT! (10x bet)"
            elif result[0] == "⭐":
                payout = ammount * 5
                tier = "⭐ High Payout! (5x bet)"
            else:
                payout = ammount * 2
                tier = f"Three of a kind! (2x bet)"
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            payout = ammount * 1.5
            tier = "Two of a kind! (1.5x bet)"
        else:
            payout = 0
            tier = None

        # Handle payout
        if payout > 0:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (payout, user_id))
            c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (payout, self.bot.user.id))
            conn.commit()
            conn.close()
            embed = discord.Embed(
                title="Slots Result",
                description=f"{slot_str}\n\n🎉 You won {payout:.2f} dabloons!\n**{tier}**",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="Slots Result",
                description=f"{slot_str}\n\nBetter luck next time!",
                color=discord.Color.gold()
            )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Games(bot))
