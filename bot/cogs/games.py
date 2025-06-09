import discord
from discord.ext import commands
import random
import sqlite3
import os
import asyncio

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

    @commands.hybrid_command(alias="hl")
    async def highlow(self, ctx):
        """Play a simple High-Low game. Guess if the next number is higher or lower! Win 5 dabloons if correct."""
        number = random.randint(1, 100)
        embed = discord.Embed(
            title="High-Low Game",
            description=f"The current number is **{number}**. Will the next number be higher or lower? Type `high` or `low`.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["high", "low"]
        try:
            reply = await self.bot.wait_for('message', check=check, timeout=30)
        except Exception:
            await ctx.send("Timed out! Game ended.")
            return
        guess = reply.content.lower()
        next_number = random.randint(1, 100)
        result = None
        if (guess == "high" and next_number > number) or (guess == "low" and next_number < number):
            result = True
        else:
            result = False
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        user_id = ctx.author.id
        if result:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
            c.execute("UPDATE users SET dabloons = dabloons + 5 WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            embed = discord.Embed(
                title="High-Low Result",
                description=f"The next number was **{next_number}**. You guessed **{guess}** and were **correct**!\nYou win 5 dabloons!",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="High-Low Result",
                description=f"The next number was **{next_number}**. You guessed **{guess}** and were **wrong**.\nYou win nothing, but lose nothing!",
                color=discord.Color.gold()
            )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    async def poker(self, ctx, *, mode: str = None):
        """Play a simple 5-player poker game. 5 dabloons to join, 1 chip = 0.01 dabloon. Bots fill empty seats. Cash out for dabloons. If you run out of chips, you're out! Use 'constant' to keep the table running with bots when no humans are present (devs only)."""
        # Poker session state (per guild)
        if not hasattr(self, 'poker_sessions'):
            self.poker_sessions = {}
        guild_id = ctx.guild.id if ctx.guild else ctx.author.id
        session = self.poker_sessions.get(guild_id)
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db'))
        user_id = ctx.author.id
        is_constant = (mode is not None and mode.strip().lower() == "constant")
        # Only devs/owners can start a constant session
        if is_constant:
            config = getattr(self, 'config', getattr(self.bot, 'config', {}))
            owner_ids = config.get('BOT_OWNERS', [])
            developer_ids = config.get('BOT_DEVELOPERS', [])
            all_ids = set(owner_ids + developer_ids)
            if user_id not in all_ids:
                await ctx.send(embed=discord.Embed(description="Only bot developers or owners can start a constant poker session.", color=discord.Color.red()))
                return
        # --- Session Setup ---
        if not session or session.get('ended', False):
            session = {
                'players': [],  # [(user_id, chips, is_bot, user_obj)]
                'queue': [],    # [(user_id, user_obj)]
                'pot': 0,
                'ended': False,
                'constant': is_constant
            }
            if not is_constant:
                # Deduct 5 dabloons to join
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
                c.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
                bal = c.fetchone()[0]
                if bal < 5:
                    await ctx.send(embed=discord.Embed(description="You need at least 5 dabloons to join poker!", color=discord.Color.red()))
                    conn.close()
                    return
                c.execute("UPDATE users SET dabloons = dabloons - 5 WHERE user_id = ?", (user_id,))
                c.execute("UPDATE users SET dabloons = dabloons + 5 WHERE user_id = ?", (self.bot.user.id,))
                conn.commit()
                conn.close()
                session['players'].append((user_id, 500, False, ctx.author))  # 500 chips = 5 dabloons
                # Fill with bots
                for i in range(4):
                    bot_id = f"bot_{i+1}"
                    session['players'].append((bot_id, 500, True, None))
                self.poker_sessions[guild_id] = session
                embed = discord.Embed(title="Poker Game Started!", description=f"Players: 1 human, 4 bots. Each has 500 chips (5 dabloons).", color=discord.Color.green())
                await ctx.send(embed=embed)
            else:
                # Constant mode: all bots
                for i in range(5):
                    bot_id = f"bot_{i+1}"
                    session['players'].append((bot_id, 500, True, None))
                self.poker_sessions[guild_id] = session
                embed = discord.Embed(title="Constant Poker Table Started!", description=f"5 bots are playing. Humans can join at any time.", color=discord.Color.purple())
                await ctx.send(embed=embed)
        else:
            # Session running
            if session.get('constant', False):
                # Constant mode: allow humans to join by swapping with a bot
                if any(p[0] == user_id for p in session['players']):
                    await ctx.send(embed=discord.Embed(description="You are already in the current poker game!", color=discord.Color.gold()))
                    return
                bot_indices = [i for i, p in enumerate(session['players']) if p[2]]
                if bot_indices:
                    idx = bot_indices[0]
                    bot = session['players'][idx]
                    session['players'][idx] = (user_id, 500, False, ctx.author)
                    await ctx.send(embed=discord.Embed(description="A bot has cashed out and you have joined the poker game!", color=discord.Color.green()))
                    # Bank pays out bot's chips
                    chips = bot[1]
                    dabloons = chips * 0.01
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                    conn.commit()
                    conn.close()
                else:
                    await ctx.send(embed=discord.Embed(description="The poker game is full and no bots are present to swap.", color=discord.Color.gold()))
                return
            else:
                # Normal session logic
                if any(p[0] == user_id for p in session['players']):
                    await ctx.send(embed=discord.Embed(description="You are already in the current poker game!", color=discord.Color.gold()))
                    return
                if len(session['players']) < 5:
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
                    c.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
                    bal = c.fetchone()[0]
                    if bal < 5:
                        await ctx.send(embed=discord.Embed(description="You need at least 5 dabloons to join poker!", color=discord.Color.red()))
                        conn.close()
                        return
                    c.execute("UPDATE users SET dabloons = dabloons - 5 WHERE user_id = ?", (user_id,))
                    c.execute("UPDATE users SET dabloons = dabloons + 5 WHERE user_id = ?", (self.bot.user.id,))
                    conn.commit()
                    conn.close()
                    session['players'].append((user_id, 500, False, ctx.author))
                    await ctx.send(embed=discord.Embed(description="You joined the poker game!", color=discord.Color.green()))
                else:
                    if any(q[0] == user_id for q in session['queue']):
                        await ctx.send(embed=discord.Embed(description="You are already in the queue to join the next poker game!", color=discord.Color.gold()))
                        return
                    session['queue'].append((user_id, ctx.author))
                    bot_indices = [i for i, p in enumerate(session['players']) if p[2]]
                    if bot_indices:
                        idx = bot_indices[0]
                        bot = session['players'][idx]
                        session['players'][idx] = (user_id, 500, False, ctx.author)
                        session['queue'].remove((user_id, ctx.author))
                        await ctx.send(embed=discord.Embed(description="A bot has cashed out and you have joined the poker game!", color=discord.Color.green()))
                        chips = bot[1]
                        dabloons = chips * 0.01
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                        conn.commit()
                        conn.close()
                    else:
                        await ctx.send(embed=discord.Embed(description="The poker game is full and no bots are present to swap. You are in the queue.", color=discord.Color.gold()))
                    return
        # --- Poker Game Logic (actual gameplay) ---
        async def play_hand():
            # Each player is dealt 2 cards, 5 community cards, simple winner logic (highest sum)
            deck = [f"{rank}{suit}" for rank in list(map(str, range(2, 11))) + list('JQKA') for suit in '♠♥♦♣']
            random.shuffle(deck)
            hands = {}
            for p in session['players']:
                hands[p[0]] = [deck.pop(), deck.pop()]
            community = [deck.pop() for _ in range(5)]
            # Show hands (bots hidden)
            desc = ""
            for p in session['players']:
                if p[2]:
                    desc += f"[BOT]: ?? ??\n"
                else:
                    desc += f"{p[3].mention}: {hands[p[0]][0]} {hands[p[0]][1]}\n"
            desc += f"\nCommunity Cards: {' '.join(community)}"
            embed = discord.Embed(title="Poker Hand Dealt", description=desc, color=discord.Color.blue())
            await ctx.send(embed=embed)
            # Simple betting: everyone antes 10 chips (0.1 dabloon)
            for i, p in enumerate(session['players']):
                if p[1] >= 10:
                    session['players'][i] = (p[0], p[1] - 10, p[2], p[3])
                    session['pot'] += 10
                else:
                    # Out of chips
                    if p[2]:
                        # Bot cashes out
                        chips = p[1]
                        dabloons = chips * 0.01
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                        conn.commit()
                        conn.close()
                        await ctx.send(embed=discord.Embed(description=f"A bot ran out of chips and cashed out for {dabloons:.2f} dabloons!", color=discord.Color.purple()))
                    else:
                        await ctx.send(embed=discord.Embed(description=f"{p[3].mention} ran out of chips and is out of the game!", color=discord.Color.red()))
                    session['players'][i] = None
            session['players'] = [p for p in session['players'] if p]
            if len(session['players']) < 2:
                await ctx.send(embed=discord.Embed(description="Not enough players to continue. Poker session ended.", color=discord.Color.gold()))
                session['ended'] = True
                return
            # Winner: highest hand value (sum of all card ranks, A=14, K=13, Q=12, J=11)
            def hand_value(cards):
                rank_map = {str(n): n for n in range(2, 11)}
                rank_map.update({'J': 11, 'Q': 12, 'K': 13, 'A': 14})
                return sum(rank_map[c[:-1]] for c in cards)
            best = -1
            winners = []
            for p in session['players']:
                full_hand = hands[p[0]] + community
                val = hand_value(full_hand)
                if val > best:
                    best = val
                    winners = [p]
                elif val == best:
                    winners.append(p)
            # Split pot if tie
            win_chips = session['pot'] // len(winners)
            for winner in winners:
                idx = session['players'].index(winner)
                session['players'][idx] = (winner[0], winner[1] + win_chips, winner[2], winner[3])
            win_mentions = ', '.join([w[3].mention if not w[2] else '[BOT]' for w in winners])
            embed = discord.Embed(title="Poker Hand Result", description=f"Winner(s): {win_mentions}\nPot: {session['pot']} chips ({session['pot']*0.01:.2f} dabloons)\nEach wins {win_chips} chips!", color=discord.Color.green())
            await ctx.send(embed=embed)
            session['pot'] = 0
        # Main game loop for constant mode
        if session.get('constant', False):
            while not session.get('ended', False):
                await play_hand()
                # Remove bots with 0 chips
                session['players'] = [p for p in session['players'] if p[1] > 0]
                # Refill with bots if needed
                while len(session['players']) < 5:
                    bot_id = f"bot_{random.randint(1000,9999)}"
                    session['players'].append((bot_id, 500, True, None))
                await asyncio.sleep(5)  # Wait before next hand
        else:
            await play_hand()
        # Allow user to cash out or simulate chip loss
        def check(m):
            return m.author.id == user_id and m.channel == ctx.channel and m.content.lower() in ["cashout", "lose"]
        await ctx.send("Type `cashout` to leave and convert chips to dabloons, or `lose` to simulate losing all chips.")
        try:
            reply = await self.bot.wait_for('message', check=check, timeout=60)
        except Exception:
            await ctx.send("Timed out! Poker session ended for you.")
            return
        if reply.content.lower() == "cashout":
            for i, p in enumerate(session['players']):
                if p[0] == user_id:
                    chips = p[1]
                    dabloons = chips * 0.01
                    session['players'].pop(i)
                    conn = sqlite3.connect(db_path)
                    c = conn.cursor()
                    c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (dabloons, user_id))
                    c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                    conn.commit()
                    conn.close()
                    await ctx.send(embed=discord.Embed(description=f"You cashed out for {dabloons:.2f} dabloons!", color=discord.Color.green()))
                    break
        elif reply.content.lower() == "lose":
            for i, p in enumerate(session['players']):
                if p[0] == user_id:
                    session['players'].pop(i)
                    await ctx.send(embed=discord.Embed(description="You lost all your chips and are out of the game!", color=discord.Color.red()))
                    break
        # Remove session if no humans left (unless constant mode)
        if not any(not p[2] for p in session['players']) and not session.get('constant', False):
            session['ended'] = True
            await ctx.send(embed=discord.Embed(description="All human players have left. Poker session ended.", color=discord.Color.gold()))
        self.poker_sessions[guild_id] = session

async def setup(bot):
    await bot.add_cog(Games(bot))
