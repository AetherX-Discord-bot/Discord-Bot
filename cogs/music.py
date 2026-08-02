import discord
from discord.ext import commands
import yt_dlp
import asyncio
import time
import os
import random
import shutil
from collections import defaultdict
from typing import Any, Dict

# Create downloads folder if it doesn't exist
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
    print(f"✅ Created downloads folder: {DOWNLOAD_FOLDER}")

# Function to clean up old files in downloads folder
def cleanup_downloads_folder(max_age_hours=24):
    """Remove files older than specified hours from downloads folder"""
    try:
        current_time = time.time()
        removed_count = 0
        
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                file_age = current_time - os.path.getmtime(filepath)
                if file_age > (max_age_hours * 3600):  # Convert hours to seconds
                    os.remove(filepath)
                    removed_count += 1
                    print(f"🧹 Cleaned up old file: {filename}")
        
        if removed_count > 0:
            print(f"✅ Cleaned up {removed_count} old files from downloads folder")
            
    except Exception as e:
        print(f"❌ Error cleaning downloads folder: {e}")

# Run initial cleanup
cleanup_downloads_folder()

# Rate limiting tracking
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.max_requests = 50  # Conservative limit per 10 minutes
        self.time_window = 600  # 10 minutes in seconds
        
    def can_make_request(self, identifier="global"):
        now = time.time()
        # Remove old requests outside the time window
        self.requests[identifier] = [req_time for req_time in self.requests[identifier] 
                                   if now - req_time < self.time_window]
        
        # Check if under limit
        return len(self.requests[identifier]) < self.max_requests
        
    def add_request(self, identifier="global"):
        now = time.time()
        self.requests[identifier].append(now)

rate_limiter = RateLimiter()

# Check for cookies file
def setup_cookies():
    """
    Check for cookies file and detect what platforms it contains cookies for.
    Supports cookies.txt (Netscape format) for YouTube, SoundCloud, and other platforms.
    """
    cookie_files = ['cookies.txt', 'cookies.json']
    for cookie_file in cookie_files:
        if os.path.exists(cookie_file):
            # Detect which platforms have cookies
            with open(cookie_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                platforms = []
                if 'youtube' in content or '.youtube.com' in content:
                    platforms.append('YouTube')
                if 'soundcloud' in content or '.soundcloud.com' in content:
                    platforms.append('SoundCloud')
                if platforms:
                    print(f"✅ Using cookies file: {cookie_file}")
                    print(f"   Found cookies for: {', '.join(platforms)}")
                    return cookie_file
                else:
                    print(f"⚠️ Cookies file found but no recognized platform cookies detected.")
                    return cookie_file
    print("⚠️ No cookies file found. YouTube may require authentication for premium/restricted content.")
    print("   To use cookies, create/update cookies.txt with your YouTube or SoundCloud session.")
    return None

cookie_file = setup_cookies()

# Configuration - ENABLE PLAYLISTS and convert to MP3
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(extractor)s-%(id)s-%(title)s.%(ext)s'),  # Updated to use downloads folder
    'restrictfilenames': True,
    'noplaylist': False,  # ENABLE playlists
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'extract_flat': 'in_playlist',  # Extract flat only for playlist entries to avoid URL expiration
    
    # Caching options
    'cachedir': './yt_dlp_cache',
    'cookiefile': cookie_file if cookie_file else None,
    
    # Audio conversion - convert to MP3 for smaller file size and faster loading
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    
    # Audio format settings
    'extractaudio': True,
    'audioformat': 'mp3',
    'keepvideo': False,  # Don't keep original video after conversion
    
    # Throttling
    'sleep_interval': 1,
    'max_sleep_interval': 2,
    'retries': 3,
    'fragment_retries': 3,
    'skip_unavailable_fragments': True,
}

ffmpeg_options: Dict[str, Any] = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl: yt_dlp.YoutubeDL = yt_dlp.YoutubeDL(ytdl_format_options)  # type: ignore

# Cache for recently played tracks
audio_cache = {}
CACHE_DURATION = 3600  # 1 hour cache

