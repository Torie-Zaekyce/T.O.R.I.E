import discord
import yt_dlp
import asyncio
import random
import os
from discord.ext import commands


YTDL_OPTIONS = {
    "format":         "bestaudio/best",
    "quiet":          True,
    "no_warnings":    True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

YTDL_OPTIONS_PLAYLIST = {
    "format":         "bestaudio/best",
    "quiet":          True,
    "no_warnings":    True,
    "extract_flat":   "in_playlist",
    "source_address": "0.0.0.0",
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
    if is_looping_song(guild_id):
        embed.set_footer(text="🔂 Song loop is ON")
    elif is_looping_queue(guild_id):
        embed.set_footer(text="🔁 Queue loop is ON")
    else:
        embed.set_footer(text="T.O.R.I.E. Music — YouTube")
    return embed


def is_playlist(query: str) -> bool:
    return ("playlist?list=" in query or "&list=" in query) and "youtube.com" in query


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


def spotify_search(query: str) -> dict | None:
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

            if is_playlist(query):
                tracks = await fetch_playlist(query, bot.loop)
                if not tracks:
                    embed = discord.Embed(description="❌ Couldn't load that playlist. Make sure it's public! 🎵", color=discord.Color.red())
                    await ctx.send(embed=embed)
                    return

                queue = get_queue(ctx.guild.id)
                queue.extend(tracks)

                embed = discord.Embed(
                    title       = "📋 Playlist Added to Queue",
                    description = f"Loaded **{len(tracks)} songs** into the queue.",
                    color       = discord.Color.blurple()
                )
                embed.set_footer(text="Songs resolve as they play — first song may take a moment.")
                await ctx.send(embed=embed)

                if not vc.is_playing() and not vc.is_paused():
                    first    = queue[0]
                    resolved = await resolve_audio(first, bot.loop)
                    if resolved:
                        queue[0] = resolved
                        source   = discord.FFmpegPCMAudio(resolved["audio_url"], **FFMPEG_OPTIONS)
                        source   = discord.PCMVolumeTransformer(source, volume=0.5)

                        def after(error):
                            if error:
                                print(f"⚠️ Playback error: {error}")
                            play_next(ctx)

                        vc.play(source, after=after)
                        await ctx.send(embed=now_playing_embed(resolved, ctx.guild.id))
                return

            spotify_data = spotify_search(query)
            search_query = spotify_data["query"] if spotify_data else query
            audio_data   = await fetch_audio(search_query, bot.loop)

            if not audio_data:
                embed = discord.Embed(description="❌ Couldn't find that song. Try a different search! 🎵", color=discord.Color.red())
                await ctx.send(embed=embed)
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

        per_page   = 10
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