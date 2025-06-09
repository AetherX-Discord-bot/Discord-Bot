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
        # --- Poker Game Logic (actual gameplay, DM-based, betting, continue) ---
        async def betting_round(round_name, num_bets, active_players, hands, community_cards, min_bet=10, folded=None, spectators=None, section_bet=False):
            """
            Conducts a betting round for all active players.
            Returns: (updated_active_players, bets_this_round)
            """
            if folded is None:
                folded = set()
            if spectators is None:
                spectators = {}
            bets = {p[0]: 0 for p in active_players}
            actions = {p[0]: [] for p in active_players}  # Track actions for summary
            for bet_num in range(num_bets):
                round_desc = f"**{round_name}** - Betting Round {bet_num+1}/{num_bets}\nCurrent Pot: {session['pot']} chips ({session['pot']*0.01:.2f} dabloons)"
                await ctx.send(embed=discord.Embed(title=f"Poker {round_name} Betting", description=round_desc, color=discord.Color.blurple()))
                round_bet = False  # Track if anyone has bet this round
                for p in list(active_players):
                    if p[0] in folded:
                        if not p[2] and p[0] not in spectators:
                            spectators[p[0]] = p[3]
                        continue
                    if p[2]:
                        # Bot logic: randomly bet, check, or fold (but only check if no one has bet in section)
                        if p[1] < min_bet:
                            bets[p[0]] = 0
                            folded.add(p[0])
                            actions[p[0]].append('folded')
                        else:
                            if not section_bet:
                                action = random.choice(['bet', 'check'])
                                if action == 'bet':
                                    bet_amt = random.randint(min_bet, min(p[1], 100))
                                    bets[p[0]] += bet_amt
                                    actions[p[0]].append(f"bet {bet_amt}")
                                    round_bet = True
                                    section_bet = True
                                else:
                                    actions[p[0]].append('checked')
                            else:
                                # Someone has bet in this section, so must call, raise, or fold
                                action = random.choice(['bet', 'fold'])
                                if action == 'bet':
                                    bet_amt = random.randint(min_bet, min(p[1], 100))
                                    bets[p[0]] += bet_amt
                                    actions[p[0]].append(f"bet {bet_amt}")
                                    round_bet = True
                                    section_bet = True
                                else:
                                    bets[p[0]] = 0
                                    folded.add(p[0])
                                    actions[p[0]].append('folded')
                    else:
                        user = p[3]
                        try:
                            # Only allow check if no one has bet yet in this section
                            allow_check = not section_bet
                            bet_prompt = f"{round_name} - Betting Round {bet_num+1}/{num_bets}\nYour hand: {hands[p[0]][0]} {hands[p[0]][1]}\nCommunity: {' '.join(community_cards) if community_cards else 'None'}\nYou have {p[1]} chips.\nCurrent Pot: {session['pot']} chips ({session['pot']*0.01:.2f} dabloons)\nType your bet ({min_bet}-{p[1]}){' or `check`' if allow_check else ''}, or 'fold'."
                            await user.send(embed=discord.Embed(title="Poker Betting", description=bet_prompt, color=discord.Color.blue()))
                            def bet_check(m):
                                return m.author.id == user.id and isinstance(m.channel, discord.DMChannel)
                            bet_msg = await self.bot.wait_for('message', check=bet_check, timeout=60)
                            if bet_msg.content.lower() == 'fold':
                                bets[p[0]] = 0
                                folded.add(p[0])
                                spectators[p[0]] = user
                                actions[p[0]].append('folded')
                                await user.send(embed=discord.Embed(description=f"You folded this hand. You will rejoin next hand. You are now spectating.", color=discord.Color.gold()))
                            elif bet_msg.content.lower() == 'check' and allow_check:
                                actions[p[0]].append('checked')
                            elif bet_msg.content.lower() == 'check' and not allow_check:
                                await user.send(embed=discord.Embed(description="You cannot check after a bet has been made in this section. Please bet or fold.", color=discord.Color.red()))
                                # Re-prompt
                                return await betting_round(round_name, num_bets-bet_num, [p], hands, community_cards, min_bet, folded, spectators, section_bet)
                            else:
                                try:
                                    bet_amt = int(bet_msg.content)
                                    if bet_amt < min_bet or bet_amt > p[1]:
                                        await user.send("Invalid bet. You are folded this hand.")
                                        bets[p[0]] = 0
                                        folded.add(p[0])
                                        spectators[p[0]] = user
                                        actions[p[0]].append('folded')
                                        await user.send(embed=discord.Embed(description=f"You folded this hand. You will rejoin next hand. You are now spectating.", color=discord.Color.gold()))
                                    else:
                                        bets[p[0]] += bet_amt
                                        actions[p[0]].append(f"bet {bet_amt}")
                                        round_bet = True
                                        section_bet = True
                                except Exception:
                                    await user.send("Invalid input. You are folded this hand.")
                                    bets[p[0]] = 0
                                    folded.add(p[0])
                                    spectators[p[0]] = user
                                    actions[p[0]].append('folded')
                                    await user.send(embed=discord.Embed(description=f"You folded this hand. You will rejoin next hand. You are now spectating.", color=discord.Color.gold()))
                        except Exception:
                            # Timeout or DM error: remove and cash out
                            bets[p[0]] = 0
                            folded.add(p[0])
                            actions[p[0]].append('folded')
                            chips = p[1]
                            dabloons = chips * 0.01
                            try:
                                await user.send(embed=discord.Embed(description=f"You have been removed from the poker game due to inactivity and have cashed out for {dabloons:.2f} dabloons!", color=discord.Color.orange()))
                            except Exception:
                                pass
                            conn = sqlite3.connect(db_path)
                            c = conn.cursor()
                            c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (dabloons, p[0]))
                            c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                            conn.commit()
                            conn.close()
                # Deduct bets and add to pot
                for i, p in enumerate(session['players']):
                    if p[0] not in folded:
                        bet = bets.get(p[0], 0)
                        if bet > 0:
                            session['players'][i] = (p[0], p[1] - bet, p[2], p[3])
                            session['pot'] += bet
                # Announce actions after each round
                action_lines = []
                for p in active_players:
                    if p[0] in folded:
                        action = actions[p[0]][-1] if actions[p[0]] else 'folded'
                    elif actions[p[0]]:
                        action = actions[p[0]][-1]
                    else:
                        action = 'checked'
                    name = p[3].mention if not p[2] else f"[BOT] {p[0]}"
                    action_lines.append(f"{name}: {action}")
                summary = '\n'.join(action_lines)
                embed = discord.Embed(title=f"{round_name} - Betting Round {bet_num+1} Actions", description=summary, color=discord.Color.blurple())
                await ctx.send(embed=embed)
                for user in spectators.values():
                    try:
                        await user.send(embed=embed)
                    except Exception:
                        pass
                # --- Check if only one player remains (all others folded) ---
                remaining = [p for p in active_players if p[0] not in folded]
                if len(remaining) == 1:
                    winner = remaining[0]
                    idx = None
                    # Find the winner in session['players'] by user_id
                    for i, sp in enumerate(session['players']):
                        if sp[0] == winner[0]:
                            idx = i
                            break
                    if idx is not None:
                        session['players'][idx] = (winner[0], winner[1] + session['pot'], winner[2], winner[3])
                    win_mentions = winner[3].mention if not winner[2] else f"[BOT] {winner[0]}"
                    embed = discord.Embed(title="Poker Hand Result", description=f"All other players folded! {win_mentions} wins the pot of {session['pot']} chips ({session['pot']*0.01:.2f} dabloons)", color=discord.Color.green())
                    await ctx.send(embed=embed)
                    for user in spectators.values():
                        try:
                            await user.send(embed=embed)
                        except Exception:
                            pass
                    session['pot'] = 0
                    # End the entire hand/game, not just the section
                    raise StopAsyncIteration  # Custom signal to break out of play_hand_dm
            # Return only non-folded players for this hand
            return [p for p in active_players if p[0] not in folded], bets, folded, spectators, section_bet

        async def play_hand_dm():
            deck = [f"{rank}{suit}" for rank in list(map(str, range(2, 11))) + list('JQKA') for suit in '♠♥♦♣']
            random.shuffle(deck)
            hands = {}
            for p in session['players']:
                hands[p[0]] = [deck.pop(), deck.pop()]
            community = [deck.pop() for _ in range(5)]
            def get_active_players(player_list):
                return [p for p in player_list if p[1] > 0]
            active_players = get_active_players(session['players'])
            folded = set()
            spectators = {}
            try:
                # Pre-flop: 3 betting rounds
                section_bet = False
                active_players, _, folded, spectators, section_bet = await betting_round("Pre-Flop", 3, active_players, hands, [], folded=folded, spectators=spectators, section_bet=section_bet)
                # Reveal flop
                flop = community[:3]
                embed = discord.Embed(title="Poker Flop", description=f"Community Cards: {' '.join(flop)}", color=discord.Color.teal())
                await ctx.send(embed=embed)
                for user in spectators.values():
                    try:
                        await user.send(embed=discord.Embed(title="Poker Flop", description=f"Community Cards: {' '.join(flop)}", color=discord.Color.teal()))
                    except Exception:
                        pass
                await asyncio.sleep(2)
                # Before turn: 2 betting rounds
                section_bet = False
                active_players, _, folded, spectators, section_bet = await betting_round("Before Turn", 2, active_players, hands, flop, folded=folded, spectators=spectators, section_bet=section_bet)
                # Reveal turn
                turn = community[3]
                embed = discord.Embed(title="Poker Turn", description=f"Community Cards: {' '.join(flop)} {turn}", color=discord.Color.teal())
                await ctx.send(embed=embed)
                for user in spectators.values():
                    try:
                        await user.send(embed=discord.Embed(title="Poker Turn", description=f"Community Cards: {' '.join(flop)} {turn}", color=discord.Color.teal()))
                    except Exception:
                        pass
                await asyncio.sleep(2)
                # Before river: 1 betting round
                section_bet = False
                active_players, _, folded, spectators, section_bet = await betting_round("Before River", 1, active_players, hands, flop + [turn], folded=folded, spectators=spectators, section_bet=section_bet)
                # Reveal river
                river = community[4]
                embed = discord.Embed(title="Poker River", description=f"Community Cards: {' '.join(flop)} {turn} {river}", color=discord.Color.teal())
                await ctx.send(embed=embed)
                for user in spectators.values():
                    try:
                        await user.send(embed=discord.Embed(title="Poker River", description=f"Community Cards: {' '.join(flop)} {turn} {river}", color=discord.Color.teal()))
                    except Exception:
                        pass
                await asyncio.sleep(2)
                # After river: 3 betting rounds
                section_bet = False
                active_players, _, folded, spectators, section_bet = await betting_round("After River", 3, active_players, hands, flop + [turn, river], folded=folded, spectators=spectators, section_bet=section_bet)
            except StopAsyncIteration:
                # End the hand immediately if only one player remains
                return
            # Remove/cash out only players with 0 chips or who timed out (not just folded)
            leavers = []
            for i, p in enumerate(session['players']):
                if p[1] <= 0:
                    if p[2]:
                        chips = p[1]
                        dabloons = chips * 0.01
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                        conn.commit()
                        conn.close()
                        leavers.append(f"[BOT] {p[0]} (cashed out for {dabloons:.2f} dabloons)")
                    else:
                        chips = p[1]
                        dabloons = chips * 0.01
                        leavers.append(f"{p[3].mention} (cashed out for {dabloons:.2f} dabloons)")
                        try:
                            await p[3].send(embed=discord.Embed(description=f"You ran out of chips and have cashed out for {dabloons:.2f} dabloons!", color=discord.Color.green()))
                        except Exception:
                            pass
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (dabloons, p[0]))
                        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                        conn.commit()
                        conn.close()
            if leavers:
                await ctx.send(embed=discord.Embed(title="Players Left This Hand", description="\n".join(leavers), color=discord.Color.red()))
            def hand_value(cards):
                rank_map = {str(n): n for n in range(2, 11)}
                rank_map.update({'J': 11, 'Q': 12, 'K': 13, 'A': 14})
                return sum(rank_map[c[:-1]] for c in cards)
            best = -1
            winners = []
            for p in [p for p in active_players if p[0] not in folded]:
                full_hand = hands[p[0]] + community
                val = hand_value(full_hand)
                if val > best:
                    best = val
                    winners = [p]
                elif val == best:
                    winners.append(p)
            if not winners:
                await ctx.send(embed=discord.Embed(description="No winners this hand. Pot carries over.", color=discord.Color.gold()))
                for user in spectators.values():
                    try:
                        await user.send(embed=discord.Embed(description="No winners this hand. Pot carries over.", color=discord.Color.gold()))
                    except Exception:
                        pass
                return
            win_chips = session['pot'] // len(winners)
            for winner in winners:
                idx = session['players'].index(winner)
                session['players'][idx] = (winner[0], winner[1] + win_chips, winner[2], winner[3])
            win_mentions = ', '.join([w[3].mention if not w[2] else '[BOT]' for w in winners])
            embed = discord.Embed(title="Poker Hand Result", description=f"Winner(s): {win_mentions}\nPot: {session['pot']} chips ({session['pot']*0.01:.2f} dabloons)\nEach wins {win_chips} chips!", color=discord.Color.green())
            await ctx.send(embed=embed)
            for user in spectators.values():
                try:
                    await user.send(embed=discord.Embed(title="Poker Hand Result", description=f"Winner(s): {win_mentions}\nPot: {session['pot']} chips ({session['pot']*0.01:.2f} dabloons)\nEach wins {win_chips} chips!", color=discord.Color.green()))
                except Exception:
                    pass
            session['pot'] = 0
        # Main game loop for constant mode or DM-based play
        if session.get('constant', False):
            while not session.get('ended', False):
                await play_hand_dm()
                session['players'] = [p for p in session['players'] if p[1] > 0]
                while len(session['players']) < 5:
                    bot_id = f"bot_{random.randint(1000,9999)}"
                    session['players'].append((bot_id, 500, True, None))
                await asyncio.sleep(5)
        else:
            playing = True
            while playing and not session.get('ended', False):
                try:
                    await play_hand_dm()
                except StopAsyncIteration:
                    # Custom signal to break out of the hand loop and end the hand
                    break
                # Remove players with 0 chips
                session['players'] = [p for p in session['players'] if p[1] > 0]
                # DM all humans to ask if they want to continue
                humans = [p for p in session['players'] if not p[2]]
                if not humans:
                    session['ended'] = True
                    await ctx.send(embed=discord.Embed(description="All human players have left. Poker session ended.", color=discord.Color.gold()))
                    break
                continue_votes = 0
                for p in humans:
                    try:
                        await p[3].send("Type 'continue' to play another hand, or anything else to leave.")
                        def cont_check(m):
                            return m.author.id == p[0] and isinstance(m.channel, discord.DMChannel)
                        msg = await self.bot.wait_for('message', check=cont_check, timeout=60)
                        if msg.content.lower() == 'continue':
                            continue_votes += 1
                        else:
                            await p[3].send("You have left the poker game.")
                            # Cash out on leave
                            chips = p[1]
                            dabloons = chips * 0.01
                            await p[3].send(embed=discord.Embed(description=f"You have cashed out for {dabloons:.2f} dabloons!", color=discord.Color.green()))
                            conn = sqlite3.connect(db_path)
                            c = conn.cursor()
                            c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (dabloons, p[0]))
                            c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                            conn.commit()
                            conn.close()
                            session['players'].remove(p)
                    except Exception:
                        # Timeout or DM error: remove and cash out
                        chips = p[1]
                        dabloons = chips * 0.01
                        try:
                            await p[3].send(embed=discord.Embed(description=f"You have been removed from the poker game due to inactivity and have cashed out for {dabloons:.2f} dabloons!", color=discord.Color.orange()))
                        except Exception:
                            pass
                        conn = sqlite3.connect(db_path)
                        c = conn.cursor()
                        c.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (dabloons, p[0]))
                        c.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (dabloons, self.bot.user.id))
                        conn.commit()
                        conn.close()
                        session['players'].remove(p)
            if continue_votes == 0:
                session['ended'] = True
                await ctx.send(embed=discord.Embed(description="All human players have left. Poker session ended.", color=discord.Color.gold()))
                return
        self.poker_sessions[guild_id] = session

async def setup(bot):
    await bot.add_cog(Games(bot))
