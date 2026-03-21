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


YTDL_OPTIONS = {
    "format":              "bestaudio/best",
    "quiet":               True,
    "no_warnings":         True,
    "default_search":      "ytsearch",
    "source_address":      "0.0.0.0",
    "nocheckcertificate":  True,
    "ignoreerrors":        False,
    "logtostderr":         False,
    "cookiesfrombrowser":  None,
    "extractor_args":      {"youtube": {"skip": ["dash", "hls"]}},
}

YTDL_OPTIONS_PLAYLIST = {
    "format":              "bestaudio/best",
    "quiet":               True,
    "no_warnings":         True,
    "extract_flat":        "in_playlist",
    "source_address":      "0.0.0.0",
    "nocheckcertificate":  True,
    "cookiesfrombrowser":  None,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options":        "-vn",
}

ytdl          = yt_dlp.YoutubeDL(YTDL_OPTIONS)
ytdl_playlist = yt_dlp.YoutubeDL(YTDL_OPTIONS_PLAYLIST)

queues:     dict[int, list] = {}
loop_song:  dict[int, bool] = {}
loop_queue: dict[int, bool] = {}

_sp_auth = None

def get_spotify():
    global _sp_auth
    client_id     = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    try:
        if _sp_auth is None:
            _sp_auth = SpotifyClientCredentials(
                client_id     = client_id,
                client_secret = client_secret
            )
        return spotipy.Spotify(auth_manager=_sp_auth)
    except Exception as e:
        print(f"⚠️ Spotify init error: {e}")
        return None

def sp() -> spotipy.Spotify | None:
    return get_spotify()


def get_queue(guild_id: int) -> list:
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

def is_looping_song(guild_id: int) -> bool:
    return loop_song.get(guild_id, False)

def is_looping_queue(guild_id: int) -> bool:
    return loop_queue.get(guild_id, False)

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
        embed.add_field(name="Album",    value=entry["album"],                    inline=True)
    embed.add_field(    name="Duration", value=format_duration(entry["duration"]), inline=True)
    if entry.get("spotify"):
        embed.add_field(name="Spotify",  value=f"[Open]({entry['spotify']})",      inline=True)
    if entry.get("deezer"):
        embed.add_field(name="Deezer",   value=f"[Open]({entry['deezer']})",       inline=True)
    if is_looping_song(guild_id):
        embed.set_footer(text="🔂 Song loop is ON")
    elif is_looping_queue(guild_id):
        embed.set_footer(text="🔁 Queue loop is ON")
    else:
        embed.set_footer(text="T.O.R.I.E. Music — Spotify + Deezer + YouTube")
    return embed


# ---- Spotify URL detectors ----

def is_spotify_track(query: str) -> bool:
    return "open.spotify.com/track/" in query

def is_spotify_playlist(query: str) -> bool:
    return "open.spotify.com/playlist/" in query

def is_spotify_album(query: str) -> bool:
    return "open.spotify.com/album/" in query

def is_youtube_playlist(query: str) -> bool:
    return ("playlist?list=" in query or "&list=" in query) and "youtube.com" in query

# ---- Deezer URL detectors ----

def is_deezer_track(query: str) -> bool:
    return "deezer.com/track/" in query or "deezer.com/us/track/" in query

def is_deezer_playlist(query: str) -> bool:
    return "deezer.com/playlist/" in query or "deezer.com/us/playlist/" in query

def is_deezer_album(query: str) -> bool:
    return "deezer.com/album/" in query or "deezer.com/us/album/" in query


# ---- Deezer client (no API key needed) ----

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
        track    = _dz.get_track(int(track_id))
        entry    = _dz_entry(track)
        entry["pending"] = False
        return entry
    except Exception as e:
        print(f"⚠️ Deezer track error: {e}")
        return None

def deezer_playlist_tracks(url: str) -> list[dict]:
    try:
        playlist_id = url.rstrip("/").split("/")[-1].split("?")[0]
        playlist    = _dz.get_playlist(int(playlist_id))
        return [_dz_entry(t) for t in playlist.tracks]
    except Exception as e:
        print(f"⚠️ Deezer playlist error: {e}")
        return []

