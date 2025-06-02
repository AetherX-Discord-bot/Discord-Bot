# Basic Discord bot using discord.py
import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv

async def load_cogs(bot):
    from pathlib import Path
    import importlib
    cogs_dir = Path(__file__).parent / 'cogs'
    for file in cogs_dir.glob('*.py'):
        if file.name.startswith('_'):
            continue
        cog_name = f"cogs.{file.stem}"
        try:
            await bot.load_extension(cog_name)
        except Exception as e:
            print(f'Failed to load cog {cog_name}: {e}')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

load_dotenv()

def get_presence():
    activity_type = os.getenv('BOT_ACTIVITY_TYPE', 'playing').lower()
    activity_name = os.getenv('BOT_ACTIVITY', 'with code')
    status_str = os.getenv('BOT_STATUS', 'online').lower()

    if activity_type == 'playing':
        activity = discord.Game(name=activity_name)
    elif activity_type == 'streaming':
        activity = discord.Streaming(name=activity_name, url='https://twitch.tv/yourchannel')
    elif activity_type == 'listening':
        activity = discord.Activity(type=discord.ActivityType.listening, name=activity_name)
    elif activity_type == 'watching':
        activity = discord.Activity(type=discord.ActivityType.watching, name=activity_name)
    elif activity_type == 'competing':
        activity = discord.Activity(type=discord.ActivityType.competing, name=activity_name)
    elif activity_type == 'custom':
        activity = discord.CustomActivity(name=activity_name)
    else:
        activity = discord.Game(name=activity_name)

    status = discord.Status.online
    if status_str == 'idle':
        status = discord.Status.idle
    elif status_str == 'dnd':
        status = discord.Status.dnd
    elif status_str == 'invisible':
        status = discord.Status.invisible
    return activity, status

@tasks.loop(seconds=30)
async def update_presence():
    activity, status = get_presence()
    await bot.change_presence(activity=activity, status=status)

@bot.event
async def on_ready():
    update_presence.start()
    print(f'Logged in as {bot.user}')
    await load_cogs(bot)

# use an environment variable
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
if TOKEN is None:
    raise ValueError("No Bot Token provided. Set the DISCORD_BOT_TOKEN environment variable.")

bot.run(TOKEN)
