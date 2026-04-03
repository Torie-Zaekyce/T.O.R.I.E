import discord
import yt_dlp
import spotipy
import deezer
import asyncio
import random
import os
import re
import requests
from spotipy.oauth2 import SpotifyClientCredentials
from discord.ext import commands


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

YTDL_OPTIONS = {
    "format":             "bestaudio/best",
    "quiet":              True,
    "no_warnings":        True,
    "default_search":     "ytsearch",
    "source_address":     "0.0.0.0",
    "nocheckcertificate": True,
    "ignoreerrors":       False,
    "logtostderr":        False,
    "cookiesfrombrowser": None,
    "extractor_args":     {"youtube": {"skip": ["dash", "hls"]}},
}

YTDL_OPTIONS_PLAYLIST = {
    "format":             "bestaudio/best",
    "quiet":              True,
    "no_warnings":        True,
    "extract_flat":       "in_playlist",
    "source_address":     "0.0.0.0",
    "nocheckcertificate": True,
    "cookiesfrombrowser": None,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options":        "-vn",
}

DEFAULT_VOLUME = 0.5

ytdl          = yt_dlp.YoutubeDL(YTDL_OPTIONS)
ytdl_playlist = yt_dlp.YoutubeDL(YTDL_OPTIONS_PLAYLIST)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

queues:     dict[int, list] = {}
loop_song:  dict[int, bool] = {}
loop_queue: dict[int, bool] = {}

_sp_client: spotipy.Spotify | None = None

def get_spotify() -> spotipy.Spotify | None:
    global _sp_client
    client_id     = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    if _sp_client is None:
        try:
            auth      = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            _sp_client = spotipy.Spotify(auth_manager=auth)
        except Exception as e:
            print(f"⚠️ Spotify init error: {e}")
    return _sp_client

# ---------------------------------------------------------------------------
# Queue helpers
# ---------------------------------------------------------------------------

def get_queue(guild_id: int) -> list:
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

def clear_state(guild_id: int) -> None:
    queues.pop(guild_id, None)
    loop_song.pop(guild_id, None)
    loop_queue.pop(guild_id, None)

def is_looping_song(guild_id: int) -> bool:
    return loop_song.get(guild_id, False)

def is_looping_queue(guild_id: int) -> bool:
    return loop_queue.get(guild_id, False)

# ---------------------------------------------------------------------------
# Formatting / embeds
# ---------------------------------------------------------------------------

def format_duration(seconds) -> str:
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}:{secs:02d}"

def now_playing_embed(entry: dict, guild_id: int) -> discord.Embed:
    embed = discord.Embed(
        title       = "🎵 Now Playing",
        description = f"**{entry['title']}**\nby {entry['artist']}",
        color       = discord.Color.green()
    )
    if entry.get("art"):
        embed.set_thumbnail(url=entry["art"])
    if entry.get("album"):
        embed.add_field(name="Album",    value=entry["album"],                     inline=True)
    embed.add_field(    name="Duration", value=format_duration(entry["duration"]),  inline=True)
    if entry.get("spotify"):
        embed.add_field(name="Spotify",  value=f"[Open]({entry['spotify']})",       inline=True)
    if entry.get("deezer"):
        embed.add_field(name="Deezer",   value=f"[Open]({entry['deezer']})",        inline=True)
    if is_looping_song(guild_id):
        embed.set_footer(text="🔂 Song loop is ON")
    elif is_looping_queue(guild_id):
        embed.set_footer(text="🔁 Queue loop is ON")
    else:
        embed.set_footer(text="T.O.R.I.E. Music — Spotify + Deezer + YouTube")
    return embed

def queued_embed(entry: dict, position: int) -> discord.Embed:
    embed = discord.Embed(
        title       = f"➕ Added to Queue — #{position}",
        description = f"**{entry['title']}**\nby {entry['artist']}",
        color       = discord.Color.blurple()
    )
    if entry.get("art"):
        embed.set_thumbnail(url=entry["art"])
    embed.add_field(name="Duration", value=format_duration(entry["duration"]), inline=True)
    if entry.get("spotify"):
        embed.add_field(name="Spotify", value=f"[Open]({entry['spotify']})", inline=True)
    if entry.get("deezer"):
        embed.add_field(name="Deezer",  value=f"[Open]({entry['deezer']})",  inline=True)
    return embed

