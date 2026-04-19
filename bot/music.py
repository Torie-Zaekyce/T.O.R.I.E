import discord
import wavelink
import asyncio
import random
from discord.ext import commands


DEFAULT_VOLUME = 50

queues:     dict[int, list[wavelink.Playable]] = {}
loop_song:  dict[int, bool] = {}
loop_queue: dict[int, bool] = {}


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


def format_duration(ms: int) -> str:
    secs = ms // 1000
    mins, secs = divmod(secs, 60)
    return f"{mins}:{secs:02d}"

def now_playing_embed(track: wavelink.Playable, guild_id: int) -> discord.Embed:
    embed = discord.Embed(
        title       = "🎵 Now Playing",
        description = f"**{track.title}**\nby {track.author}",
        color       = discord.Color.green()
    )
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
    if hasattr(track, "uri") and track.uri:
        embed.add_field(name="Link", value=f"[Open]({track.uri})", inline=True)
    if is_looping_song(guild_id):
        embed.set_footer(text="🔂 Song loop is ON")
    elif is_looping_queue(guild_id):
        embed.set_footer(text="🔁 Queue loop is ON")
    else:
        embed.set_footer(text="T.O.R.I.E. Music — Powered by Lavalink")
    return embed

def queued_embed(track: wavelink.Playable, position: int) -> discord.Embed:
    embed = discord.Embed(
        title       = f"➕ Added to Queue — #{position}",
        description = f"**{track.title}**\nby {track.author}",
        color       = discord.Color.blurple()
    )
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
    return embed


