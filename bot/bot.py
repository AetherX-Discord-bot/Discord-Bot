# Basic Discord bot using discord.py
import discord
from discord.ext import commands, tasks
import os
import json
import asyncio

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

# Load config.json
with open(os.path.join(os.path.dirname(__file__), 'config.json')) as f:
    config = json.load(f)

# Show startup message if allowed
if config.get('CONSOLE_STARTUP_MESSAGE_WATERMARK_ALLOWED', True):
    print('---------------------------------------')
    print('AETHERX BOT BASEPLATE')
    print('---------------------------------------')

# Utility: Check if a user is a developer or owner (matches custom check)
def is_developer_or_owner_id(user_id):
    owner_ids = config.get('BOT_OWNERS', [])
    developer_ids = config.get('BOT_DEVELOPERS', [])
    all_ids = set(owner_ids + developer_ids)
    return user_id in all_ids

# Get command prefix from config, default to '!'
def get_prefix(bot, message):
    prefix = config.get('BOT_PREFIX', '!').strip()
    return commands.when_mentioned_or(prefix)(bot, message)

def get_presence():
    activity_type = config.get('BOT_ACTIVITY_TYPE', 'playing').lower()
    activity_name = config.get('BOT_ACTIVITY', 'with code')
    status_str = config.get('BOT_STATUS', 'online').lower()

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

async def start_bot(token):
    bot = commands.Bot(command_prefix=get_prefix, intents=intents)
    bot.config = config
    async def update_presence():
        while True:
            activity, status = get_presence()
            await bot.change_presence(activity=activity, status=status)
            await asyncio.sleep(30)
    async def on_ready():
        bot.loop.create_task(update_presence())
        print(f'Logged in as {bot.user}')
        await load_cogs(bot)
    bot.event(on_ready)
    await bot.start(token)

async def main():
    TOKENS = config.get('DISCORD_BOT_TOKEN')
    if isinstance(TOKENS, str):
        TOKENS = [TOKENS] if TOKENS else []
    if not TOKENS:
        raise ValueError("No Bot Token provided. Set the DISCORD_BOT_TOKEN in config.json.")
    await asyncio.gather(*(start_bot(token) for token in TOKENS))

if __name__ == "__main__":
    asyncio.run(main())