# ---------------------------------------------------------------------------
# URL detectors
# ---------------------------------------------------------------------------

def is_spotify_track(q: str)    -> bool: return "open.spotify.com/track/"    in q
def is_spotify_playlist(q: str) -> bool: return "open.spotify.com/playlist/" in q
def is_spotify_album(q: str)    -> bool: return "open.spotify.com/album/"    in q
def is_youtube_playlist(q: str) -> bool: return ("playlist?list=" in q or "&list=" in q) and "youtube.com" in q
def is_deezer_track(q: str)     -> bool: return "deezer.com/track/"    in q or "deezer.com/us/track/"    in q
def is_deezer_playlist(q: str)  -> bool: return "deezer.com/playlist/" in q or "deezer.com/us/playlist/" in q
def is_deezer_album(q: str)     -> bool: return "deezer.com/album/"    in q or "deezer.com/us/album/"    in q

# ---------------------------------------------------------------------------
# Deezer fetchers
# ---------------------------------------------------------------------------

_dz = deezer.Client()

def _dz_entry(track, album_art=None) -> dict:
    art = album_art or (track.album.cover_xl if hasattr(track, "album") and track.album else None)
    return {
        "title":     track.title,
        "artist":    track.artist.name,
        "album":     track.album.title if hasattr(track, "album") and track.album else None,
        "art":       art,
        "spotify":   None,
        "deezer":    track.link,
        "duration":  track.duration,
        "query":     f"{track.title} {track.artist.name}",
        "audio_url": None,
        "yt_url":    None,
        "pending":   True,
    }

def deezer_track(url: str) -> dict | None:
    try:
        track_id = url.rstrip("/").split("/")[-1].split("?")[0]
        entry    = _dz_entry(_dz.get_track(int(track_id)))
        entry["pending"] = False
        return entry
    except Exception as e:
        print(f"⚠️ Deezer track error: {e}")
        return None

def deezer_playlist_tracks(url: str) -> list[dict]:
    try:
        playlist_id = url.rstrip("/").split("/")[-1].split("?")[0]
        return [_dz_entry(t) for t in _dz.get_playlist(int(playlist_id)).tracks]
    except Exception as e:
        print(f"⚠️ Deezer playlist error: {e}")
        return []

def deezer_album_tracks(url: str) -> list[dict]:
    try:
        album_id = url.rstrip("/").split("/")[-1].split("?")[0]
        album    = _dz.get_album(int(album_id))
        return [_dz_entry(t, album_art=album.cover_xl) for t in album.tracks]
    except Exception as e:
        print(f"⚠️ Deezer album error: {e}")
        return []

# ---------------------------------------------------------------------------
# Spotify fetchers
# ---------------------------------------------------------------------------

def spotify_track(url_or_query: str) -> dict | None:
    client = get_spotify()
    if not client:
        return None
    try:
        if is_spotify_track(url_or_query):
            track = client.track(url_or_query.split("/track/")[1].split("?")[0])
        else:
            results = client.search(q=url_or_query, type="track", limit=1)
            items   = results["tracks"]["items"]
            if not items:
                return None
            track = items[0]

        return {
            "title":     track["name"],
            "artist":    track["artists"][0]["name"],
            "album":     track["album"]["name"],
            "art":       track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "spotify":   track["external_urls"]["spotify"],
            "deezer":    None,
            "duration":  track["duration_ms"] // 1000,
            "query":     f"{track['name']} {track['artists'][0]['name']}",
            "pending":   False,
            "audio_url": None,
            "yt_url":    None,
        }
    except Exception as e:
        print(f"⚠️ Spotify track error: {e}")
        return None