def deezer_album_tracks(url: str) -> list[dict]:
    try:
        album_id = url.rstrip("/").split("/")[-1].split("?")[0]
        album    = _dz.get_album(int(album_id))
        art      = album.cover_xl
        return [_dz_entry(t, album_art=art) for t in album.tracks]
    except Exception as e:
        print(f"⚠️ Deezer album error: {e}")
        return []


# ---- Spotify fetchers ----

def spotify_track(url_or_query: str) -> dict | None:
    client = sp()
    if not client:
        return None
    try:
        if is_spotify_track(url_or_query):
            track_id = url_or_query.split("/track/")[1].split("?")[0]
            track    = client.track(track_id)
        else:
            results = client.search(q=url_or_query, type="track", limit=1)
            items   = results["tracks"]["items"]
            if not items:
                return None
            track = items[0]

        return {
            "title":    track["name"],
            "artist":   track["artists"][0]["name"],
            "album":    track["album"]["name"],
            "art":      track["album"]["images"][0]["url"] if track["album"]["images"] else None,
            "spotify":  track["external_urls"]["spotify"],
            "deezer":   None,
            "duration": track["duration_ms"] // 1000,
            "query":    f"{track['name']} {track['artists'][0]['name']}",
            "pending":  False,
            "audio_url": None,
            "yt_url":   None,
        }
    except Exception as e:
        print(f"⚠️ Spotify track error: {e}")
        return None


def spotify_playlist_tracks(url: str) -> list[dict]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
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
            tracks  = []
            for title, artist in zip(titles, artists):
                tracks.append({
                    "title":     title,
                    "artist":    artist,
                    "album":     None,
                    "art":       None,
                    "spotify":   None,
                    "deezer":    None,
                    "duration":  0,
                    "query":     f"{title} {artist}",
                    "audio_url": None,
                    "yt_url":    None,
                    "pending":   True,
                })
            return tracks

        import json
        data   = json.loads(match.group(1))
        items  = data.get("entities", {}).get("items", {})
        tracks = []
        for key, item in items.items():
            if item.get("type") != "track":
                continue
            name   = item.get("name", "Unknown")
            artist = (item.get("artists", {}) or {})
            if isinstance(artist, dict):
                artist = list(artist.values())
            artist_name = artist[0].get("profile", {}).get("name", "Unknown") if artist else "Unknown"
            album       = item.get("albumOfTrack", {}) or {}
            art_items   = album.get("coverArt", {}).get("sources", [])
            art         = art_items[-1].get("url") if art_items else None
            duration_ms = item.get("duration", {}).get("totalMilliseconds", 0)
            tracks.append({
                "title":     name,
                "artist":    artist_name,
                "album":     album.get("name"),
                "art":       art,
                "spotify":   f"https://open.spotify.com/track/{item.get('id', '')}",
                "deezer":    None,
                "duration":  duration_ms // 1000,
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
    client = sp()
    if not client:
        return []
    try:
        album_id = url.split("/album/")[1].split("?")[0]
        album    = client.album(album_id)
        results  = client.album_tracks(album_id)
        art      = album["images"][0]["url"] if album["images"] else None
        tracks   = []
        for track in results["items"]:
            tracks.append({
                "title":     track["name"],
                "artist":    track["artists"][0]["name"],
                "album":     album["name"],
                "art":       art,
                "spotify":   track["external_urls"]["spotify"],
                "deezer":    None,
                "duration":  track["duration_ms"] // 1000,
                "query":     f"{track['name']} {track['artists'][0]['name']}",
                "audio_url": None,
                "yt_url":    None,
                "pending":   True,
            })
        return tracks
    except Exception as e:
        print(f"⚠️ Spotify album error: {e}")
        return []


# ---- YouTube fetchers ----

async def fetch_playlist(url: str, loop: asyncio.AbstractEventLoop) -> list[dict]:
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
                "deezer":    None,
                "duration":  entry.get("duration", 0),
                "audio_url": f"https://www.youtube.com/watch?v={entry['id']}",
                "yt_url":    f"https://www.youtube.com/watch?v={entry['id']}",
                "pending":   True,
            })
        return tracks
    except Exception as e:
        print(f"⚠️ Playlist fetch error: {e}")
        return []


async def resolve_audio(entry: dict, loop: asyncio.AbstractEventLoop) -> dict | None:
    try:
        search = entry.get("query") or entry.get("audio_url") or entry["title"]
        query  = search if search.startswith("http") else f"ytsearch:{search}"
        data   = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(query, download=False)
        )
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


