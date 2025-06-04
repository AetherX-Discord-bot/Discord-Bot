import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

class Music(commands.Cog):
    """Music related commands."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, *, query: str = None):
        """Plays music from a YouTube URL or search term using yt-dlp and ffmpeg."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You must be in a voice channel to play music.")
            return
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
        vc = ctx.voice_client
        if not query:
            await ctx.send("Please provide a YouTube URL or search term.")
            return
        # Download audio using yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'outtmpl': 'song.%(ext)s',
            'cookiefile': '../cookies.txt',  # Use parent folder for cookies.txt
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        await ctx.send("Downloading audio...")
        loop = asyncio.get_event_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                return ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
        try:
            filename = await loop.run_in_executor(None, download)
        except Exception as e:
            await ctx.send(f"Error downloading audio: {e}")
            return
        # Play audio with ffmpeg
        if vc.is_playing():
            vc.stop()
        source = discord.FFmpegPCMAudio(filename)
        vc.play(source, after=lambda e: os.remove(filename) if os.path.exists(filename) else None)
        await ctx.send(f"Now playing: {query}")

    @commands.command(aliases=['p'])
    async def pause(self, ctx):
        """Pauses the currently playing song."""
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("Paused the music.")
        else:
            await ctx.send("Nothing is playing.")

    @commands.command(aliases=['res', 'r'])
    async def resume(self, ctx):
        """Resumes the paused song."""
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("Resumed the music.")
        else:
            await ctx.send("Nothing is paused.")

    @commands.command(aliases=['s'])
    async def stop(self, ctx):
        """Stops the music and clears the queue."""
        vc = ctx.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await ctx.send("Stopped the music.")
        else:
            await ctx.send("Nothing to stop.")

    @commands.command()
    async def skip(self, ctx):
        """Skips the currently playing song."""
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await ctx.send("Skipped the song.")
        else:
            await ctx.send("Nothing to skip.")

    @commands.command(aliases=['q'])
    async def queue(self, ctx):
        """Displays the current music queue."""
        await ctx.send("Queue is not implemented yet.")

    @commands.command(aliases=['j', 'connect'])
    async def join(self, ctx):
        """Joins the user's voice channel."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("You are not in a voice channel.")
            return
        channel = ctx.author.voice.channel
        # If already connected to a channel, move to the user's channel
        if ctx.voice_client:
            if ctx.voice_client.channel != channel:
                await ctx.voice_client.move_to(channel)
                await ctx.send(f"Moved to {channel}.")
            else:
                await ctx.send(f"Already in {channel}.")
        else:
            try:
                await channel.connect()
                await ctx.send(f"Joined {channel}.")
            except Exception as e:
                await ctx.send(f"Failed to join voice channel: {e}")

    @commands.command(aliases=['l', 'disconnect'])
    async def leave(self, ctx):
        """Leaves the voice channel."""
        vc = ctx.voice_client
        if vc:
            await vc.disconnect()
            await ctx.send("Left the voice channel.")
        else:
            await ctx.send("I'm not in a voice channel.")

async def setup(bot):
    await bot.add_cog(Music(bot))