class MusicPlayer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.bot = ctx.bot
        self.queue = []
        self.current = None
        self.lock = asyncio.Lock()
        self.volume = 0.5
        self.skip_votes = set()
        self.admin_ids = {435125886996709377, 1286383453016686705}
        self._last_error_time = 0
        self._is_playing = False
        self._last_request_time = 0
        self._request_delay = 2
        self._playlist_tracks = []  # Store playlist tracks
        self._current_playlist = None  # Current playlist being processed
        self._downloaded_files = []  # Track downloaded files for cleanup
        self.start_time = None
        self.duration = 0
        self.paused = False
        self.pause_start = None

    async def safe_extract_info(self, url, platform, download=False):
        """Safely extract info with rate limiting and delays"""
        # Check rate limits
        if not rate_limiter.can_make_request(platform):
            wait_time = random.randint(30, 60)
            print(f"⚠️ Rate limit approached for {platform}. Waiting {wait_time}s")
            await asyncio.sleep(wait_time)
        
        # Check cache first
        cache_key = f"{platform}:{url}:{download}"
        if cache_key in audio_cache:
            cache_time, cached_data = audio_cache[cache_key]
            if time.time() - cache_time < CACHE_DURATION:
                print(f"✅ Using cached data for {url}")
                return cached_data
        
        # Enforce minimum delay between requests
        time_since_last = time.time() - self._last_request_time
        if time_since_last < self._request_delay:
            await asyncio.sleep(self._request_delay - time_since_last)
        
        # Add jitter to avoid synchronized requests
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        try:
            rate_limiter.add_request(platform)
            self._last_request_time = time.time()
            
            # Create a temporary ytdl instance with appropriate settings
            temp_options = ytdl_format_options.copy()
            
            # For playlist extraction, use extract_flat for discovery
            # For actual playback, get full info immediately (don't extract flat)
            if download:
                # When downloading/preparing for playback, don't use extract_flat
                temp_options['extract_flat'] = False
            # else keep the default 'in_playlist' setting
            
            temp_ytdl = yt_dlp.YoutubeDL(temp_options)  # type: ignore
            
            data = await self.bot.loop.run_in_executor(
                None,
                lambda: temp_ytdl.extract_info(url, download=download)
            )
            
            # If we downloaded a file, track it
            if download and data and '_filename' in data:
                downloaded_file = data.get('_filename')
                if downloaded_file and os.path.exists(downloaded_file):
                    # Move to downloads folder if not already there (for consistency)
                    if DOWNLOAD_FOLDER not in downloaded_file:
                        filename = os.path.basename(downloaded_file)
                        new_path = os.path.join(DOWNLOAD_FOLDER, filename)
                        if not os.path.exists(new_path):
                            shutil.move(downloaded_file, new_path)
                            downloaded_file = new_path
                    
                    self._downloaded_files.append(downloaded_file)
                    print(f"💾 Downloaded file saved to: {downloaded_file}")
            
            # Cache successful results
            if data:
                audio_cache[cache_key] = (time.time(), data)
                
            return data
            
        except Exception as e:
            print(f"❌ Extraction failed for {url}: {e}")
            return None

    def cleanup_downloaded_files(self):
        """Clean up downloaded files for this player"""
        for file_path in self._downloaded_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🧹 Cleaned up downloaded file: {file_path}")
            except Exception as e:
                print(f"❌ Error cleaning up file {file_path}: {e}")
        self._downloaded_files.clear()

    async def load_playlist_track(self, track_info):
        """Load a single track from a playlist with proper URL extraction"""
        try:
            platform = 'soundcloud' if 'soundcloud' in track_info.get('url', '').lower() else 'youtube'
            track_url = track_info.get('url') or track_info.get('webpage_url')
            
            if not track_url:
                print(f"❌ No URL found for track: {track_info.get('title', 'Unknown')}")
                return None
            
            # Extract full audio info for this specific track
            print(f"🔍 Extracting full track info for: {track_info.get('title', 'Unknown')}")
            full_data = await self.safe_extract_info(
                track_url, 
                platform, 
                download=True  # Download the audio file for reliable playback
            )
            
            if not full_data:
                print(f"❌ Failed to extract info for: {track_info.get('title', 'Unknown')}")
                return None
            
            # Get the audio URL or downloaded file path
            # If a file was downloaded, use the file path
            audio_url = None
            if '_filename' in full_data and os.path.exists(full_data['_filename']):
                # Use downloaded file
                audio_url = full_data['_filename']
                self._downloaded_files.append(audio_url)
                print(f"✅ Using downloaded file for playback: {audio_url}")
            else:
                # Fallback to URL (for streaming sources)
                audio_url = full_data.get('url')
                if not audio_url and 'entries' in full_data and len(full_data['entries']) > 0:
                    audio_url = full_data['entries'][0].get('url')
            
            if not audio_url:
                print(f"❌ Could not extract audio URL for: {track_info.get('title', 'Unknown')}")
                return None
            
            # Get title from full_data if not in track_info
            title = track_info.get('title') or full_data.get('title', 'Unknown Title')
            
            return {
                'title': title,
                'url': audio_url,  # Use downloaded file path or audio stream URL
                'webpage_url': track_url,  # Keep original URL for reference
                'requester': self.ctx.author,
                'platform': platform,
                'is_playlist_track': True,
                'extractor': full_data.get('extractor', platform),
                'duration': full_data.get('duration', 0)
            }
            
        except Exception as e:
            print(f"❌ Error loading playlist track: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def play_next(self, error=None):
        async with self.lock:
            self._is_playing = False
            now = time.time()
            
            if error:
                print(f"Playback error: {error}")
                if now - self._last_error_time < 5:
                    await asyncio.sleep(5)
                self._last_error_time = now

            self.skip_votes.clear()

            if not self.ctx.voice_client or not self.ctx.voice_client.is_connected():
                self.cleanup()
                return

            # Check if we need to load the next playlist track
            if self._playlist_tracks and not self.queue:
                embed = discord.Embed(title="🔄 Loading Next Track", color=discord.Color.blue())
                embed.description = "Processing next song from playlist..."
                await self.ctx.send(embed=embed)
                
                next_track_info = self._playlist_tracks.pop(0)
                loaded_track = await self.load_playlist_track(next_track_info)
                
                if loaded_track:
                    self.queue.append(loaded_track)
                    
                    # Update current playlist info
                    remaining_tracks = len(self._playlist_tracks)
                    if remaining_tracks > 0:
                        embed = discord.Embed(title="📋 Playlist Progress", color=discord.Color.blue())
                        embed.add_field(name="Tracks Remaining", value=str(remaining_tracks), inline=False)
                        await self.ctx.send(embed=embed)
                else:
                    embed = discord.Embed(title="❌ Failed to Load Track", color=discord.Color.red())
                    embed.description = f"Could not load: {next_track_info.get('title', 'Unknown')}"
                    await self.ctx.send(embed=embed)
                    
                    # Continue with next track if available
                    if self._playlist_tracks:
                        await self.play_next()

            if not self.queue:
                # Clear playlist if queue is empty
                if self._playlist_tracks:
                    self._playlist_tracks.clear()
                    self._current_playlist = None
                    
                await asyncio.sleep(60)
                if not self.queue and self.ctx.voice_client and self.ctx.voice_client.is_connected():
                    await self.ctx.voice_client.disconnect()
                    self.cleanup()
                return

            self.current = self.queue.pop(0)
            self._is_playing = True
            self.start_time = time.time()
            self.duration = self.current.get('duration', 0)
            self.paused = False
            self.pause_start = None
            
            for attempt in range(2):
                try:
                    source = discord.FFmpegPCMAudio(
                        self.current['url'],
                        **ffmpeg_options
                    )
                    
                    source = discord.PCMVolumeTransformer(source, volume=self.volume)
                    
                    self.ctx.voice_client.play(
                        source,
                        after=lambda e: asyncio.run_coroutine_threadsafe(
                            self.play_next(e),
                            self.bot.loop
                        )
                    )
                    
                    platform_icon = self.get_platform_icon(self.current.get('platform', ''))
                    playlist_indicator = " (playlist)" if self.current.get('is_playlist_track') else ""
                    
                    embed = discord.Embed(title=f"{platform_icon} Now Playing", color=discord.Color.green())
                    embed.add_field(name="Track", value=self.current['title'], inline=False)
                    embed.add_field(name="Requested by", value=self.current['requester'].mention, inline=False)
                    if playlist_indicator:
                        embed.add_field(name="Source", value="Playlist", inline=True)
                    embed.set_footer(text=f"Platform: {self.current.get('platform', 'Unknown').title()}")
                    
                    await self.ctx.send(embed=embed)
                    return
                    
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed: {e}")
                    if attempt == 1:
                        embed = discord.Embed(title="❌ Playback Failed", color=discord.Color.red())
                        embed.add_field(name="Track", value=self.current['title'], inline=False)
                        embed.add_field(name="Error", value=str(e)[:256], inline=False)
                        await self.ctx.send(embed=embed)
                        await self.play_next()
                    await asyncio.sleep(1)

    def get_platform_icon(self, extractor):
        icons = {
            'youtube': '📺',
            'soundcloud': '🎧',
            'bandcamp': '🎵',
            'twitch': '🔴',
            'vimeo': '🎬'
        }
        return icons.get(extractor.lower(), '🎶')

    def cleanup(self):
        # Clean up downloaded files
        self.cleanup_downloaded_files()
        
        # Clear playlist data
        self._playlist_tracks.clear()
        self._current_playlist = None
        
        if hasattr(self.ctx, 'cog') and hasattr(self.ctx.cog, 'players'):
            self.ctx.cog.players.pop(self.ctx.guild.id, None)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}
        self.last_cleanup_time = time.time()
        self.cleanup_interval = 3600  # Clean up every hour

    def get_player(self, ctx):
        if ctx.guild.id not in self.players:
            self.players[ctx.guild.id] = MusicPlayer(ctx)
            self.players[ctx.guild.id].bot = self.bot
        return self.players[ctx.guild.id]

    async def periodic_cleanup(self):
        """Periodically clean up old files"""
        current_time = time.time()
        if current_time - self.last_cleanup_time > self.cleanup_interval:
            cleanup_downloads_folder()
            self.last_cleanup_time = current_time

    async def ensure_connection(self, ctx):
        if not ctx.author.voice:
            await ctx.send("❌ You're not in a voice channel!")
            return False

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                await ctx.voice_client.move_to(ctx.author.voice.channel)
        else:
            try:
                await ctx.author.voice.channel.connect()
            except discord.ClientException as e:
                await ctx.send(f"❌ Connection failed: {e}")
                return False
        return True

    def is_valid_url(self, query):
        supported_domains = [
            'youtube.com', 'youtu.be',
            'soundcloud.com', 'snd.sc', 'on.soundcloud.com',
            'bandcamp.com',
            'twitch.tv',
            'vimeo.com'
        ]
        return any(domain in query.lower() for domain in supported_domains)

    async def safe_play_extraction(self, ctx, query, is_soundcloud=False):
        """Safe extraction with rate limiting"""
        platform = 'soundcloud' if is_soundcloud else 'youtube'
        
        if not rate_limiter.can_make_request(platform):
            await ctx.send("⚠️ Rate limit approached. Please wait a few minutes before making more requests.")
            return None

        player = self.get_player(ctx)
        
        # Determine URL - FIX: Always use search prefix for non-URL queries
        if self.is_valid_url(query):
            url = query
        else:
            url = f"scsearch:{query}" if is_soundcloud else f"ytsearch:{query}"

        data = await player.safe_extract_info(url, platform, download=False)
        
        return data

    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, query: str):
        """Play a song or playlist from YouTube, SoundCloud, or other supported platforms"""
        if not await self.ensure_connection(ctx):
            return

        player = self.get_player(ctx)
        
        # Run periodic cleanup
        await self.periodic_cleanup()
        
        async with ctx.typing():
            try:
                is_soundcloud = 'soundcloud.com' in query.lower()
                
                data = await self.safe_play_extraction(ctx, query, is_soundcloud)
                
                if not data:
                    if not self.is_valid_url(query):
                        alternative_data = await self.safe_play_extraction(ctx, query, not is_soundcloud)
                        if alternative_data:
                            data = alternative_data
                    
                    if not data:
                        embed = discord.Embed(title="❌ Not Found", color=discord.Color.red())
                        embed.description = "Couldn't find that audio or rate limit reached. Try again in a few minutes."
                        await ctx.send(embed=embed)
                        return

                # Handle playlists
                if 'entries' in data and len(data['entries']) > 1:
                    playlist_tracks = []
                    valid_entries = [entry for entry in data['entries'] if entry is not None]
                    
                    if not valid_entries:
                        embed = discord.Embed(title="❌ No Playable Tracks", color=discord.Color.red())
                        embed.description = "The playlist appears to be empty or unavailable."
                        await ctx.send(embed=embed)
                        return

                    # Store playlist info
                    playlist_title = data.get('title', 'Unknown Playlist')
                    total_tracks = len(valid_entries)
                    
                    # Only load the first track immediately, queue the rest as track info
                    first_track_info = valid_entries[0]
                    loaded_first_track = await player.load_playlist_track(first_track_info)
                    
                    if loaded_first_track:
                        player.queue.append(loaded_first_track)
                    
                    # Store remaining tracks as info only (will be loaded one by one)
                    player._playlist_tracks = valid_entries[1:]
                    player._current_playlist = playlist_title
                    
                    platform_icon = player.get_platform_icon(data.get('extractor', ''))
                    
                    embed = discord.Embed(title=f"{platform_icon} Playlist Added", color=discord.Color.blue())
                    embed.add_field(name="Playlist Title", value=playlist_title, inline=False)
                    embed.add_field(name="Total Tracks", value=str(total_tracks), inline=True)
                    embed.add_field(name="Remaining Tracks", value=str(len(valid_entries) - 1), inline=True)
                    embed.add_field(name="First Track", value=first_track_info.get('title', 'Unknown'), inline=False)
                    embed.set_footer(text="Tracks will load one by one during playback")
                    
                    await ctx.send(embed=embed)
                    
                else:
                    # Single track - FIX: Handle search results properly
                    track_data = data
                    if 'entries' in data:
                        # This is a search result with entries
                        entries = data['entries']
                        if entries and len(entries) > 0:
                            track_data = entries[0]
                        else:
                            await ctx.send("❌ No results found for your search!")
                            return

                    # Validate we have the required data
                    if not track_data or not isinstance(track_data, dict):
                        await ctx.send("❌ Invalid data received from search.")
                        return

                    # Get the track title safely
                    track_title = track_data.get('title', 'Unknown Title')
                    track_url = track_data.get('url', '')
                    
                    if not track_url:
                        await ctx.send("❌ Could not get audio URL for this track.")
                        return

                    # For single tracks, load full audio immediately
                    full_data = await player.safe_extract_info(
                        track_url, 
                        'soundcloud' if is_soundcloud else 'youtube', 
                        download=True
                    )
                    
                    if full_data and 'url' in full_data:
                        final_url = full_data['url']
                    else:
                        final_url = track_url

                    player.queue.append({
                        'title': track_title,
                        'url': final_url,
                        'requester': ctx.author,
                        'platform': track_data.get('extractor', ''),
                        'duration': full_data.get('duration', 0) if full_data else 0
                    })

                    platform_icon = player.get_platform_icon(track_data.get('extractor', ''))
                    embed = discord.Embed(title=f"{platform_icon} Added to Queue", color=discord.Color.green())
                    embed.add_field(name="Track", value=track_title, inline=False)
                    embed.add_field(name="Requested by", value=ctx.author.mention, inline=False)
                    await ctx.send(embed=embed)

                # Start playing if not already
                if not ctx.voice_client.is_playing() and not player._is_playing:
                    await player.play_next()
                
            except Exception as e:
                await ctx.send(f"❌ Error: {str(e)}")

    @commands.command(name='soundcloud', aliases=['sc'])
    async def soundcloud(self, ctx, *, query: str):
        """Search and play specifically from SoundCloud"""
        if not await self.ensure_connection(ctx):
            return

        player = self.get_player(ctx)
        
        # Run periodic cleanup
        await self.periodic_cleanup()
        
        async with ctx.typing():
            try:
                if not rate_limiter.can_make_request('soundcloud'):
                    await ctx.send("❌ SoundCloud rate limit reached. Please wait before making more requests.")
                    return

                is_url = self.is_valid_url(query) and 'soundcloud.com' in query.lower()
                url = query if is_url else f"scsearch:{query}"

                data = await self.safe_play_extraction(ctx, url, True)
                
                if not data:
                    await ctx.send("❌ Couldn't find that SoundCloud track or rate limit reached.")
                    return

                # Handle SoundCloud playlists
                if 'entries' in data and len(data['entries']) > 1:
                    playlist_tracks = []
                    valid_entries = [entry for entry in data['entries'] if entry is not None]
                    
                    if not valid_entries:
                        await ctx.send("❌ No playable tracks found in SoundCloud playlist!")
                        return

                    playlist_title = data.get('title', 'Unknown SoundCloud Playlist')
                    total_tracks = len(valid_entries)
                    
                    first_track_info = valid_entries[0]
                    loaded_first_track = await player.load_playlist_track(first_track_info)
                    
                    if loaded_first_track:
                        player.queue.append(loaded_first_track)
                    
                    player._playlist_tracks = valid_entries[1:]
                    player._current_playlist = playlist_title
                    
                    message = f"🎧 **SoundCloud Playlist Added:** {playlist_title}\n"
                    message += f"📋 **Tracks:** {total_tracks} total\n"
                    message += f"🎵 **First track:** {first_track_info.get('title', 'Unknown')}\n"
                    message += f"🔄 **Loading:** Remaining tracks will load one by one during playback"
                    
                    await ctx.send(message)
                    
                else:
                    # Single SoundCloud track - FIX: Handle search results properly
                    track_data = data
                    if 'entries' in data:
                        entries = data['entries']
                        if entries and len(entries) > 0:
                            track_data = entries[0]
                        else:
                            await ctx.send("❌ No SoundCloud results found!")
                            return

                    # Validate data
                    if not track_data or not isinstance(track_data, dict):
                        await ctx.send("❌ Invalid data received from SoundCloud search.")
                        return

                    track_title = track_data.get('title', 'Unknown Title')
                    track_url = track_data.get('url', '')
                    
                    if not track_url:
                        await ctx.send("❌ Could not get audio URL for this SoundCloud track.")
                        return

                    full_data = await player.safe_extract_info(
                        track_url, 
                        'soundcloud', 
                        download=True
                    )
                    
                    if full_data and 'url' in full_data:
                        final_url = full_data['url']
                    else:
                        final_url = track_url

                    player.queue.append({
                        'title': track_title,
                        'url': final_url,
                        'requester': ctx.author,
                        'platform': 'soundcloud',
                        'duration': full_data.get('duration', 0) if full_data else 0
                    })

                    remaining = rate_limiter.max_requests - len(rate_limiter.requests['soundcloud'])
                    message = f"🎧 Added to queue: **{track_title}** (from SoundCloud)"
                    if remaining < 10:
                        message += f"\n⚠️ Only {remaining} SoundCloud requests left this hour"
                        
                    await ctx.send(message)

                if not ctx.voice_client.is_playing() and not player._is_playing:
                    await player.play_next()
                
            except Exception as e:
                await ctx.send(f"❌ SoundCloud error: {str(e)}")

    @commands.command(name='skip', aliases=['s'])
    async def skip(self, ctx):
        """Vote to skip the current song"""
        player = self.get_player(ctx)
        
        if not ctx.voice_client or (not ctx.voice_client.is_playing() and not player._is_playing):
            embed = discord.Embed(title="❌ Nothing Playing", color=discord.Color.red())
            embed.description = "No song is currently playing."
            await ctx.send(embed=embed)
            return

        # Admin override
        if ctx.author.id in player.admin_ids:
            embed = discord.Embed(title="⏭️ Admin Skip", color=discord.Color.green())
            embed.description = f"Admin {ctx.author.mention} forced skip!"
            await ctx.send(embed=embed)
            ctx.voice_client.stop()
            return

        # Vote system
        voters = [m for m in ctx.voice_client.channel.members if not m.bot]
        required_votes = (len(voters) // 2 + 1)
        
        if ctx.author.id in player.skip_votes:
            embed = discord.Embed(title="❌ Already Voted", color=discord.Color.red())
            embed.description = "You already voted to skip this song."
            await ctx.send(embed=embed)
            return

        player.skip_votes.add(ctx.author.id)
        current_votes = len(player.skip_votes)
        
        if current_votes >= required_votes:
            embed = discord.Embed(title="⏭️ Skip Vote Passed", color=discord.Color.green())
            embed.description = f"Vote passed! ({current_votes}/{required_votes})\nSkipping to next song..."
            await ctx.send(embed=embed)
            ctx.voice_client.stop()
        else:
            embed = discord.Embed(title="🗳️ Skip Vote", color=discord.Color.blue())
            embed.description = f"Vote recorded: {current_votes}/{required_votes} needed"
            await ctx.send(embed=embed)

    @commands.command(name='queue', aliases=['q'])
    async def queue(self, ctx):
        """Show the current queue"""
        player = self.get_player(ctx)
        
        if not player.queue and not player._playlist_tracks and not player.current:
            embed = discord.Embed(title="📭 Queue Empty", color=discord.Color.red())
            embed.description = "No songs in queue or currently playing."
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title="🎧 Queue", color=discord.Color.blue())
        
        # Show currently playing
        if player.current:
            platform_icon = player.get_platform_icon(player.current.get('platform', ''))
            embed.add_field(
                name=f"{platform_icon} Now Playing",
                value=f"**{player.current['title']}**\nRequested by: {player.current['requester'].mention}",
                inline=False
            )
        
        # Show upcoming in queue
        if player.queue:
            queue_list = "\n".join(
                f"{i+1}. {track['title']}"
                for i, track in enumerate(player.queue[:5])
            )
            embed.add_field(
                name=f"Up Next ({len(player.queue)} total)",
                value=queue_list if queue_list else "No tracks",
                inline=False
            )
        
        # Show playlist info if active
        if player._playlist_tracks:
            embed.add_field(
                name=f"📋 {player._current_playlist}",
                value=f"{len(player._playlist_tracks)} tracks remaining in playlist",
                inline=False
            )
        
        embed.set_footer(text=f"Total in queue: {len(player.queue)}")
        await ctx.send(embed=embed)

    @commands.command(name='nowplaying', aliases=['np'])
    async def nowplaying(self, ctx):
        """Show the currently playing song"""
        player = self.get_player(ctx)
        
        if not player.current:
            embed = discord.Embed(title="❌ Nothing Playing", color=discord.Color.red())
            embed.description = "No song is currently playing."
            await ctx.send(embed=embed)
            return

        platform_icon = player.get_platform_icon(player.current.get('platform', ''))
        embed = discord.Embed(title=f"{platform_icon} Now Playing", color=discord.Color.green())
        embed.add_field(name="Track", value=player.current['title'], inline=False)
        embed.add_field(name="Requested by", value=player.current['requester'].mention, inline=True)
        embed.add_field(name="Platform", value=player.current.get('platform', 'Unknown').title(), inline=True)
        if player.current.get('is_playlist_track'):
            embed.add_field(name="Source", value="Playlist", inline=True)
        
        # Add progress if available
        if player.start_time:
            if player.paused and player.pause_start:
                elapsed = int(player.pause_start - player.start_time)
            else:
                elapsed = int(time.time() - player.start_time)
            
            duration = player.duration
            if duration > 0:
                progress = f"{elapsed//60}:{elapsed%60:02d} / {duration//60}:{duration%60:02d}"
            else:
                progress = f"{elapsed//60}:{elapsed%60:02d}"
            
            embed.add_field(name="Progress", value=progress, inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='pause')
    async def pause(self, ctx):
        """Pause the player"""
        player = self.get_player(ctx)
        
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            player.paused = True
            player.pause_start = time.time()
            embed = discord.Embed(title="⏸️ Paused", color=discord.Color.blue())
            embed.description = "Playback paused. Use `resume` to continue."
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="❌ Nothing Playing", color=discord.Color.red())
            embed.description = "No song is currently playing."
            await ctx.send(embed=embed)

    @commands.command(name='resume')
    async def resume(self, ctx):
        """Resume the player"""
        player = self.get_player(ctx)
        
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            player.paused = False
            if player.pause_start and player.start_time:
                player.start_time += time.time() - player.pause_start
            player.pause_start = None
            embed = discord.Embed(title="▶️ Resumed", color=discord.Color.green())
            embed.description = "Playback resumed."
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="❌ Not Paused", color=discord.Color.red())
            embed.description = "Player isn't paused or nothing is playing."
            await ctx.send(embed=embed)

    @commands.command(name='stop')
    async def stop(self, ctx):
        """Stop the player and clear queue"""
        player = self.get_player(ctx)
        
        if ctx.voice_client:
            player.queue.clear()
            player._playlist_tracks.clear()
            player._current_playlist = None
            ctx.voice_client.stop()
            await ctx.voice_client.disconnect()
            player.cleanup()
            embed = discord.Embed(title="⏹️ Stopped", color=discord.Color.red())
            embed.description = "Playback stopped and queue cleared."
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="❌ Not Connected", color=discord.Color.red())
            embed.description = "Bot is not in a voice channel."
            await ctx.send(embed=embed)

    @commands.command(name='volume', aliases=['vol'])
    async def volume(self, ctx, volume: int):
        """Set volume (0-100)"""
        player = self.get_player(ctx)
        
        if not 0 <= volume <= 100:
            embed = discord.Embed(title="❌ Invalid Volume", color=discord.Color.red())
            embed.description = "Volume must be between 0-100."
            await ctx.send(embed=embed)
            return

        player.volume = volume / 100
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = player.volume
        
        embed = discord.Embed(title="🔊 Volume Changed", color=discord.Color.blue())
        embed.description = f"Volume set to **{volume}%**"
        await ctx.send(embed=embed)

    @commands.command(name='leave', aliases=['disconnect', 'dc'])
    async def leave(self, ctx):
        """Make the bot leave the voice channel"""
        player = self.get_player(ctx)
        
        if ctx.voice_client:
            # Clear queue and stop playback
            player.queue.clear()
            player._playlist_tracks.clear()
            player._current_playlist = None
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                ctx.voice_client.stop()
            
            await ctx.voice_client.disconnect()
            player.cleanup()
            embed = discord.Embed(title="👋 Left Voice Channel", color=discord.Color.blue())
            embed.description = "Bot has disconnected from voice channel."
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title="❌ Not Connected", color=discord.Color.red())
            embed.description = "Bot is not in a voice channel."
            await ctx.send(embed=embed)

    @commands.command(name='platforms')
    async def platforms(self, ctx):
        """Show supported platforms"""
        platforms = """
**Supported Platforms:**
📺 YouTube (full support with cookies)
🎧 SoundCloud (search & direct URLs)
🎵 Bandcamp
🔴 Twitch
🎬 Vimeo

**Cookie Support:**
- Add YouTube cookies for age-restricted and premium content
- Add SoundCloud cookies for premium track playback
- Use `$fixsoundcloud` command for setup instructions

**Examples:**
-# This depends on the bots prefix for your server (default is !)
`play never gonna give you up` - Search YouTube
`play https://soundcloud.com/...` - Play SoundCloud URL
`soundcloud chill lofi` - Search SoundCloud specifically
`play https://www.youtube.com/playlist?list=...` - Play YouTube playlist
        """
        await ctx.send(platforms)

    @commands.command(name='cookies')
    async def check_cookies(self, ctx):
        """Check if cookies are working"""
        if cookie_file:
            cookie_info = "❌ Could not detect cookies"
            try:
                with open(cookie_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    if 'youtube' in content or '.youtube.com' in content:
                        cookie_info = "✅ YouTube cookies detected"
                    elif 'soundcloud' in content or '.soundcloud.com' in content:
                        cookie_info = "✅ SoundCloud cookies detected"
            except:
                pass
            await ctx.send(f"✅ Cookies file detected: `{cookie_file}`\n{cookie_info}\nYouTube and SoundCloud playback should work properly!")
        else:
            await ctx.send("⚠️ No cookies file found. Bot will still work but YouTube premium/restricted content may fail.\nFor best results, add YouTube cookies to `cookies.txt`")

    @commands.command(name='fixsoundcloud')
    async def fix_soundcloud(self, ctx):
        """Instructions for fixing SoundCloud and YouTube playback"""
        message = """
**Fixing SoundCloud & YouTube Playback:**

1. **Create a cookies file:**
   - Install a browser extension like "Get cookies.txt" for Chrome/Firefox
   - Go to youtube.com (and/or soundcloud.com) and log in
   - Export cookies to `cookies.txt` in your bot's folder

2. **YouTube Cookies (Recommended):**
   - Log into your YouTube account
   - Export cookies to `cookies.txt`
   - This allows playing age-restricted and premium content

3. **SoundCloud Cookies (Optional):**
   - Log into your SoundCloud account
   - Export cookies and append to `cookies.txt` (or replace YouTube cookies)

4. **Current status:** """ + ("✅ Cookies file found" if cookie_file else "❌ No cookies file found")

        await ctx.send(message)

    @commands.command(name='debug')
    async def debug(self, ctx, *, query: str):
        """Debug command to check what yt-dlp sees"""
        try:
            player = self.get_player(ctx)
            data = await player.safe_extract_info(query, 'debug', download=False)
            if data:
                info = f"""
**Extractor:** {data.get('extractor', 'Unknown')}
**Title:** {data.get('title', 'Unknown')}
**URL:** {data.get('url', 'No URL')}
**Webpage URL:** {data.get('webpage_url', 'No webpage URL')}
**Duration:** {data.get('duration', 'Unknown')}
**Has entries:** {'entries' in data}
**Entries count:** {len(data['entries']) if 'entries' in data else 0}
                """
                await ctx.send(f"🔧 Debug info:\n{info}")
            else:
                await ctx.send("❌ No data extracted")
        except Exception as e:
            await ctx.send(f"❌ Debug error: {e}")

    @commands.command(name='ratelimit')
    async def ratelimit_status(self, ctx):
        """Check current rate limit status"""
        soundcloud_requests = len(rate_limiter.requests['soundcloud'])
        youtube_requests = len(rate_limiter.requests['youtube'])
        
        soundcloud_remaining = rate_limiter.max_requests - soundcloud_requests
        youtube_remaining = rate_limiter.max_requests - youtube_requests
        
        # Calculate reset time
        all_requests = rate_limiter.requests['soundcloud'] + rate_limiter.requests['youtube']
        if all_requests:
            oldest_request = min(all_requests)
            reset_in = int((rate_limiter.time_window - (time.time() - oldest_request)) / 60)
        else:
            reset_in = 0
        
        status = f"""
**Rate Limit Status:**
🎧 SoundCloud: {soundcloud_requests}/{rate_limiter.max_requests} requests used ({soundcloud_remaining} remaining)
📺 YouTube: {youtube_requests}/{rate_limiter.max_requests} requests used ({youtube_remaining} remaining)
⏰ Resets in: {reset_in} minutes

**Tips:**
- Use YouTube when possible (no rate limits)
- Queue multiple songs at once
- Use direct URLs instead of searches
        """
        await ctx.send(status)

    @commands.command(name='clearcache')
    async def clear_cache(self, ctx):
        """Clear the audio cache"""
        audio_cache.clear()
        await ctx.send("✅ Audio cache cleared!")

    @commands.command(name='playlistinfo', aliases=['plinfo'])
    async def playlist_info(self, ctx):
        """Show current playlist information"""
        player = self.get_player(ctx)
        
        if not player._current_playlist and not player._playlist_tracks:
            await ctx.send("❌ No active playlist!")
            return
            
        info = f"""
**Current Playlist:** {player._current_playlist or 'Unknown'}
**Tracks Remaining:** {len(player._playlist_tracks)}
**In Queue:** {len(player.queue)}
**Status:** {'Loading next track...' if player._playlist_tracks else 'Playlist complete'}
        """
        await ctx.send(info)

    @commands.command(name='cancelplaylist', aliases=['cancelpl'])
    async def cancel_playlist(self, ctx):
        """Cancel the current playlist"""
        player = self.get_player(ctx)
        
        if not player._current_playlist:
            await ctx.send("❌ No active playlist to cancel!")
            return
            
        cancelled_tracks = len(player._playlist_tracks)
        player._playlist_tracks.clear()
        player._current_playlist = None
        
        await ctx.send(f"✅ Playlist cancelled! {cancelled_tracks} tracks removed from queue.")

    @commands.command(name='cleanupdownloads', aliases=['cleanup'])
    async def cleanup_downloads_command(self, ctx):
        """Manually clean up the downloads folder"""
        try:
            initial_count = len([name for name in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, name))])
            cleanup_downloads_folder()
            final_count = len([name for name in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, name))])
            removed = initial_count - final_count
            
            await ctx.send(f"🧹 Cleaned up {removed} old files from downloads folder!\n📁 Current files: {final_count}")
        except Exception as e:
            await ctx.send(f"❌ Error cleaning downloads folder: {e}")

    @commands.command(name='downloadsfolder', aliases=['downloads'])
    async def downloads_folder_info(self, ctx):
        """Show information about the downloads folder"""
        try:
            if not os.path.exists(DOWNLOAD_FOLDER):
                await ctx.send(f"❌ Downloads folder '{DOWNLOAD_FOLDER}' doesn't exist!")
                return
            
            files = [f for f in os.listdir(DOWNLOAD_FOLDER) if os.path.isfile(os.path.join(DOWNLOAD_FOLDER, f))]
            file_count = len(files)
            total_size = sum(os.path.getsize(os.path.join(DOWNLOAD_FOLDER, f)) for f in files)
            
            # Get oldest and newest files
            if files:
                file_times = [(f, os.path.getmtime(os.path.join(DOWNLOAD_FOLDER, f))) for f in files]
                oldest = min(file_times, key=lambda x: x[1])
                newest = max(file_times, key=lambda x: x[1])
                
                oldest_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(oldest[1]))
                newest_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(newest[1]))
            else:
                oldest = ("None", 0)
                newest = ("None", 0)
                oldest_time = "N/A"
                newest_time = "N/A"
            
            info = f"""
**Downloads Folder Information:**
📁 **Folder:** `{DOWNLOAD_FOLDER}`
📊 **Files:** {file_count} files
💾 **Total Size:** {total_size / (1024*1024):.2f} MB
📅 **Oldest File:** `{oldest[0]}` ({oldest_time})
📅 **Newest File:** `{newest[0]}` ({newest_time})

**Note:** Files are automatically cleaned up after 24 hours.
Use `$cleanupdownloads` to manually clean up now.
            """
            
            await ctx.send(info)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting downloads folder info: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Auto-disconnect if bot is alone
        if member == self.bot.user and not after.channel:
            guild_id = before.channel.guild.id
            if guild_id in self.players:
                # Clean up downloaded files for this player
                self.players[guild_id].cleanup_downloaded_files()
                
                # Clear playlist data
                self.players[guild_id]._playlist_tracks.clear()
                self.players[guild_id]._current_playlist = None
                del self.players[guild_id]

async def setup(bot):
    await bot.add_cog(Music(bot))