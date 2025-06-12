import discord
from discord.ext import commands, tasks
import os
import json
import asyncio
import sqlite3
from pathlib import Path
import importlib

# Load config.json
with open(os.path.join(os.path.dirname(__file__), 'config.json')) as f:
    config = json.load(f)

# Cog loading config
COG_WHITELIST = config.get('COG WHITELIST', [])
COG_BLACKLIST = config.get('COG BLACKLIST', [])
LOAD_ALL_COGS = config.get('LOAD_ALL_COGS', True)
BYPASS_FORCED_BOTMANAGEMENT_PY = config.get('BYPASS_FORCED_BOTMANAGEMENT.PY', False)
CUSTOM_COGS_WHITELIST = config.get('CUSTOM_COGS_WHITELIST', [])
CUSTOM_COGS_BLACKLIST = config.get('CUSTOM_COGS_BLACKLIST', [])
CUSTOM_COGS_AUTOMATICALLY_LOADED = config.get('CUSTOM_COGS_AUTOMATICALLY_LOADED', True)

async def load_cogs(bot):
    cogs_dir = Path(__file__).parent / 'cogs'
    for file in cogs_dir.glob('*.py'):
        if file.name.startswith('_'):
            continue
        if file.stem in COG_BLACKLIST:
            continue
        if file.stem == 'botmanagement' and not BYPASS_FORCED_BOTMANAGEMENT_PY:
            # Always load botmanagement.py unless bypass is enabled
            try:
                await bot.load_extension('cogs.botmanagement')
            except Exception as e:
                print(f'Failed to load cog cogs.botmanagement: {e}')
            continue
        cog_name = f"cogs.{file.stem}"
        # Only load cogs if LOAD_ALL_COGS is True or cog is in whitelist
        if LOAD_ALL_COGS or file.stem in COG_WHITELIST:
            try:
                await bot.load_extension(cog_name)
            except Exception as e:
                print(f'Failed to load cog {cog_name}: {e}')

    # Load custom cogs if enabled
    if CUSTOM_COGS_AUTOMATICALLY_LOADED:
        custom_cogs_dir = Path(__file__).parent / 'custom cogs'
        for file in custom_cogs_dir.glob('*.py'):
            if file.name.startswith('_'):
                continue
            if file.stem in CUSTOM_COGS_BLACKLIST:
                continue
            cog_name = f"custom cogs.{file.stem}"
            if file.stem in CUSTOM_COGS_WHITELIST or CUSTOM_COGS_AUTOMATICALLY_LOADED:
                try:
                    await bot.load_extension(cog_name)
                except Exception as e:
                    print(f'Failed to load custom cog {cog_name}: {e}')

intents = discord.Intents.default()
intents.message_content = True

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

# Get command prefix from config, default to '!'. If in a guild, use the server's prefix from the database if set.
def get_prefix(bot, message):
    prefix = config.get('BOT_PREFIX', '!').strip()
    # User prefix overrides guild prefix
    if message.guild:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'database.db')
        user_prefix = None
        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            # Check for user-specific prefix
            c.execute("SELECT personal_prefix FROM users WHERE user_id = ?", (message.author.id,))
            user_row = c.fetchone()
            if user_row and user_row[0]:
                user_prefix = user_row[0]
            # If no user prefix, check for server prefix
            if not user_prefix:
                c.execute("SELECT prefix FROM server_settings WHERE server_id = ?", (message.guild.id,))
                row = c.fetchone()
                if row and row[0]:
                    prefix = row[0]
            conn.close()
        except Exception:
            pass
        if user_prefix:
            prefix = user_prefix
    return commands.when_mentioned_or(prefix)(bot, message)

def get_presence():
    activity_type = config.get('BOT_ACTIVITY_TYPE', 'playing').lower()
    activity_name = config.get('BOT_ACTIVITY', 'with code')
    status_str = config.get('BOT_STATUS', 'online').lower()

    if activity_type == 'playing':
        activity = discord.Game(name=activity_name)
    elif activity_type == 'streaming':
        # Use a configurable streaming URL or mark this as a placeholder
        streaming_url = config.get('BOT_STREAMING_URL', 'https://example.com/stream')  # Placeholder URL
        activity = discord.Streaming(name=activity_name, url=streaming_url)
    elif activity_type == 'listening':
        activity = discord.Activity(type=discord.ActivityType.listening, name=activity_name)
    elif activity_type == 'watching':
        activity = discord.Activity(type=discord.ActivityType.watching, name=activity_name)
    elif activity_type == 'competing':
        activity = discord.Activity(type=discord.ActivityType.competing, name=activity_name)
    elif activity_type == 'custom':
        activity = discord.CustomActivity(name=activity_name)
    elif activity_type == 'none':
        activity = None
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
