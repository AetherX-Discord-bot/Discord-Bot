import discord
from discord.ext import commands
import random

class Games(commands.Cog):
    """A cog to handle various games like coinflip, roll, and blackjack."""
    def __init__(self, bot):
        self.bot = bot
        self.config = getattr(bot, 'config', {})

    @commands.hybrid_command(name="coinflip", aliases=["cf"])
    async def coinflip(self, ctx):
        """Flip a coin!"""
        result = random.choice(["Heads", "Tails"])
        await ctx.send(f"🪙 The coin landed on: **{result}**!")

    @commands.hybrid_command(name="roll")
    async def roll(self, ctx, sides: int = 6):
        """Roll a die with a specified number of sides (default 6)."""
        if sides < 2:
            await ctx.send("Please provide a number of sides greater than 1.")
            return
        result = random.randint(1, sides)
        await ctx.send(f"🎲 You rolled a **{result}** (1-{sides})!")

    @commands.hybrid_command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx, *, mode: str = None):
        """Play a game of Blackjack against the bot. Use 'constant' to play repeatedly until you say stop."""
        constant_mode = (mode is not None and mode.strip().lower() == "constant")
        keep_playing = True
        while keep_playing:
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
                elif hand_value(player) < hand_value(dealer):
                    await ctx.send("Dealer wins!")
                else:
                    await ctx.send("It's a tie!")
            if not constant_mode:
                break
            await ctx.send("Starting a new game! Type `stop` at any time to end constant mode.")

async def setup(bot):
    await bot.add_cog(Games(bot))
