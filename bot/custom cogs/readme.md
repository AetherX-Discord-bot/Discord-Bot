# Adding Custom Cogs to Your Discord Bot

> **Note:** This project is currently under an overhaul. Features, documentation, and structure may change frequently.

This folder is for your custom cogs! Cogs are Python files that add new commands or features to your Discord bot.

## How to Add a Custom Cog

1. **Create a Python file** in this folder (e.g., `mycog.py`).
2. **Define a class** that inherits from `commands.Cog` and add your commands as methods.
3. **Add a setup function** at the bottom of your file:
   ```python
   async def setup(bot):
       await bot.add_cog(MyCog(bot))
   ```
4. **(Optional) Add a docstring** at the top of your file or class to describe your cog.

## Example
```python
import discord
from discord.ext import commands

class MyCog(commands.Cog):
    """A simple custom cog example."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello(self, ctx):
        await ctx.send("Hello from a custom cog!")

async def setup(bot):
    await bot.add_cog(MyCog(bot))
```

## Loading Your Custom Cog

Make sure your bot loads cogs from this folder. You may need to add code in your main bot file to load all cogs in `custom cogs/`.

## Tips
- Name your cog files and classes clearly.
- Use async functions for commands.
- You can use all features of `discord.py` or your fork (e.g., py-cord, nextcord).

Happy coding!