def setup_music(bot: commands.Bot):

    @bot.event
    async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
        print(f"✅ Lavalink node connected: {payload.node.identifier}")

    @bot.event
    async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
        player: wavelink.Player = payload.player
        if not player:
            return

        guild_id = player.guild.id
        queue    = get_queue(guild_id)
        ctx      = getattr(player, "_ctx", None)

        if not queue:
            return

        if is_looping_song(guild_id):
            track = queue[0]
            await player.play(track)
            return

        finished = queue.pop(0)
        if is_looping_queue(guild_id):
            queue.append(finished)

        if not queue:
            if ctx:
                await ctx.send(embed=discord.Embed(
                    description="✅ Queue finished! Add more songs with `t!play`.",
                    color       = discord.Color.greyple()
                ))
            return

        next_track = queue[0]
        await player.play(next_track)
        if ctx:
            await ctx.send(embed=now_playing_embed(next_track, guild_id))


    @bot.command(name="play", aliases=["p"])
    async def play(ctx: commands.Context, *, query: str):
        if not ctx.author.voice:
            await ctx.send(embed=discord.Embed(
                description="⚠️ You need to be in a voice channel first! 🎧",
                color=discord.Color.red()
            ))
            return

        player: wavelink.Player = ctx.voice_client
        if not player:
            player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        elif player.channel != ctx.author.voice.channel:
            await player.move_to(ctx.author.voice.channel)

        player._ctx = ctx
        player.autoplay = wavelink.AutoPlayMode.disabled

        async with ctx.typing():
            tracks = await wavelink.Playable.search(query)

            if not tracks:
                await ctx.send(embed=discord.Embed(
                    description="❌ No results found. Try a different search!",
                    color=discord.Color.red()
                ))
                return

            queue = get_queue(ctx.guild.id)

            if isinstance(tracks, wavelink.Playlist):
                for track in tracks:
                    queue.append(track)
                await ctx.send(embed=discord.Embed(
                    title       = "📋 Playlist Added",
                    description = f"Loaded **{len(tracks.tracks)} songs** into the queue.",
                    color       = discord.Color.blurple()
                ).set_footer(text=tracks.name or ""))
            else:
                track = tracks[0]
                queue.append(track)
                if player.playing or player.paused:
                    await ctx.send(embed=queued_embed(track, len(queue)))
                    return

            if not player.playing and not player.paused and queue:
                first = queue[0]
                await player.play(first)
                player.set_volume(DEFAULT_VOLUME)
                await ctx.send(embed=now_playing_embed(first, ctx.guild.id))


    @bot.command(name="skip", aliases=["s"])
    async def skip(ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if not player or not player.playing:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is playing.", color=discord.Color.orange()))
            return
        await player.stop()
        await ctx.send(embed=discord.Embed(description="⏭️ Skipped!", color=discord.Color.blurple()))


    @bot.command(name="pause")
    async def pause(ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if player and player.playing:
            await player.pause(True)
            await ctx.send(embed=discord.Embed(description="⏸️ Paused.", color=discord.Color.orange()))
        else:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is playing.", color=discord.Color.orange()))


    @bot.command(name="resume")
    async def resume(ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if player and player.paused:
            await player.pause(False)
            await ctx.send(embed=discord.Embed(description="▶️ Resumed!", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is paused.", color=discord.Color.orange()))


    @bot.command(name="stop")
    async def stop(ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        if player:
            clear_state(ctx.guild.id)
            await player.disconnect()
            await ctx.send(embed=discord.Embed(description="⏹️ Stopped and disconnected. See ya! 👋", color=discord.Color.red()))
        else:
            await ctx.send(embed=discord.Embed(description="⚠️ I'm not in a voice channel.", color=discord.Color.orange()))


    @bot.command(name="volume", aliases=["vol"])
    async def volume(ctx: commands.Context, vol: int):
        player: wavelink.Player = ctx.voice_client
        if not player:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is playing.", color=discord.Color.orange()))
            return
        if not 1 <= vol <= 100:
            await ctx.send(embed=discord.Embed(description="⚠️ Volume must be between 1 and 100.", color=discord.Color.red()))
            return
        await player.set_volume(vol)
        await ctx.send(embed=discord.Embed(description=f"🔊 Volume set to **{vol}%**", color=discord.Color.blurple()))


    @bot.command(name="nowplaying", aliases=["np", "current", "playing"])
    async def nowplaying(ctx: commands.Context):
        player: wavelink.Player = ctx.voice_client
        queue = get_queue(ctx.guild.id)
        if not player or (not player.playing and not player.paused) or not queue:
            await ctx.send(embed=discord.Embed(description="⚠️ Nothing is playing.", color=discord.Color.orange()))
            return
        embed = now_playing_embed(queue[0], ctx.guild.id)
        if player.paused:
            embed.title = "⏸️ Currently Paused"
        if len(queue) > 1:
            embed.add_field(name="Up Next", value=f"**{queue[1].title}** by {queue[1].author}", inline=False)
        await ctx.send(embed=embed)


    @bot.command(name="queue", aliases=["q"])
    async def queue_cmd(ctx: commands.Context):
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
                f"{'▶️' if i == 0 else f'`{i+1}.`'} **{t.title}** by {t.author} — {format_duration(t.length)}"
                for i, t in enumerate(queue[start:start + per_page], start=start)
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


    @bot.command(name="clearqueue", aliases=["cq"])
    async def clearqueue(ctx: commands.Context):
        queue = get_queue(ctx.guild.id)
        if not queue:
            await ctx.send(embed=discord.Embed(description="📋 The queue is already empty!", color=discord.Color.greyple()))
            return
        player: wavelink.Player = ctx.voice_client
        current = queue[0] if (player and player.playing) else None
        queue.clear()
        if current:
            queue.append(current)
            await ctx.send(embed=discord.Embed(
                description=f"🗑️ Queue cleared! Still playing: **{current.title}**",
                color=discord.Color.blurple()
            ))
        else:
            await ctx.send(embed=discord.Embed(description="🗑️ Queue cleared!", color=discord.Color.blurple()))


    @bot.command(name="shuffle", aliases=["sh"])
    async def shuffle(ctx: commands.Context):
        queue = get_queue(ctx.guild.id)
        if len(queue) < 3:
            await ctx.send(embed=discord.Embed(description="⚠️ Need at least 3 songs to shuffle.", color=discord.Color.orange()))
            return
        current, rest = queue[0], queue[1:]
        random.shuffle(rest)
        queue.clear()
        queue.append(current)
        queue.extend(rest)
        await ctx.send(embed=discord.Embed(
            title       = "🔀 Queue Shuffled!",
            description = f"**{len(rest)}** songs rearranged.\nCurrently playing: **{current.title}**",
            color       = discord.Color.blurple()
        ))


    @bot.command(name="loop", aliases=["l"])
    async def loop(ctx: commands.Context, mode: str = None):
        guild_id = ctx.guild.id
        if mode is None:
            status = "🔂 Song" if is_looping_song(guild_id) else ("🔁 Queue" if is_looping_queue(guild_id) else "➡️ Off")
            await ctx.send(embed=discord.Embed(
                description=f"Current loop mode: **{status}**\nUse `t!loop song`, `t!loop queue`, or `t!loop off`.",
                color=discord.Color.blurple()
            ))
            return

        mode = mode.lower()
        if mode == "song":
            loop_song[guild_id], loop_queue[guild_id] = True, False
            await ctx.send(embed=discord.Embed(description="🔂 Song loop **ON**", color=discord.Color.blurple()))
        elif mode == "queue":
            loop_song[guild_id], loop_queue[guild_id] = False, True
            await ctx.send(embed=discord.Embed(description="🔁 Queue loop **ON**", color=discord.Color.blurple()))
        elif mode == "off":
            loop_song[guild_id], loop_queue[guild_id] = False, False
            await ctx.send(embed=discord.Embed(description="➡️ Loop **OFF**", color=discord.Color.greyple()))
        else:
            await ctx.send(embed=discord.Embed(
                description="⚠️ Invalid mode. Use `t!loop song`, `t!loop queue`, or `t!loop off`.",
                color=discord.Color.red()
            ))