def spotify_playlist_tracks(url: str) -> list[dict]:
    try:
        headers = {
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"⚠️ Spotify playlist page returned {resp.status_code}")
            return []

        match = re.search(r'<script id="initial-store" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
        if not match:
            titles  = re.findall(r'"track_name":"([^"]+)"', resp.text)
            artists = re.findall(r'"artist_name":"([^"]+)"', resp.text)
            return [
                {
                    "title": title, "artist": artist, "album": None, "art": None,
                    "spotify": None, "deezer": None, "duration": 0,
                    "query": f"{title} {artist}", "audio_url": None, "yt_url": None, "pending": True,
                }
                for title, artist in zip(titles, artists)
            ]

        import json
        data   = json.loads(match.group(1))
        items  = data.get("entities", {}).get("items", {})
        tracks = []
        for item in items.values():
            if item.get("type") != "track":
                continue
            name        = item.get("name", "Unknown")
            artist_raw  = item.get("artists", {}) or {}
            if isinstance(artist_raw, dict):
                artist_raw = list(artist_raw.values())
            artist_name = artist_raw[0].get("profile", {}).get("name", "Unknown") if artist_raw else "Unknown"
            album       = item.get("albumOfTrack", {}) or {}
            art_items   = album.get("coverArt", {}).get("sources", [])
            tracks.append({
                "title":     name,
                "artist":    artist_name,
                "album":     album.get("name"),
                "art":       art_items[-1].get("url") if art_items else None,
                "spotify":   f"https://open.spotify.com/track/{item.get('id', '')}",
                "deezer":    None,
                "duration":  item.get("duration", {}).get("totalMilliseconds", 0) // 1000,
                "query":     f"{name} {artist_name}",
                "audio_url": None,
                "yt_url":    None,
                "pending":   True,
            })
        return tracks
    except Exception as e:
        print(f"⚠️ Spotify playlist scrape error: {e}")
        return []

def spotify_album_tracks(url: str) -> list[dict]:
    client = get_spotify()
    if not client:
        return []
    try:
        album_id = url.split("/album/")[1].split("?")[0]
        album    = client.album(album_id)
        art      = album["images"][0]["url"] if album["images"] else None
        return [
            {
                "title":     t["name"],
                "artist":    t["artists"][0]["name"],
                "album":     album["name"],
                "art":       art,
                "spotify":   t["external_urls"]["spotify"],
                "deezer":    None,
                "duration":  t["duration_ms"] // 1000,
                "query":     f"{t['name']} {t['artists'][0]['name']}",
                "audio_url": None,
                "yt_url":    None,
                "pending":   True,
            }
            for t in client.album_tracks(album_id)["items"]
        ]
    except Exception as e:
        print(f"⚠️ Spotify album error: {e}")
        return []

# ---------------------------------------------------------------------------
# YouTube fetchers
# ---------------------------------------------------------------------------

async def fetch_playlist(url: str) -> list[dict]:
    loop = asyncio.get_running_loop()
    try:
        data = await loop.run_in_executor(
            None, lambda: ytdl_playlist.extract_info(url, download=False)
        )
        if not data or "entries" not in data:
            return []
        return [
            {
                "title":     e.get("title", "Unknown"),
                "artist":    e.get("uploader", "Unknown"),
                "album":     None,
                "art":       e.get("thumbnail"),
                "spotify":   None,
                "deezer":    None,
                "duration":  e.get("duration", 0),
                "query":     f"{e.get('title', '')} {e.get('uploader', '')}".strip(),
                "audio_url": f"https://www.youtube.com/watch?v={e['id']}",
                "yt_url":    f"https://www.youtube.com/watch?v={e['id']}",
                "pending":   True,
            }
            for e in data["entries"] if e
        ]
    except Exception as e:
        print(f"⚠️ Playlist fetch error: {e}")
        return []

async def resolve_audio(entry: dict) -> dict | None:
    loop = asyncio.get_running_loop()
    try:
        search = entry.get("query") or entry.get("audio_url") or entry["title"]
        query  = search if search.startswith("http") else f"ytsearch:{search}"
        data   = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if not data:
            return None
        if "entries" in data:
            data = data["entries"][0]
        entry["audio_url"] = data["url"]
        entry["yt_url"]    = data.get("webpage_url", "")
        entry["pending"]   = False
        return entry
    except Exception as e:
        print(f"⚠️ Resolve error for {entry.get('title', '?')}: {e}")
        return None

async def fetch_audio(query: str) -> dict | None:
    loop = asyncio.get_running_loop()
    try:
        # Don't prefix direct URLs with ytsearch: — only search queries need it
        search = query if query.startswith("http") else f"ytsearch:{query}"
        data   = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(search, download=False)
        )
        if not data:
            return None
        if "entries" in data:
            data = data["entries"][0]
        return {
            "url":      data["url"],
            "title":    data.get("title", "Unknown"),
            "duration": data.get("duration", 0),
            "webpage":  data.get("webpage_url", ""),
        }
    except Exception as e:
        print(f"⚠️ yt-dlp fetch error: {e}")
        return None


