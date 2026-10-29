import discord
from discord.ext import commands
import sqlite3
import json


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = "AetherX.db"
        self.authorized_users = [1286383453016686705, 435125886996709377]
        self.setup_db()

    def setup_db(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop (
            item_id INTEGER PRIMARY KEY,
            item_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            max_quantity INTEGER NOT NULL,
            can_buy BOOLEAN DEFAULT 0
        )
        ''')

        conn.commit()
        conn.close()

    def get_balance(self, user_id):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("SELECT dabloons FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0

    def update_balance(self, user_id, amount):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (user_id,))
        cursor.execute("UPDATE users SET dabloons = dabloons + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

    def get_all_items(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shop")
        items = cursor.fetchall()
        conn.close()
        return items

    def get_inventory(self, user_id):
        conn = sqlite3.connect(self.db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT inventory FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row is None:
                cursor.execute("INSERT INTO users (user_id, inventory) VALUES (?, ?)", (user_id, '{}'))
                conn.commit()
                return {}
            raw = row[0] if row[0] else '{}'
            return json.loads(raw)
        finally:
            conn.close()

    def update_inventory(self, user_id, item_id, quantity):
        inventory = self.get_inventory(user_id)
        inventory[str(item_id)] = inventory.get(str(item_id), 0) + quantity

        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET inventory = ? WHERE user_id = ?", (json.dumps(inventory), user_id))
        conn.commit()
        conn.close()

    def get_shop_items(self):
        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shop WHERE can_buy = 1")
        items = cursor.fetchall()
        conn.close()
        return items

    @commands.command(name="shop")
    async def shop(self, ctx):
        items = self.get_shop_items()
        if not items:
            await ctx.send("The shop is currently empty.")
            return

        inventory = self.get_inventory(ctx.author.id)

        embed = discord.Embed(
            title="🛍️ Welcome to the Shop!",
            description="Here are the available items:",
            color=discord.Color.gold()
        )

        for item in items:
            item_id, item_name, price, max_quantity, can_buy = item
            owned = inventory.get(str(item_id), 0)

            name_display = f"ID: {item_id} - {item_name}"
            if owned > 0:
                name_display += f" (owned: {owned})"

            if max_quantity != 0:
                embed.add_field(
                    name=name_display,
                    value=f"Price: {price} dabloons\nMax: {max_quantity}",
                    inline=False
                )
            else:
                embed.add_field(
                    name=name_display,
                    value=f"Price: {price} dabloons",
                    inline=False
                )

        embed.set_footer(text="Use the buy command to purchase items!")
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy(self, ctx, item_id: int, quantity: int = 1):
        if quantity <= 0:
            embed = discord.Embed(
                title="⚠️ Error",
                description="Quantity must be at least 1.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        items = self.get_shop_items()
        item = next((i for i in items if i[0] == item_id), None)

        if item is None:
            embed = discord.Embed(
                title="⚠️ Error",
                description="Item not found or not available for purchase.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        price = item[2]
        max_quantity = item[3]
        user_balance = self.get_balance(ctx.author.id)
        total_cost = price * quantity

        if user_balance < total_cost:
            embed = discord.Embed(
                title="⚠️ Insufficient Funds",
                description=f"You don't have enough dabloons to buy {item[1]} (total cost: {total_cost} dabloons).",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        inventory = self.get_inventory(ctx.author.id)
        current_quantity = inventory.get(str(item_id), 0)
        if current_quantity + quantity > max_quantity and max_quantity != 0:
            embed = discord.Embed(
                title="⚠️ Purchase Limit Reached",
                description=f"You can't buy more than {max_quantity} of {item[1]} (you already have {current_quantity}).",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        conn = sqlite3.connect(self.db)
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO users (user_id, dabloons) VALUES (?, 0)", (ctx.author.id,))
            cursor.execute(
                "UPDATE users SET dabloons = dabloons - ? WHERE user_id = ?",
                (total_cost, ctx.author.id)
            )
            cursor.execute("SELECT inventory FROM users WHERE user_id = ?", (ctx.author.id,))
            row = cursor.fetchone()
            inv = json.loads(row[0]) if row and row[0] else {}
            inv[str(item_id)] = inv.get(str(item_id), 0) + quantity
            cursor.execute(
                "UPDATE users SET inventory = ? WHERE user_id = ?",
                (json.dumps(inv), ctx.author.id)
            )
            conn.commit()
        finally:
            conn.close()

        embed = discord.Embed(
            title="✅ Purchase Successful",
            description=f"You've bought {quantity} {item[1]}(s) for {total_cost} dabloons!",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"{self.get_balance(ctx.author.id)} dabloons", inline=True)
        embed.add_field(name="Now Owned", value=f"{current_quantity + quantity}", inline=True)

        await ctx.send(embed=embed)

    @commands.command(name="additem", hidden=True)
    async def additem(self, ctx, item_id: int, item_name: str, price: int, max_quantity: int, can_buy: bool = True):
        if ctx.author.id not in self.authorized_users:
            await ctx.send("❌ You don't have permission to use this command.")
            return

        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT item_id FROM shop WHERE item_id = ?", (item_id,))
            if cursor.fetchone() is not None:
                await ctx.send(f"❌ Item ID {item_id} is already in use. Please choose a different ID.")
                return

            cursor.execute(
                "INSERT INTO shop (item_id, item_name, price, max_quantity, can_buy) VALUES (?, ?, ?, ?, ?)",
                (item_id, item_name, price, max_quantity, int(can_buy))
            )
            conn.commit()

            embed = discord.Embed(
                title="✅ Item Added to Shop",
                color=discord.Color.green()
            )
            embed.add_field(name="ID", value=item_id, inline=True)
            embed.add_field(name="Name", value=item_name, inline=True)
            embed.add_field(name="Price", value=f"{price} dabloons", inline=True)
            embed.add_field(name="Max Quantity", value=max_quantity, inline=True)
            embed.add_field(name="Can Buy", value="Yes" if can_buy else "No", inline=True)

            await ctx.send(embed=embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error Adding Item",
                description=str(e),
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
        finally:
            conn.close()

    @commands.command(name="togglebuy", hidden=True)
    async def togglebuy(self, ctx, item_id: int):
        if ctx.author.id not in self.authorized_users:
            await ctx.send("❌ You don't have permission to use this command.")
            return

        conn = sqlite3.connect(self.db)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT item_name, can_buy FROM shop WHERE item_id = ?", (item_id,))
            item = cursor.fetchone()

            if not item:
                await ctx.send(f"❌ Item with ID {item_id} not found.")
                return

            item_name, current_status = item
            new_status = not current_status

            cursor.execute(
                "UPDATE shop SET can_buy = ? WHERE item_id = ?",
                (int(new_status), item_id)
            )
            conn.commit()

            embed = discord.Embed(
                title="✅ Purchase Status Updated",
                color=discord.Color.green()
            )
            embed.add_field(name="Item ID", value=item_id, inline=True)
            embed.add_field(name="Item Name", value=item_name, inline=True)
            embed.add_field(name="Status", value="Can now be purchased" if new_status else "No longer purchasable", inline=False)

            await ctx.send(embed=embed)
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Error Updating Item",
                description=str(e),
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
        finally:
            conn.close()


async def setup(bot):
    await bot.add_cog(Shop(bot))