# ---- Playback ----

def play_next(ctx: commands.Context):
    queue    = get_queue(ctx.guild.id)
    guild_id = ctx.guild.id

    if not queue:
        return

    current = queue[0]

    if is_looping_song(guild_id):
        async def _replay():
            entry = current
            if entry.get("pending"):
                resolved = await resolve_audio(entry, ctx.bot.loop)
                if not resolved:
                    queue.pop(0)
                    play_next(ctx)
                    return
                entry    = resolved
                queue[0] = entry

            source = discord.FFmpegPCMAudio(entry["audio_url"], **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=0.5)

            def after(error):
                if error:
                    print(f"⚠️ Playback error: {error}")
                play_next(ctx)

            ctx.voice_client.play(source, after=after)

        asyncio.run_coroutine_threadsafe(_replay(), ctx.bot.loop)
        return

    finished = queue.pop(0)

    if is_looping_queue(guild_id):
        finished["pending"] = True
        queue.append(finished)

    if not queue:
        embed = discord.Embed(
            description = "✅ Queue finished! Add more songs with `t!play`.",
            color       = discord.Color.greyple()
        )
        asyncio.run_coroutine_threadsafe(ctx.send(embed=embed), ctx.bot.loop)
        return

    entry = queue[0]

    async def _play():
        nonlocal entry
        if entry.get("pending"):
            resolved = await resolve_audio(entry, ctx.bot.loop)
            if not resolved:
                queue.pop(0)
                play_next(ctx)
                return
            entry    = resolved
            queue[0] = entry

        source = discord.FFmpegPCMAudio(entry["audio_url"], **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=0.5)

        def after(error):
            if error:
                print(f"⚠️ Playback error: {error}")
            play_next(ctx)

        ctx.voice_client.play(source, after=after)
        await ctx.send(embed=now_playing_embed(entry, guild_id))

    asyncio.run_coroutine_threadsafe(_play(), ctx.bot.loop)


