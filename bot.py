import os
import discord_vr # type:ignore
import discord
from discord.ext import commands
import datetime
import asyncio
import sqlite3
import time
from dotenv import load_dotenv
from datetime import datetime, timezone
from typing import Optional

load_dotenv()
TOKEN = os.getenv("TOKEN")
database = sqlite3.connect("AetherX.db")
cursor = database.cursor()

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set")


def print_boot_banner():
    banner = r"""
        _____          __  .__                ____  ___
       /  _  \   _____/  |_|  |__   __________\   \/  /
      /  /_\  \_/ __ \   __\  |  \_/ __ \_  __ \     / 
     /    |    \  ___/|  | |   Y  \  ___/|  | \/     \ 
     \____|__  /\___  >__| |___|  /\___  >__| /___/\  \
             \/     \/          \/     \/           \_/
    """
    print("\033[96m" + banner + "\033[0m")
    print("\033[92m[INFO]\033[0m Initializing AetherX...\n")
    print("\033[94m" + "=" * 50 + "\033[0m")


intents = discord.Intents.default()
intents.message_content = True
intents.members = True



class BootAnimator:
    def __init__(self):
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.current_frame = 0
        self.start_time = time.time()

    def get_spinner(self) -> str:
        frame = self.spinner_frames[self.current_frame]
        self.current_frame = (self.current_frame + 1) % len(self.spinner_frames)
        return frame

    def elapsed_time(self) -> str:
        return f"{time.time() - self.start_time:.2f}s"

    async def print_loading_step(self, text: str, status: Optional[str] = None, color: str = "cyan"):
        spinner = self.get_spinner()
        elapsed = self.elapsed_time()
        
        colors = {
            "cyan": "\033[96m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "red": "\033[91m",
            "reset": "\033[0m"
        }
        
        status_text = ""
        if status:
            status_color = "green" if status.lower() == "success" else "red" if status.lower() == "failed" else "yellow"
            status_text = f" [{colors[status_color]}{status.upper()}{colors['reset']}]"
        
        print(f"{colors[color]}{spinner} [{elapsed}] {text}{status_text}{colors['reset']}")
        await asyncio.sleep(0.1)


# ==================== CUSTOM BOT CLASS ====================
class AetherXBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.twitter_task = None
        # self.db = Database()  # Uncomment when you have a Database class

    async def setup_hook(self):
        """Load extensions from cogs/ and slash_cogs/"""
        animator = BootAnimator()

        # Initialize database (commented out)
        # await animator.print_loading_step("Initializing database...")
        # try:
        #     await self.db.connect()
        #     await animator.print_loading_step("Database connected", "SUCCESS")
        # except Exception as e:
        #     await animator.print_loading_step("Database failed", "FAILED", "red")
        #     raise

        EXT_FOLDERS = ("cogs",)
        for folder in EXT_FOLDERS:
            if os.path.exists(folder):
                await animator.print_loading_step(f"Scanning {folder} for extensions...")
                for filename in os.listdir(folder):
                    if filename.endswith(".py") and not filename.startswith("__"):
                        module_name = filename[:-3]
                        if module_name.isidentifier() and folder.isidentifier():
                            import_path = f"{folder}.{module_name}"
                            try:
                                await animator.print_loading_step(f"Loading {import_path}...")
                                await self.load_extension(import_path)
                                await animator.print_loading_step(f"Loaded {import_path}", "SUCCESS")
                            except Exception as e:
                                await animator.print_loading_step(f"Failed to load {import_path}", "FAILED", "red")
                                print(f"Error loading {import_path}: {e}")


# ==================== INSTANTIATE BOT ====================
bot = AetherXBot(command_prefix="$", intents=intents)


# ==================== BOT EVENTS ====================
@bot.event
async def on_ready():
    animator = BootAnimator()
    await bot.change_presence(activity=discord.Game(name="Version 0.2.5 Alpha out now | $help"))
    database = sqlite3.connect("AetherX.db")
    cursor = database.cursor()
    
    steps = [
        ("Syncing slash commands...", bot.tree.sync()),
        ("Setting status...", None),
        ("Preparing statistics...", None),
        ("Finalizing startup...", None),
    ]

    for text, task in steps:
        try:
            await animator.print_loading_step(text)
            if task is not None:
                await task
            await animator.print_loading_step(text, "SUCCESS")
        except Exception as e:
            await animator.print_loading_step(text, "FAILED", "red")
            print(f"Error during startup step '{text}': {e}")
            raise

    print(f'\n\033[92m[READY]\033[0m Logged in as {bot.user} (ID: {bot.user.id})')  # type: ignore
    print(f'\033[94m[INFO]\033[0m Boot completed in {animator.elapsed_time()}')
    print('\033[94m[INFO]\033[0m ' + '=' * 40)


# ==================== RUN BOT ====================
if __name__ == "__main__":
    print_boot_banner()
    bot.run(TOKEN)