def _make_source(audio_url: str) -> discord.PCMVolumeTransformer:
    raw = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
    return discord.PCMVolumeTransformer(raw, volume=DEFAULT_VOLUME)

async def _start_or_queue(ctx: commands.Context, entry: dict, vc: discord.VoiceClient) -> None:
    """
    If nothing is playing: resolve the entry and start playback immediately.
    If something is already playing: just send the queued embed.
    Pre-fetches the next pending track in the background while the current one plays.
    """
    queue    = get_queue(ctx.guild.id)
    guild_id = ctx.guild.id

    if vc.is_playing() or vc.is_paused():
        await ctx.send(embed=queued_embed(entry, len(queue)))
        return

    if entry.get("pending"):
        resolved = await resolve_audio(entry)
        if not resolved:
            await ctx.send(embed=discord.Embed(
                description="❌ Couldn't resolve audio for this track.", color=discord.Color.red()
            ))
            return
        queue[queue.index(entry)] = resolved
        entry = resolved

    source = _make_source(entry["audio_url"])

    def after(error):
        if error:
            print(f"⚠️ Playback error: {error}")
        asyncio.run_coroutine_threadsafe(_play_next(ctx), ctx.bot.loop)

    vc.play(source, after=after)
    await ctx.send(embed=now_playing_embed(entry, guild_id))

    asyncio.create_task(_prefetch_next(ctx))

async def _prefetch_next(ctx: commands.Context) -> None:
    """Resolve the second queue entry in the background while the current song plays."""
    queue = get_queue(ctx.guild.id)
    if len(queue) < 2:
        return
    nxt = queue[1]
    if nxt.get("pending"):
        resolved = await resolve_audio(nxt)
        q = get_queue(ctx.guild.id)
        if len(q) > 1 and q[1] is nxt and resolved:
            q[1] = resolved

async def _play_next(ctx: commands.Context) -> None:
    queue    = get_queue(ctx.guild.id)
    guild_id = ctx.guild.id
    vc       = ctx.voice_client

    if not vc or not queue:
        return

    current = queue[0]

    if is_looping_song(guild_id):
        if current.get("pending"):
            resolved = await resolve_audio(current)
            if not resolved:
                queue.pop(0)
                await _play_next(ctx)
                return
            queue[0] = resolved
            current  = resolved
    else:
        finished = queue.pop(0)
        if is_looping_queue(guild_id):
            finished["pending"] = True
            queue.append(finished)

        if not queue:
            await ctx.send(embed=discord.Embed(
                description="✅ Queue finished! Add more songs with `t!play`.",
                color       = discord.Color.greyple()
            ))
            return

        current = queue[0]
        if current.get("pending"):
            resolved = await resolve_audio(current)
            if not resolved:
                queue.pop(0)
                await _play_next(ctx)
                return
            queue[0] = resolved
            current  = resolved

    source = _make_source(current["audio_url"])

    def after(error):
        if error:
            print(f"⚠️ Playback error: {error}")
        asyncio.run_coroutine_threadsafe(_play_next(ctx), ctx.bot.loop)

    vc.play(source, after=after)

    if not is_looping_song(guild_id):
        await ctx.send(embed=now_playing_embed(current, guild_id))
        asyncio.create_task(_prefetch_next(ctx))