def setup_music(bot: commands.Bot):

    @bot.command(name="play", aliases=["p"])
    async def play(ctx, *, query: str):
        if not ctx.author.voice:
            embed = discord.Embed(description="⚠️ You need to be in a voice channel first! 🎧", color=discord.Color.red())
            await ctx.send(embed=embed)
            return

        vc = ctx.voice_client
        if not vc:
            vc = await ctx.author.voice.channel.connect()
        elif vc.channel != ctx.author.voice.channel:
            await vc.move_to(ctx.author.voice.channel)

        async with ctx.typing():

            # ---- Spotify playlist ----
            if is_spotify_playlist(query):
                tracks = await asyncio.get_event_loop().run_in_executor(None, lambda: spotify_playlist_tracks(query))
                if not tracks:
                    embed = discord.Embed(description="❌ Couldn't load that Spotify playlist. Make sure it's public!", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                queue = get_queue(ctx.guild.id)
                queue.extend(tracks)

                embed = discord.Embed(
                    title       = "📋 Spotify Playlist Added",
                    description = f"Loaded **{len(tracks)} songs** into the queue.",
                    color       = discord.Color.green()
                )
                embed.set_footer(text="Audio resolves via YouTube as each song plays.")
                await ctx.send(embed=embed)

                if not vc.is_playing() and not vc.is_paused():
                    resolved = await resolve_audio(queue[0], bot.loop)
                    if resolved:
                        queue[0] = resolved
                        source   = discord.FFmpegPCMAudio(resolved["audio_url"], **FFMPEG_OPTIONS)
                        source   = discord.PCMVolumeTransformer(source, volume=0.5)
                        def after(error):
                            if error: print(f"⚠️ Playback error: {error}")
                            play_next(ctx)
                        vc.play(source, after=after)
                        await ctx.send(embed=now_playing_embed(resolved, ctx.guild.id))
                return

            # ---- Spotify album ----
            if is_spotify_album(query):
                tracks = await asyncio.get_event_loop().run_in_executor(None, lambda: spotify_album_tracks(query))
                if not tracks:
                    embed = discord.Embed(description="❌ Couldn't load that Spotify album.", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                queue = get_queue(ctx.guild.id)
                queue.extend(tracks)

                embed = discord.Embed(
                    title       = "💿 Spotify Album Added",
                    description = f"Loaded **{len(tracks)} songs** into the queue.",
                    color       = discord.Color.green()
                )
                embed.set_footer(text="Audio resolves via YouTube as each song plays.")
                await ctx.send(embed=embed)

                if not vc.is_playing() and not vc.is_paused():
                    resolved = await resolve_audio(queue[0], bot.loop)
                    if resolved:
                        queue[0] = resolved
                        source   = discord.FFmpegPCMAudio(resolved["audio_url"], **FFMPEG_OPTIONS)
                        source   = discord.PCMVolumeTransformer(source, volume=0.5)
                        def after(error):
                            if error: print(f"⚠️ Playback error: {error}")
                            play_next(ctx)
                        vc.play(source, after=after)
                        await ctx.send(embed=now_playing_embed(resolved, ctx.guild.id))
                return

            # ---- Spotify track ----
            if is_spotify_track(query):
                spotify_data = await asyncio.get_event_loop().run_in_executor(None, lambda: spotify_track(query))
                if not spotify_data:
                    embed = discord.Embed(description="❌ Couldn't find that Spotify track.", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                audio_data = await fetch_audio(spotify_data["query"], bot.loop)
                if not audio_data:
                    embed = discord.Embed(description="❌ Couldn't find audio on YouTube for this track.", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                entry = {**spotify_data, "audio_url": audio_data["url"], "yt_url": audio_data["webpage"], "pending": False}
                queue = get_queue(ctx.guild.id)
                queue.append(entry)

                if not vc.is_playing() and not vc.is_paused():
                    source = discord.FFmpegPCMAudio(entry["audio_url"], **FFMPEG_OPTIONS)
                    source = discord.PCMVolumeTransformer(source, volume=0.5)
                    def after(error):
                        if error: print(f"⚠️ Playback error: {error}")
                        play_next(ctx)
                    vc.play(source, after=after)
                    await ctx.send(embed=now_playing_embed(entry, ctx.guild.id))
                else:
                    embed = discord.Embed(
                        title       = f"➕ Added to Queue — #{len(queue)}",
                        description = f"**{entry['title']}**\nby {entry['artist']}",
                        color       = discord.Color.blurple()
                    )
                    if entry.get("art"):
                        embed.set_thumbnail(url=entry["art"])
                    embed.add_field(name="Duration", value=format_duration(entry["duration"]), inline=True)
                    embed.add_field(name="Spotify",  value=f"[Open]({entry['spotify']})",      inline=True)
                    await ctx.send(embed=embed)
                return

            # ---- YouTube playlist ----
            if is_youtube_playlist(query):
                tracks = await fetch_playlist(query, bot.loop)
                if not tracks:
                    embed = discord.Embed(description="❌ Couldn't load that playlist. Make sure it's public! 🎵", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                queue = get_queue(ctx.guild.id)
                queue.extend(tracks)

                embed = discord.Embed(
                    title       = "📋 YouTube Playlist Added",
                    description = f"Loaded **{len(tracks)} songs** into the queue.",
                    color       = discord.Color.blurple()
                )
                embed.set_footer(text="Songs resolve as they play — first song may take a moment.")
                await ctx.send(embed=embed)

                if not vc.is_playing() and not vc.is_paused():
                    resolved = await resolve_audio(queue[0], bot.loop)
                    if resolved:
                        queue[0] = resolved
                        source   = discord.FFmpegPCMAudio(resolved["audio_url"], **FFMPEG_OPTIONS)
                        source   = discord.PCMVolumeTransformer(source, volume=0.5)
                        def after(error):
                            if error: print(f"⚠️ Playback error: {error}")
                            play_next(ctx)
                        vc.play(source, after=after)
                        await ctx.send(embed=now_playing_embed(resolved, ctx.guild.id))
                return

            # ---- Deezer playlist ----
            if is_deezer_playlist(query):
                tracks = await asyncio.get_event_loop().run_in_executor(None, lambda: deezer_playlist_tracks(query))
                if not tracks:
                    embed = discord.Embed(description="❌ Couldn't load that Deezer playlist. Make sure it's public!", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                queue = get_queue(ctx.guild.id)
                queue.extend(tracks)

                embed = discord.Embed(
                    title       = "📋 Deezer Playlist Added",
                    description = f"Loaded **{len(tracks)} songs** into the queue.",
                    color       = discord.Color.from_rgb(169, 99, 255)
                )
                embed.set_footer(text="Audio resolves via YouTube as each song plays.")
                await ctx.send(embed=embed)

                if not vc.is_playing() and not vc.is_paused():
                    resolved = await resolve_audio(queue[0], bot.loop)
                    if resolved:
                        queue[0] = resolved
                        source   = discord.FFmpegPCMAudio(resolved["audio_url"], **FFMPEG_OPTIONS)
                        source   = discord.PCMVolumeTransformer(source, volume=0.5)
                        def after(error):
                            if error: print(f"⚠️ Playback error: {error}")
                            play_next(ctx)
                        vc.play(source, after=after)
                        await ctx.send(embed=now_playing_embed(resolved, ctx.guild.id))
                return

            # ---- Deezer album ----
            if is_deezer_album(query):
                tracks = await asyncio.get_event_loop().run_in_executor(None, lambda: deezer_album_tracks(query))
                if not tracks:
                    embed = discord.Embed(description="❌ Couldn't load that Deezer album.", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                queue = get_queue(ctx.guild.id)
                queue.extend(tracks)

                embed = discord.Embed(
                    title       = "💿 Deezer Album Added",
                    description = f"Loaded **{len(tracks)} songs** into the queue.",
                    color       = discord.Color.from_rgb(169, 99, 255)
                )
                embed.set_footer(text="Audio resolves via YouTube as each song plays.")
                await ctx.send(embed=embed)

                if not vc.is_playing() and not vc.is_paused():
                    resolved = await resolve_audio(queue[0], bot.loop)
                    if resolved:
                        queue[0] = resolved
                        source   = discord.FFmpegPCMAudio(resolved["audio_url"], **FFMPEG_OPTIONS)
                        source   = discord.PCMVolumeTransformer(source, volume=0.5)
                        def after(error):
                            if error: print(f"⚠️ Playback error: {error}")
                            play_next(ctx)
                        vc.play(source, after=after)
                        await ctx.send(embed=now_playing_embed(resolved, ctx.guild.id))
                return

            # ---- Deezer track ----
            if is_deezer_track(query):
                dz_data = await asyncio.get_event_loop().run_in_executor(None, lambda: deezer_track(query))
                if not dz_data:
                    embed = discord.Embed(description="❌ Couldn't find that Deezer track.", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                audio_data = await fetch_audio(dz_data["query"], bot.loop)
                if not audio_data:
                    embed = discord.Embed(description="❌ Couldn't find audio on YouTube for this track.", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                entry = {**dz_data, "audio_url": audio_data["url"], "yt_url": audio_data["webpage"], "pending": False}
                queue = get_queue(ctx.guild.id)
                queue.append(entry)

                if not vc.is_playing() and not vc.is_paused():
                    source = discord.FFmpegPCMAudio(entry["audio_url"], **FFMPEG_OPTIONS)
                    source = discord.PCMVolumeTransformer(source, volume=0.5)
                    def after(error):
                        if error: print(f"⚠️ Playback error: {error}")
                        play_next(ctx)
                    vc.play(source, after=after)
                    await ctx.send(embed=now_playing_embed(entry, ctx.guild.id))
                else:
                    embed = discord.Embed(
                        title       = f"➕ Added to Queue — #{len(queue)}",
                        description = f"**{entry['title']}**\nby {entry['artist']}",
                        color       = discord.Color.blurple()
                    )
                    if entry.get("art"):
                        embed.set_thumbnail(url=entry["art"])
                    embed.add_field(name="Duration", value=format_duration(entry["duration"]), inline=True)
                    embed.add_field(name="Deezer",   value=f"[Open]({entry['deezer']})",       inline=True)
                    await ctx.send(embed=embed)
                return

            # ---- Single song (search or YouTube URL) ----
            spotify_data = await asyncio.get_event_loop().run_in_executor(None, lambda: spotify_track(query))
            search_query = spotify_data["query"] if spotify_data else query
            audio_data   = await fetch_audio(search_query, bot.loop)

            if not audio_data:
                embed = discord.Embed(description="❌ Couldn't find that song. Try a different search! 🎵", color=discord.Color.red())
                await ctx.send(embed=embed)
                return

            entry = {
                "title":     spotify_data["title"]    if spotify_data else audio_data["title"],
                "artist":    spotify_data["artist"]   if spotify_data else "Unknown",
                "album":     spotify_data["album"]    if spotify_data else None,
                "art":       spotify_data["art"]      if spotify_data else None,
                "spotify":   spotify_data["spotify"]  if spotify_data else None,
                "deezer":    None,
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
                    if error: print(f"⚠️ Playback error: {error}")
                    play_next(ctx)
                vc.play(source, after=after)
                await ctx.send(embed=now_playing_embed(entry, ctx.guild.id))
            else:
                embed = discord.Embed(
                    title       = f"➕ Added to Queue — #{len(queue)}",
                    description = f"**{entry['title']}**\nby {entry['artist']}",
                    color       = discord.Color.blurple()
                )
                if entry.get("art"):
                    embed.set_thumbnail(url=entry["art"])
                embed.add_field(name="Duration", value=format_duration(entry["duration"]), inline=True)
                if entry.get("spotify"):
                    embed.add_field(name="Spotify", value=f"[Open]({entry['spotify']})", inline=True)
                await ctx.send(embed=embed)

    @bot.command(name="skip", aliases=["s"])
    async def skip(ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            embed = discord.Embed(description="⚠️ Nothing is playing right now.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return
        vc.stop()
        embed = discord.Embed(description="⏭️ Skipped!", color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @bot.command(name="pause")
    async def pause(ctx):
        vc = ctx.voice_client
        if vc and vc.is_playing():
            vc.pause()
            embed = discord.Embed(description="⏸️ Paused.", color=discord.Color.orange())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="⚠️ Nothing is playing right now.", color=discord.Color.orange())
            await ctx.send(embed=embed)

    @bot.command(name="resume")
    async def resume(ctx):
        vc = ctx.voice_client
        if vc and vc.is_paused():
            vc.resume()
            embed = discord.Embed(description="▶️ Resumed!", color=discord.Color.green())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="⚠️ Nothing is paused right now.", color=discord.Color.orange())
            await ctx.send(embed=embed)

    @bot.command(name="queue", aliases=["q"])
    async def queue_cmd(ctx):
        queue = get_queue(ctx.guild.id)
        if not queue:
            embed = discord.Embed(description="📋 The queue is empty! Use `t!play <song>` to add something.", color=discord.Color.greyple())
            await ctx.send(embed=embed)
            return

        per_page    = 10
        total_pages = (len(queue) + per_page - 1) // per_page

        def build_embed(page: int) -> discord.Embed:
            start = page * per_page
            end   = start + per_page
            lines = []
            for i, e in enumerate(queue[start:end], start=start):
                prefix = "▶️" if i == 0 else f"`{i+1}.`"
                lines.append(f"{prefix} **{e['title']}** by {e['artist']} — {format_duration(e['duration'])}")

            loop_status = ""
            if is_looping_song(ctx.guild.id):
                loop_status = " 🔂"
            elif is_looping_queue(ctx.guild.id):
                loop_status = " 🔁"

            embed = discord.Embed(
                title       = f"🎵 Queue — {len(queue)} song(s){loop_status}",
                description = "\n".join(lines),
                color       = discord.Color.blurple()
            )
            embed.set_footer(text=f"Page {page + 1} of {total_pages}")
            return embed

        class QueueView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.page = 0
                self.update_buttons()

            def update_buttons(self):
                self.prev_btn.disabled = self.page == 0
                self.next_btn.disabled = self.page >= total_pages - 1

            @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
            async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the person who ran the command can flip pages!", ephemeral=True)
                    return
                self.page -= 1
                self.update_buttons()
                await interaction.response.edit_message(embed=build_embed(self.page), view=self)

            @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
            async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the person who ran the command can flip pages!", ephemeral=True)
                    return
                self.page += 1
                self.update_buttons()
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

    @bot.command(name="clearqueue", aliases=["cq"])
    async def clearqueue(ctx):
        queue = get_queue(ctx.guild.id)
        if not queue:
            embed = discord.Embed(description="📋 The queue is already empty!", color=discord.Color.greyple())
            await ctx.send(embed=embed)
            return
        current = queue[0] if queue else None
        queue.clear()
        if current and ctx.voice_client and ctx.voice_client.is_playing():
            queue.append(current)
            embed = discord.Embed(description=f"🗑️ Queue cleared! Still playing: **{current['title']}**", color=discord.Color.blurple())
        else:
            embed = discord.Embed(description="🗑️ Queue cleared!", color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @bot.command(name="loop", aliases=["l"])
    async def loop(ctx, mode: str = None):
        guild_id = ctx.guild.id
        if mode is None:
            song_on  = is_looping_song(guild_id)
            queue_on = is_looping_queue(guild_id)
            status   = "🔂 Song loop" if song_on else ("🔁 Queue loop" if queue_on else "➡️ No loop")
            embed    = discord.Embed(
                description = f"Current loop mode: **{status}**\nUse `t!loop song`, `t!loop queue`, or `t!loop off`.",
                color       = discord.Color.blurple()
            )
            await ctx.send(embed=embed)
            return
        mode = mode.lower()
        if mode == "song":
            loop_song[guild_id]  = True
            loop_queue[guild_id] = False
            embed = discord.Embed(description="🔂 Song loop **ON** — current song will repeat.", color=discord.Color.blurple())
        elif mode == "queue":
            loop_song[guild_id]  = False
            loop_queue[guild_id] = True
            embed = discord.Embed(description="🔁 Queue loop **ON** — queue will repeat when finished.", color=discord.Color.blurple())
        elif mode == "off":
            loop_song[guild_id]  = False
            loop_queue[guild_id] = False
            embed = discord.Embed(description="➡️ Loop **OFF**.", color=discord.Color.greyple())
        else:
            embed = discord.Embed(description="⚠️ Invalid mode. Use `t!loop song`, `t!loop queue`, or `t!loop off`.", color=discord.Color.red())
        await ctx.send(embed=embed)

    @bot.command(name="shuffle", aliases=["sh"])
    async def shuffle(ctx):
        queue = get_queue(ctx.guild.id)
        if len(queue) < 3:
            embed = discord.Embed(description="⚠️ Need at least 3 songs in the queue to shuffle.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return
        current = queue[0]
        rest    = queue[1:]
        random.shuffle(rest)
        queue.clear()
        queue.append(current)
        queue.extend(rest)
        embed = discord.Embed(
            title       = "🔀 Queue Shuffled!",
            description = f"**{len(rest)}** songs rearranged.\nCurrently playing: **{current['title']}**",
            color       = discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @bot.command(name="stop")
    async def stop(ctx):
        vc = ctx.voice_client
        if vc:
            guild_id             = ctx.guild.id
            get_queue(guild_id).clear()
            loop_song[guild_id]  = False
            loop_queue[guild_id] = False
            await vc.disconnect()
            embed = discord.Embed(description="⏹️ Stopped and disconnected. See ya! 👋", color=discord.Color.red())
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="⚠️ I'm not in a voice channel.", color=discord.Color.orange())
            await ctx.send(embed=embed)

    @bot.command(name="volume", aliases=["vol"])
    async def volume(ctx, vol: int):
        vc = ctx.voice_client
        if not vc or not vc.source:
            embed = discord.Embed(description="⚠️ Nothing is playing right now.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return
        if not 1 <= vol <= 100:
            embed = discord.Embed(description="⚠️ Volume must be between 1 and 100.", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        vc.source.volume = vol / 100
        embed = discord.Embed(description=f"🔊 Volume set to **{vol}%**", color=discord.Color.blurple())
        await ctx.send(embed=embed)

    @bot.command(name="nowplaying", aliases=["np", "current", "playing"])
    async def nowplaying(ctx):
        vc    = ctx.voice_client
        queue = get_queue(ctx.guild.id)
        if not vc or (not vc.is_playing() and not vc.is_paused()) or not queue:
            embed = discord.Embed(description="⚠️ Nothing is playing right now.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return
        entry = queue[0]
        embed = now_playing_embed(entry, ctx.guild.id)
        if vc.is_paused():
            embed.title = "⏸️ Currently Paused"
        up_next = queue[1] if len(queue) > 1 else None
        if up_next:
            embed.add_field(name="Up Next", value=f"**{up_next['title']}** by {up_next['artist']}", inline=False)
        await ctx.send(embed=embed)