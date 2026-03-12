# music.py — T.O.R.I.E.'s Music System

import discord
import yt_dlp
import spotipy
import asyncio
import os
from spotipy.oauth2 import SpotifyClientCredentials
from discord.ext import commands


YTDL_OPTIONS = {
    "format":         "bestaudio/best",
    "quiet":          True,
    "no_warnings":    True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

YTDL_OPTIONS_PLAYLIST = {
    "format":          "bestaudio/best",
    "quiet":           True,
    "no_warnings":     True,
    "extract_flat":    "in_playlist",
    "source_address":  "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options":        "-vn",
}

ytdl          = yt_dlp.YoutubeDL(YTDL_OPTIONS)
ytdl_playlist = yt_dlp.YoutubeDL(YTDL_OPTIONS_PLAYLIST)


def is_playlist(query: str) -> bool:
    return ("playlist?list=" in query or "&list=" in query) and "youtube.com" in query


async def fetch_playlist(url: str, loop: asyncio.AbstractEventLoop) -> list[dict]:
    """Fetch all entries from a YouTube playlist. Returns list of track dicts."""
    try:
        data = await loop.run_in_executor(
            None,
            lambda: ytdl_playlist.extract_info(url, download=False)
        )
        if not data or "entries" not in data:
            return []

        tracks = []
        for entry in data["entries"]:
            if not entry:
                continue
            tracks.append({
                "title":     entry.get("title", "Unknown"),
                "artist":    entry.get("uploader", "Unknown"),
                "album":     None,
                "art":       entry.get("thumbnail", None),
                "spotify":   None,
                "duration":  entry.get("duration", 0),
                "audio_url": f"https://www.youtube.com/watch?v={entry['id']}",
                "yt_url":    f"https://www.youtube.com/watch?v={entry['id']}",
                "pending":   True,   # audio URL needs resolving before playing
            })
        return tracks
    except Exception as e:
        print(f"⚠️ Playlist fetch error: {e}")
        return []


async def resolve_audio(entry: dict, loop: asyncio.AbstractEventLoop) -> dict | None:
    """Resolve the actual stream URL for a pending playlist entry."""
    try:
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(entry["audio_url"], download=False)
        )
        if not data:
            return None
        entry["audio_url"] = data["url"]
        entry["pending"]   = False
        return entry
    except Exception as e:
        print(f"⚠️ Resolve error for {entry['title']}: {e}")
        return None

# ---- Queue store per guild ----
queues: dict[int, list] = {}

def get_queue(guild_id: int) -> list:
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]


# ---- Spotify helpers ----
# Initialized lazily so load_dotenv() in main.py runs first

def get_spotify():
    client_id     = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    try:
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id     = client_id,
            client_secret = client_secret
        ))
    except Exception as e:
        print(f"⚠️ Spotify init error: {e}")
        return None

_sp = None

def spotify_search(query: str) -> dict | None:
    global _sp
    if _sp is None:
        _sp = get_spotify()
        if _sp:
            print("✅ Spotify connected!")
        else:
            print("⚠️ Spotify credentials missing — using YouTube only")
    if not _sp:
        return None
    try:
        results = _sp.search(q=query, type="track", limit=1)
        tracks = results["tracks"]["items"]
        if not tracks:
            return None
        track = tracks[0]
        return {
            "title":    track["name"],
            "artist":   track["artists"][0]["name"],
            "album":    track["album"]["name"],
            "art":      track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "url":      track["external_urls"]["spotify"],
            "duration": track["duration_ms"] // 1000,
            "query":    f"{track['name']} {track['artists'][0]['name']}",
        }
    except Exception as e:
        print(f"⚠️ Spotify search error: {e}")
        return None


def format_duration(seconds: int) -> str:
    mins, secs = divmod(seconds, 60)
    return f"{mins}:{secs:02d}"


# ---- YouTube audio fetcher ----

async def fetch_audio(query: str, loop: asyncio.AbstractEventLoop) -> dict | None:
    try:
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(f"ytsearch:{query}", download=False)
        )
        if not data or "entries" not in data or not data["entries"]:
            return None
        entry = data["entries"][0]
        return {
            "url":      entry["url"],
            "title":    entry.get("title", "Unknown"),
            "duration": entry.get("duration", 0),
            "webpage":  entry.get("webpage_url", ""),
        }
    except Exception as e:
        print(f"⚠️ yt-dlp fetch error: {e}")
        return None