def play_next(ctx: commands.Context) -> None:
    """Sync shim for external callers that need to schedule _play_next from a thread."""
    asyncio.run_coroutine_threadsafe(_play_next(ctx), ctx.bot.loop)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def setup_music(bot: commands.Bot):

    async def _load_collection(ctx, tracks: list[dict], label: str, emoji: str, color: discord.Color) -> None:
        """Shared helper for all playlist/album branches. Loads tracks and starts playback if idle."""
        vc = ctx.voice_client
        if not tracks:
            await ctx.send(embed=discord.Embed(
                description=f"❌ Couldn't load that {label}.", color=discord.Color.red()
            ))
            return

        queue = get_queue(ctx.guild.id)
        queue.extend(tracks)

        await ctx.send(embed=discord.Embed(
            title       = f"{emoji} {label.title()} Added",
            description = f"Loaded **{len(tracks)} songs** into the queue.",
            color       = color
        ).set_footer(text="Audio resolves via YouTube as each song plays."))

        if not vc.is_playing() and not vc.is_paused():
            await _start_or_queue(ctx, queue[0], vc)

    # ---- play ----

    @bot.command(name="play", aliases=["p"])
    async def play(ctx, *, query: str):
        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(
                description="⚠️ You need to be in a voice channel first! 🎧", color=discord.Color.red()
            ))
            return

        vc = ctx.voice_client
        if not vc:
            vc = await ctx.author.voice.channel.connect()
        elif vc.channel != ctx.author.voice.channel:
            await vc.move_to(ctx.author.voice.channel)

        sp_green   = discord.Color.green()
        dz_purple  = discord.Color.from_rgb(169, 99, 255)
        yt_blue    = discord.Color.blurple()

        async with ctx.typing():

            if is_spotify_playlist(query):
                tracks = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: spotify_playlist_tracks(query)
                )
                await _load_collection(ctx, tracks, "Spotify playlist", "📋", sp_green)
                return

            if is_spotify_album(query):
                tracks = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: spotify_album_tracks(query)
                )
                await _load_collection(ctx, tracks, "Spotify album", "💿", sp_green)
                return

            if is_spotify_track(query):
                spotify_data = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: spotify_track(query)
                )
                if not spotify_data:
                    await ctx.send(embed=discord.Embed(
                        description="❌ Couldn't find that Spotify track.", color=discord.Color.red()
                    ))
                    return
                audio = await fetch_audio(spotify_data["query"])
                if not audio:
                    await ctx.send(embed=discord.Embed(
                        description="❌ Couldn't find audio on YouTube for this track.", color=discord.Color.red()
                    ))
                    return
                entry = {**spotify_data, "audio_url": audio["url"], "yt_url": audio["webpage"], "pending": False}
                queue = get_queue(ctx.guild.id)
                queue.append(entry)
                await _start_or_queue(ctx, entry, vc)
                return

            if is_youtube_playlist(query):
                tracks = await fetch_playlist(query)
                await _load_collection(ctx, tracks, "YouTube playlist", "📋", yt_blue)
                return

            if is_deezer_playlist(query):
                tracks = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: deezer_playlist_tracks(query)
                )
                await _load_collection(ctx, tracks, "Deezer playlist", "📋", dz_purple)
                return

            if is_deezer_album(query):
                tracks = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: deezer_album_tracks(query)
                )
                await _load_collection(ctx, tracks, "Deezer album", "💿", dz_purple)
                return

            if is_deezer_track(query):
                dz_data = await asyncio.get_running_loop().run_in_executor(
                    None, lambda: deezer_track(query)
                )
                if not dz_data:
                    await ctx.send(embed=discord.Embed(
                        description="❌ Couldn't find that Deezer track.", color=discord.Color.red()
                    ))
                    return
                audio = await fetch_audio(dz_data["query"])
                if not audio:
                    await ctx.send(embed=discord.Embed(
                        description="❌ Couldn't find audio on YouTube for this track.", color=discord.Color.red()
                    ))
                    return
                entry = {**dz_data, "audio_url": audio["url"], "yt_url": audio["webpage"], "pending": False}
                queue = get_queue(ctx.guild.id)
                queue.append(entry)
                await _start_or_queue(ctx, entry, vc)
                return

            # Single song — search or direct YouTube URL
            spotify_data = await asyncio.get_running_loop().run_in_executor(
                None, lambda: spotify_track(query)
            )
            audio = await fetch_audio(spotify_data["query"] if spotify_data else query)
            if not audio:
                await ctx.send(embed=discord.Embed(
                    description="❌ Couldn't find that song. Try a different search! 🎵",
                    color=discord.Color.red()
                ))
                return

            entry = {
                "title":     spotify_data["title"]    if spotify_data else audio["title"],
                "artist":    spotify_data["artist"]   if spotify_data else "Unknown",
                "album":     spotify_data["album"]    if spotify_data else None,
                "art":       spotify_data["art"]      if spotify_data else None,
                "spotify":   spotify_data["spotify"]  if spotify_data else None,
                "deezer":    None,
                "duration":  spotify_data["duration"] if spotify_data else audio["duration"],
                "query":     spotify_data["query"]    if spotify_data else query,
                "audio_url": audio["url"],
                "yt_url":    audio["webpage"],
                "pending":   False,
            }
            queue = get_queue(ctx.guild.id)
            queue.append(entry)
            await _start_or_queue(ctx, entry, vc)

    # ---- skip ----

    @bot.command(name="skip", aliases=["s"])
    async def skip(ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is playing right now.", color=discord.Color.orange()))
            return
        vc.stop()
        await ctx.send(embed=discord.Embed(description="⏭️ Skipped!", color=discord.Color.blurple()))

    # ---- pause / resume ----

    @bot.command(name="pause")
    async def pause(ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send(embed=discord.Embed(description="⏸️ Paused.", color=discord.Color.orange()))
        else:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is playing right now.", color=discord.Color.orange()))

    @bot.command(name="resume")
    async def resume(ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await ctx.send(embed=discord.Embed(description="▶️ Resumed!", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is paused right now.", color=discord.Color.orange()))

    # ---- queue ----

    @bot.command(name="queue", aliases=["q"])
    async def queue_cmd(ctx):
        queue = get_queue(ctx.guild.id)
        if not queue:
            await ctx.send(embed=discord.Embed(
                description="📋 The queue is empty! Use `t!play <song>` to add something.",
                color=discord.Color.greyple()
            ))
            return

        per_page    = 10
        total_pages = (len(queue) + per_page - 1) // per_page

        def build_embed(page: int) -> discord.Embed:
            start = page * per_page
            lines = [
                f"{'▶️' if i == 0 else f'`{i+1}.`'} **{e['title']}** by {e['artist']} — {format_duration(e['duration'])}"
                for i, e in enumerate(queue[start:start + per_page], start=start)
            ]
            loop_status = " 🔂" if is_looping_song(ctx.guild.id) else (" 🔁" if is_looping_queue(ctx.guild.id) else "")
            return discord.Embed(
                title       = f"🎵 Queue — {len(queue)} song(s){loop_status}",
                description = "\n".join(lines),
                color       = discord.Color.blurple()
            ).set_footer(text=f"Page {page + 1} of {total_pages}")

        class QueueView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.page = 0
                self._update_buttons()

            def _update_buttons(self):
                self.prev_btn.disabled = self.page == 0
                self.next_btn.disabled = self.page >= total_pages - 1

            @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
            async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the command author can flip pages!", ephemeral=True)
                    return
                self.page -= 1
                self._update_buttons()
                await interaction.response.edit_message(embed=build_embed(self.page), view=self)

            @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
            async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the command author can flip pages!", ephemeral=True)
                    return
                self.page += 1
                self._update_buttons()
                await interaction.response.edit_message(embed=build_embed(self.page), view=self)

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                try:
                    await self.message.edit(view=self)
                except Exception:
                    pass

        view         = QueueView()
        view.message = await ctx.send(embed=build_embed(0), view=view)

    # ---- clearqueue ----

    @bot.command(name="clearqueue", aliases=["cq"])
    async def clearqueue(ctx):
        queue = get_queue(ctx.guild.id)
        if not queue:
            await ctx.send(embed=discord.Embed(description="📋 The queue is already empty!", color=discord.Color.greyple()))
            return
        current = queue[0] if (ctx.voice_client and ctx.voice_client.is_playing()) else None
        queue.clear()
        if current:
            queue.append(current)
            await ctx.send(embed=discord.Embed(
                description=f"🗑️ Queue cleared! Still playing: **{current['title']}**",
                color=discord.Color.blurple()
            ))
        else:
            await ctx.send(embed=discord.Embed(description="🗑️ Queue cleared!", color=discord.Color.blurple()))

    # ---- loop ----

    @bot.command(name="loop", aliases=["l"])
    async def loop(ctx, mode: str = None):
        guild_id = ctx.guild.id
        if mode is None:
            status = "🔂 Song loop" if is_looping_song(guild_id) else ("🔁 Queue loop" if is_looping_queue(guild_id) else "➡️ No loop")
            await ctx.send(embed=discord.Embed(
                description=f"Current loop mode: **{status}**\nUse `t!loop song`, `t!loop queue`, or `t!loop off`.",
                color=discord.Color.blurple()
            ))
            return

        mode = mode.lower()
        if mode == "song":
            loop_song[guild_id], loop_queue[guild_id] = True, False
            await ctx.send(embed=discord.Embed(description="🔂 Song loop **ON** — current song will repeat.", color=discord.Color.blurple()))
        elif mode == "queue":
            loop_song[guild_id], loop_queue[guild_id] = False, True
            await ctx.send(embed=discord.Embed(description="🔁 Queue loop **ON** — queue will repeat when finished.", color=discord.Color.blurple()))
        elif mode == "off":
            loop_song[guild_id], loop_queue[guild_id] = False, False
            await ctx.send(embed=discord.Embed(description="➡️ Loop **OFF**.", color=discord.Color.greyple()))
        else:
            await ctx.send(embed=discord.Embed(
                description="⚠️ Invalid mode. Use `t!loop song`, `t!loop queue`, or `t!loop off`.",
                color=discord.Color.red()
            ))

    # ---- shuffle ----

    @bot.command(name="shuffle", aliases=["sh"])
    async def shuffle(ctx):
        queue = get_queue(ctx.guild.id)
        if len(queue) < 3:
            await ctx.send(embed=discord.Embed(description="⚠️ Need at least 3 songs in the queue to shuffle.", color=discord.Color.orange()))
            return
        current, rest = queue[0], queue[1:]
        random.shuffle(rest)
        queue.clear()
        queue.append(current)
        queue.extend(rest)
        await ctx.send(embed=discord.Embed(
            title       = "🔀 Queue Shuffled!",
            description = f"**{len(rest)}** songs rearranged.\nCurrently playing: **{current['title']}**",
            color       = discord.Color.blurple()
        ))

    # ---- stop ----

    @bot.command(name="stop")
    async def stop(ctx):
        vc = ctx.voice_client
        if vc:
            clear_state(ctx.guild.id)
            await vc.disconnect()
            await ctx.send(embed=discord.Embed(description="⏹️ Stopped and disconnected. See ya! 👋", color=discord.Color.red()))
        else:
            await ctx.send(embed=discord.Embed(description="⚠️ I'm not in a voice channel.", color=discord.Color.orange()))

    # ---- volume ----

    @bot.command(name="volume", aliases=["vol"])
    async def volume(ctx, vol: int):
        vc = ctx.voice_client
        if not vc or not vc.source:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is playing right now.", color=discord.Color.orange()))
            return
        if not 1 <= vol <= 100:
            await ctx.send(embed=discord.Embed(description="⚠️ Volume must be between 1 and 100.", color=discord.Color.red()))
            return
        vc.source.volume = vol / 100
        await ctx.send(embed=discord.Embed(description=f"🔊 Volume set to **{vol}%**", color=discord.Color.blurple()))

    # ---- nowplaying ----

    @bot.command(name="nowplaying", aliases=["np", "current", "playing"])
    async def nowplaying(ctx):
        vc    = ctx.voice_client
        queue = get_queue(ctx.guild.id)
        if not vc or (not vc.is_playing() and not vc.is_paused()) or not queue:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is playing right now.", color=discord.Color.orange()))
            return
        entry = queue[0]
        embed = now_playing_embed(entry, ctx.guild.id)
        if vc.is_paused():
            embed.title = "⏸️ Currently Paused"
        if len(queue) > 1:
            nxt = queue[1]
            embed.add_field(name="Up Next", value=f"**{nxt['title']}** by {nxt['artist']}", inline=False)
        await ctx.send(embed=embed)