import asyncio

import discord
from discord.ext import commands

from bot.tts import generate_tts, cleanup_tts_file, DEFAULT_VOICE


class VoiceCog(commands.Cog, name="Voice"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # One speech queue per guild so messages play in order, not on top of each other
        self._queues: dict[int, asyncio.Queue] = {}
        self._workers: dict[int, asyncio.Task] = {}

    def _get_queue(self, guild_id: int) -> asyncio.Queue:
        if guild_id not in self._queues:
            self._queues[guild_id] = asyncio.Queue()
            self._workers[guild_id] = asyncio.create_task(self._queue_worker(guild_id))
        return self._queues[guild_id]

    async def _queue_worker(self, guild_id: int):
        queue = self._queues[guild_id]
        while True:
            voice_client, path = await queue.get()
            try:
                if voice_client and voice_client.is_connected():
                    done = asyncio.Event()

                    def _after_play(error):
                        if error:
                            print(f"⚠️ Voice playback error: {error}")
                        done.set()

                    voice_client.play(discord.FFmpegPCMAudio(path), after=_after_play)
                    await done.wait()
            except Exception as e:
                print(f"⚠️ TTS playback failed: {type(e).__name__}: {e}")
            finally:
                cleanup_tts_file(path)
                queue.task_done()

    @commands.command(name="join")
    async def join(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(embed=discord.Embed(
                description="⚠️ You need to be in a voice channel first!",
                color=discord.Color.orange()
            ))
            return

        channel = ctx.author.voice.channel
        if ctx.voice_client:
            if ctx.voice_client.channel == channel:
                await ctx.send(embed=discord.Embed(description=f"🔊 I'm already in {channel.mention}.", color=discord.Color.blurple()))
                return
            await ctx.voice_client.move_to(channel)
        else:
            try:
                await channel.connect()
            except discord.ClientException:
                await ctx.send(embed=discord.Embed(description="⚠️ Already connecting/connected here.", color=discord.Color.orange()))
                return
            except asyncio.TimeoutError:
                await ctx.send(embed=discord.Embed(description="⛔ Couldn't connect — timed out.", color=discord.Color.red()))
                return

        await ctx.send(embed=discord.Embed(description=f"🔊 Joined {channel.mention}!", color=discord.Color.green()))

    @commands.command(name="leave")
    async def leave(self, ctx):
        if not ctx.voice_client:
            await ctx.send(embed=discord.Embed(description="⚠️ I'm not in a voice channel.", color=discord.Color.orange()))
            return
        await ctx.voice_client.disconnect()
        await ctx.send(embed=discord.Embed(description="👋 Left the voice channel.", color=discord.Color.green()))

    @commands.command(name="say")
    async def say(self, ctx, *, text: str = None):
        if not text:
            await ctx.send(embed=discord.Embed(
                description="⚠️ Usage: `t!say <text>` (must be in a voice channel, or use `t!join` first)",
                color=discord.Color.orange()
            ))
            return

        voice_client = ctx.voice_client
        if not voice_client:
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.send(embed=discord.Embed(
                    description="⚠️ I'm not in a voice channel, and neither are you. Join one first!",
                    color=discord.Color.orange()
                ))
                return
            try:
                voice_client = await ctx.author.voice.channel.connect()
            except Exception as e:
                await ctx.send(embed=discord.Embed(description=f"⛔ Couldn't join voice channel: {e}", color=discord.Color.red()))
                return

        async with ctx.typing():
            path = await generate_tts(text, voice=DEFAULT_VOICE)

        if not path:
            await ctx.send(embed=discord.Embed(description="❌ TTS generation failed. Try again?", color=discord.Color.red()))
            return

        queue = self._get_queue(ctx.guild.id)
        await queue.put((voice_client, path))

    async def cog_unload(self):
        for task in self._workers.values():
            task.cancel()


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCog(bot))
