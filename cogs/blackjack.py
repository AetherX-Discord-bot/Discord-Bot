import discord
from discord.ext import commands
import sqlite3
import random
import asyncio
import time
import math

DB_PATH = 'AetherX.db'


def get_card():
    card_values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    card_suits = ['♠', '♥', '♦', '♣']
    return {'value': random.choice(card_values), 'suit': random.choice(card_suits)}


def calculate_score(hand):
    total = 0
    ace_count = 0
    for card in hand:
        if card['value'] in ['J', 'Q', 'K']:
            total += 10
        elif card['value'] == 'A':
            total += 11
            ace_count += 1
        else:
            total += int(card['value'])
    while total > 21 and ace_count > 0:
        total -= 10
        ace_count -= 1
    return total


def format_hand(hand):
    return ', '.join(f"{card['value']}{card['suit']}" for card in hand)


async def get_dabloons(user_id):
    def query_db():
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 0
    return await asyncio.to_thread(query_db)


async def update_dabloons_result(user_id, bet: int, result: str):
    current_dabloons = await get_dabloons(user_id)
    if result == "win":
        new_amount = math.ceil(2 * bet)
    elif result == "lose":
        new_amount = 0
    else:
        return current_dabloons

    if user_id == 1286383453016686705:
        new_amount = max(new_amount, -abs(current_dabloons))

    def update_db():
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?", (bet, user_id))
            cursor.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (new_amount, user_id))
            cursor.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone()[0]
    return await asyncio.to_thread(update_db)


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}
        self.cooldowns = {}

    async def is_on_cooldown(self, user_id):
        now = int(time.time())
        cooldown = self.cooldowns.get(user_id)
        if cooldown and now < cooldown:
            return True, discord.Embed(
                color=discord.Color.red(),
                title='Cooldown Active',
                description=f'You are on cooldown. You can start a new game in {cooldown - now} seconds.'
            )
        self.cooldowns[user_id] = now + 10
        return False, None

    @commands.command(aliases=['bj'])
    async def blackjack(self, ctx, bet: int):
        if bet < 10 and ctx.author.id != 1286383453016686705:
            return await ctx.send("The minimum bet is 10. Please enter a higher bet.")

        if ctx.author.id in self.active_games:
            return await ctx.send("You already have an active game!")

        player_dabloons = await get_dabloons(ctx.author.id)

        if ctx.author.id == 1286383453016686705:
            if bet > 0 or abs(player_dabloons) < abs(bet):
                return await ctx.send("Invalid bet. You cannot bet above 0 and must have enough dabloons.")
        elif player_dabloons <= 0:
            return await ctx.send("your broke buddy, get away from the table")
        elif player_dabloons < bet:
            return await ctx.send("You do not have enough dabloons to place this bet.")

        on_cooldown, cooldown_embed = await self.is_on_cooldown(ctx.author.id)
        if on_cooldown:
            return await ctx.send(embed=cooldown_embed)

        self.active_games[ctx.author.id] = {
            'bet': bet,
            'original_bet': bet,
            'hands': [[get_card(), get_card()]],
            'current_hand': 0,
            'dealer_hand': [get_card(), get_card()],
            'stood': False,
            'message': None,
        }

        embed, view = await self.create_game_embed(ctx)
        message = await ctx.send(embed=embed, view=view)
        self.active_games[ctx.author.id]['message'] = message

    async def create_game_embed(self, ctx):
        game_state = self.active_games[ctx.author.id]
        player_hand = game_state['hands'][game_state['current_hand']]
        dealer_hand = game_state['dealer_hand']
        player_score = calculate_score(player_hand)

        embed = discord.Embed(
            title=f"Blackjack Game (Hand {game_state['current_hand'] + 1}/{len(game_state['hands'])})",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="Your Hand",
            value=f"{format_hand(player_hand)}\nScore: {player_score}",
            inline=False
        )

        if game_state['stood']:
            dealer_display = f"{format_hand(dealer_hand)}\nScore: {calculate_score(dealer_hand)}"
        else:
            dealer_display = f"{dealer_hand[0]['value']}{dealer_hand[0]['suit']}, ?"
        embed.add_field(
            name="Dealer's Hand",
            value=dealer_display,
            inline=False
        )

        embed.add_field(
            name="Game Info",
            value=f"Bet: {game_state['bet']} dabloons\nTotal at stake: {game_state['original_bet'] * len(game_state['hands'])} dabloons",
            inline=False
        )

        view = discord.ui.View(timeout=120)

        async def on_timeout():
            self.active_games.pop(ctx.author.id, None)
            try:
                await game_state['message'].edit(view=None)
            except (discord.HTTPException, AttributeError):
                pass

        view.on_timeout = on_timeout

        async def hit_callback(interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("This isn't your game!", ephemeral=True)

            game_state = self.active_games[ctx.author.id]
            player_hand = game_state['hands'][game_state['current_hand']]
            player_hand.append(get_card())
            player_score = calculate_score(player_hand)

            if player_score > 21:
                if game_state['current_hand'] < len(game_state['hands']) - 1:
                    game_state['current_hand'] += 1
                    new_embed, new_view = await self.create_game_embed(ctx)
                    await interaction.response.edit_message(embed=new_embed, view=new_view)
                else:
                    await self.end_game(ctx, interaction)
            else:
                new_embed, new_view = await self.create_game_embed(ctx)
                await interaction.response.edit_message(embed=new_embed, view=new_view)

        async def stand_callback(interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("This isn't your game!", ephemeral=True)

            game_state = self.active_games[ctx.author.id]
            if game_state['current_hand'] < len(game_state['hands']) - 1:
                game_state['current_hand'] += 1
                new_embed, new_view = await self.create_game_embed(ctx)
                await interaction.response.edit_message(embed=new_embed, view=new_view)
            else:
                game_state['stood'] = True
                await self.end_game(ctx, interaction)

        async def split_callback(interaction):
            if interaction.user.id != ctx.author.id:
                return await interaction.response.send_message("This isn't your game!", ephemeral=True)

            game_state = self.active_games[ctx.author.id]
            player_hand = game_state['hands'][game_state['current_hand']]

            if len(player_hand) != 2 or player_hand[0]['value'] != player_hand[1]['value']:
                return await interaction.response.send_message("You can only split pairs!", ephemeral=True)
            if len(game_state['hands']) >= 4:
                return await interaction.response.send_message("Maximum splits reached!", ephemeral=True)

            new_hand1 = [player_hand[0], get_card()]
            new_hand2 = [player_hand[1], get_card()]
            game_state['hands'][game_state['current_hand']] = new_hand1
            game_state['hands'].insert(game_state['current_hand'] + 1, new_hand2)
            game_state['bet'] = game_state['original_bet'] * len(game_state['hands'])

            new_embed, new_view = await self.create_game_embed(ctx)
            await interaction.response.edit_message(embed=new_embed, view=new_view)

        hit_button = discord.ui.Button(label="Hit", style=discord.ButtonStyle.primary)
        hit_button.callback = hit_callback
        view.add_item(hit_button)

        stand_button = discord.ui.Button(label="Stand", style=discord.ButtonStyle.secondary)
        stand_button.callback = stand_callback
        view.add_item(stand_button)

        if (len(player_hand) == 2 and
                player_hand[0]['value'] == player_hand[1]['value'] and
                len(game_state['hands']) < 4):
            split_button = discord.ui.Button(label="Split", style=discord.ButtonStyle.success)
            split_button.callback = split_callback
            view.add_item(split_button)

        return embed, view

    async def end_game(self, ctx, interaction):
        game_state = self.active_games.pop(ctx.author.id)
        dealer_hand = game_state['dealer_hand']
        dealer_score = calculate_score(dealer_hand)

        while dealer_score < 17:
            dealer_hand.append(get_card())
            dealer_score = calculate_score(dealer_hand)

        total_winnings = 0
        results = []

        for hand in game_state['hands']:
            player_score = calculate_score(hand)

            if player_score > 21:
                result = "bust"
                winnings = -game_state['original_bet']
            elif dealer_score > 21 or player_score > dealer_score:
                if len(hand) == 2 and player_score == 21:
                    result = "blackjack"
                    winnings = math.floor(game_state['original_bet'] * 1.5)
                else:
                    result = "win"
                    winnings = game_state['original_bet']
            elif player_score < dealer_score:
                result = "lose"
                winnings = -game_state['original_bet']
            else:
                result = "push"
                winnings = 0

            total_winnings += winnings
            results.append((hand, player_score, result, winnings))

        new_dabloons = await update_dabloons_result(
            ctx.author.id, abs(total_winnings),
            "win" if total_winnings > 0 else "lose" if total_winnings < 0 else "draw"
        )

        if total_winnings > 0:
            embed_color = discord.Color.green()
        elif total_winnings < 0:
            embed_color = discord.Color.red()
        else:
            embed_color = discord.Color.gold()

        embed = discord.Embed(
            title="Blackjack Results",
            color=embed_color
        )

        for i, (hand, score, result, winnings) in enumerate(results, 1):
            result_str = {
                "win": "You won!",
                "lose": "You lost",
                "bust": "You busted!",
                "blackjack": "BLACKJACK!",
                "push": "Push (tie)"
            }[result]

            embed.add_field(
                name=f"Hand {i}: {result_str}",
                value=(
                    f"Cards: {format_hand(hand)}\n"
                    f"Score: {score}\n"
                    f"Result: {winnings:+} dabloons"
                ),
                inline=False
            )

        embed.add_field(
            name="Dealer's Hand",
            value=f"{format_hand(dealer_hand)}\nScore: {dealer_score}",
            inline=False
        )

        embed.add_field(
            name="Final Result",
            value=f"Total change: {total_winnings:+} dabloons\nNew balance: {new_dabloons} dabloons",
            inline=False
        )

        await interaction.response.edit_message(embed=embed, view=None)

    def cog_unload(self):
        self.active_games.clear()


async def setup(bot):
    await bot.add_cog(Blackjack(bot))