# ---- Play next in queue ----
# queue[0] is always the currently playing song
# only pop when the song finishes to advance the queue

def play_next(ctx: commands.Context):
    queue = get_queue(ctx.guild.id)

    if queue:
        queue.pop(0)

    if not queue:
        asyncio.run_coroutine_threadsafe(
            ctx.send("✅ Queue finished! Add more songs with `!play`."),
            ctx.bot.loop
        )
        return

    entry = queue[0]

    async def _play():
        nonlocal entry
        # Resolve stream URL if this is a pending playlist entry
        if entry.get("pending"):
            resolved = await resolve_audio(entry, ctx.bot.loop)
            if not resolved:
                queue.pop(0)
                play_next(ctx)
                return
            entry = resolved
            queue[0] = entry

        source = discord.FFmpegPCMAudio(entry["audio_url"], **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=0.5)

        def after(error):
            if error:
                print(f"⚠️ Playback error: {error}")
            play_next(ctx)

        ctx.voice_client.play(source, after=after)
        await ctx.send(f"⏭️ Now playing: **{entry['title']}** by {entry['artist']}")

    asyncio.run_coroutine_threadsafe(_play(), ctx.bot.loop)


def setup_music(bot: commands.Bot):

    @bot.command(name="play", aliases=["p"])
    async def play(ctx, *, query: str):
        """Join voice and play a song or playlist."""
        if not ctx.author.voice:
            await ctx.send("⚠️ You need to be in a voice channel first! 🎧")
            return

        vc = ctx.voice_client
        if not vc:
            vc = await ctx.author.voice.channel.connect()
        elif vc.channel != ctx.author.voice.channel:
            await vc.move_to(ctx.author.voice.channel)

        async with ctx.typing():

            # ---- Playlist ----
            if is_playlist(query):
                tracks = await fetch_playlist(query, bot.loop)
                if not tracks:
                    await ctx.send("❌ Couldn't load that playlist. Make sure it's public! 🎵")
                    return

                queue = get_queue(ctx.guild.id)
                queue.extend(tracks)

                embed = discord.Embed(
                    title       = "📋 Playlist Added to Queue",
                    description = f"Loaded **{len(tracks)} songs** into the queue.",
                    color       = discord.Color.blurple()
                )
                embed.set_footer(text="Songs will resolve as they play — first song may take a moment.")
                await ctx.send(embed=embed)

                # Start playing if nothing is currently playing
                if not vc.is_playing() and not vc.is_paused():
                    first = queue[0]
                    resolved = await resolve_audio(first, bot.loop)
                    if resolved:
                        queue[0] = resolved
                        source = discord.FFmpegPCMAudio(resolved["audio_url"], **FFMPEG_OPTIONS)
                        source = discord.PCMVolumeTransformer(source, volume=0.5)

                        def after(error):
                            if error:
                                print(f"⚠️ Playback error: {error}")
                            play_next(ctx)

                        vc.play(source, after=after)
                        await ctx.send(f"🎵 Now playing: **{resolved['title']}** by {resolved['artist']}")
                return

            # ---- Single song ----
            spotify_data = spotify_search(query)
            search_query = spotify_data["query"] if spotify_data else query

            audio_data = await fetch_audio(search_query, bot.loop)
            if not audio_data:
                await ctx.send("❌ Couldn't find that song. Try a different search! 🎵")
                return

            entry = {
                "title":     spotify_data["title"] if spotify_data else audio_data["title"],
                "artist":    spotify_data["artist"] if spotify_data else "Unknown",
                "album":     spotify_data["album"] if spotify_data else None,
                "art":       spotify_data["art"] if spotify_data else None,
                "spotify":   spotify_data["url"] if spotify_data else None,
                "duration":  spotify_data["duration"] if spotify_data else audio_data["duration"],
                "audio_url": audio_data["url"],
                "yt_url":    audio_data["webpage"],
                "pending":   False,
            }

            queue = get_queue(ctx.guild.id)
            queue.append(entry)

            if not vc.is_playing() and not vc.is_paused():
                source = discord.FFmpegPCMAudio(entry["audio_url"], **FFMPEG_OPTIONS)
                source = discord.PCMVolumeTransformer(source, volume=0.5)

                def after(error):
                    if error:
                        print(f"⚠️ Playback error: {error}")
                    play_next(ctx)

                vc.play(source, after=after)

                embed = discord.Embed(
                    title       = "🎵 Now Playing",
                    description = f"**{entry['title']}** by {entry['artist']}",
                    color       = discord.Color.green()
                )
                if entry["art"]:
                    embed.set_thumbnail(url=entry["art"])
                if entry["album"]:
                    embed.add_field(name="Album",    value=entry["album"],                    inline=True)
                embed.add_field(    name="Duration", value=format_duration(entry["duration"]), inline=True)
                if entry["spotify"]:
                    embed.add_field(name="Spotify",  value=f"[Open]({entry['spotify']})",      inline=True)
                embed.set_footer(text="T.O.R.I.E. Music — powered by Spotify + YouTube")
                await ctx.send(embed=embed)

            else:
                embed = discord.Embed(
                    title       = f"➕ Added to Queue — #{len(queue)}",
                    description = f"**{entry['title']}** by {entry['artist']}",
                    color       = discord.Color.blurple()
                )
                if entry["art"]:
                    embed.set_thumbnail(url=entry["art"])
                embed.add_field(name="Duration", value=format_duration(entry["duration"]), inline=True)
                if entry["spotify"]:
                    embed.add_field(name="Spotify", value=f"[Open]({entry['spotify']})", inline=True)
                await ctx.send(embed=embed)

    @bot.command(name="skip", aliases=["s"])
    async def skip(ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            await ctx.send("⚠️ Nothing is playing right now.")
            return
        vc.stop()
        await ctx.send("⏭️ Skipped!")

    @bot.command(name="pause")
    async def pause(ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("⏸️ Paused.")
        else:
            await ctx.send("⚠️ Nothing is playing right now.")

    @bot.command(name="resume")
    async def resume(ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send("▶️ Resumed!")
        else:
            await ctx.send("⚠️ Nothing is paused right now.")

    @bot.command(name="queue", aliases=["q"])
    async def queue_cmd(ctx):
        queue = get_queue(ctx.guild.id)
        if not queue:
            await ctx.send("📋 The queue is empty! Use `!play <song>` to add something.")
            return
        desc = "\n".join([
            f"`{i+1}.` **{e['title']}** by {e['artist']} — {format_duration(e['duration'])}"
            for i, e in enumerate(queue)
        ])
        embed = discord.Embed(
            title       = f"🎵 Queue — {len(queue)} song(s)",
            description = desc,
            color       = discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @bot.command(name="stop")
    async def stop(ctx):
        vc = ctx.voice_client
        if vc:
            get_queue(ctx.guild.id).clear()
            await vc.disconnect()
            await ctx.send("⏹️ Stopped and disconnected. See ya! 👋")
        else:
            await ctx.send("⚠️ I'm not in a voice channel.")

    @bot.command(name="volume", aliases=["vol"])
    async def volume(ctx, vol: int):
        vc = ctx.voice_client
        if not vc or not vc.source:
            await ctx.send("⚠️ Nothing is playing right now.")
            return
        if not 1 <= vol <= 100:
            await ctx.send("⚠️ Volume must be between 1 and 100.")
            return
        vc.source.volume = vol / 100
        await ctx.send(f"🔊 Volume set to {vol}%")

    @bot.command(name="nowplaying", aliases=["np"])
    async def nowplaying(ctx):
        vc = ctx.voice_client
        queue = get_queue(ctx.guild.id)
        if not vc or not vc.is_playing() or not queue:
            await ctx.send("⚠️ Nothing is playing right now.")
            return
        entry = queue[0]
        embed = discord.Embed(
            title       = "🎵 Now Playing",
            description = f"**{entry['title']}** by {entry['artist']}",
            color       = discord.Color.green()
        )
        if entry["art"]:
            embed.set_thumbnail(url=entry["art"])
        if entry["album"]:
            embed.add_field(name="Album",    value=entry["album"],                    inline=True)
        embed.add_field(    name="Duration", value=format_duration(entry["duration"]), inline=True)
        if entry["spotify"]:
            embed.add_field(name="Spotify", value=f"[Open]({entry['spotify']})", inline=True)
        await ctx.send(embed=embed)