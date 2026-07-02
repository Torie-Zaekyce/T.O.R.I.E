# cogs/interactions.py — GIF interactions (hug, kiss, pat, …) + t!board

import os
import random

import aiohttp
import discord
from discord.ext import commands

_INTERACTION_ACTIONS: dict[str, tuple[str, str]] = {
    "hug":   ("*gives {target} a warm hug! 🤗*",              "anime hug cute"),
    "kiss":  ("*gives {target} a little kiss! 💋*",           "anime kiss cute"),
    "pat":   ("*pats {target} on the head! 🥺*",              "anime head pat cute"),
    "bite":  ("*playfully bites {target}! 😈*",               "anime bite cute"),
    "lick":  ("*licks {target} like a weirdo! 👅*",           "anime lick cute"),
    "punch": ("*punches {target} straight in the face! 👊*",  "anime punch"),
    "kick":  ("*kicks {target} into next week! 🦵*",          "anime kick"),
    "fuck":  ("*holds {target}'s hand! 🥺👉👈*",              "anime holding hands"),
}


async def _search_klipy_gif(query: str) -> str | None:
    KLIPY_API_KEY = os.getenv("KLIPY_API_KEY")
    if not KLIPY_API_KEY:
        print("⚠️ KLIPY_API_KEY not set — GIF search disabled")
        return None
    try:
        url = f"https://api.klipy.com/api/v1/{KLIPY_API_KEY}/gifs/search"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"q": query, "limit": 25}) as resp:
                if resp.status != 200:
                    print(f"⚠️ Klipy GIF search returned HTTP {resp.status}")
                    return None
                data    = await resp.json()
                results = data.get("data", {}).get("data", [])
                if not results:
                    return None
                random.shuffle(results)
                for item in results:
                    try:
                        gif_url = (
                            item["file"]["hd"]["gif"]["url"]
                            if "file" in item
                            else item["media"]["gif"]["url"]
                        )
                        if gif_url:
                            return gif_url
                    except (KeyError, TypeError):
                        continue
                return None
    except Exception as e:
        print(f"⚠️ Klipy GIF search error: {type(e).__name__}: {e}")
        return None


async def _run_interaction(ctx, target: discord.Member, action: str):
    if action not in _INTERACTION_ACTIONS:
        await ctx.send(embed=discord.Embed(
            description=f"⚠️ Unknown action `{action}`. Valid: `{'` `'.join(_INTERACTION_ACTIONS.keys())}`",
            color=discord.Color.orange()
        ))
        return
    text_template, query = _INTERACTION_ACTIONS[action]
    gif_url = await _search_klipy_gif(query)
    text    = text_template.format(target=target.mention)
    embed   = discord.Embed(description=text, color=discord.Color.pink())
    if gif_url:
        embed.set_image(url=gif_url)
    embed.set_footer(text="T.O.R.I.E. GIFs Powered by KLIPY GIF")
    await ctx.send(embed=embed)


async def _run_interaction_slash(interaction: discord.Interaction, target: discord.Member, action: str):
    if action not in _INTERACTION_ACTIONS:
        await interaction.response.send_message(f"⚠️ Unknown action `{action}`.", ephemeral=True)
        return
    text_template, query = _INTERACTION_ACTIONS[action]
    gif_url = await _search_klipy_gif(query)
    text    = text_template.format(target=target.mention)
    embed   = discord.Embed(description=text, color=discord.Color.pink())
    if gif_url:
        embed.set_image(url=gif_url)
    embed.set_footer(text="T.O.R.I.E. GIFs Powered by KLIPY GIF")
    await interaction.response.send_message(embed=embed)


class InteractionsCog(commands.Cog, name="Interactions"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # One command per action — keeps error messages and help clean
    # ── Slash: GIF interactions ──────────────────────────────────────────────

    @discord.app_commands.command(name="hug", description="Hug someone with a GIF!")
    @discord.app_commands.describe(target="Who to hug")
    async def hug_slash(self, interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, "hug")

    @discord.app_commands.command(name="kiss", description="Kiss someone with a GIF!")
    @discord.app_commands.describe(target="Who to kiss")
    async def kiss_slash(self, interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, "kiss")

    @discord.app_commands.command(name="pat", description="Pat someone with a GIF!")
    @discord.app_commands.describe(target="Who to pat")
    async def pat_slash(self, interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, "pat")

    @discord.app_commands.command(name="bite", description="Bite someone with a GIF!")
    @discord.app_commands.describe(target="Who to bite")
    async def bite_slash(self, interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, "bite")

    @discord.app_commands.command(name="lick", description="Lick someone with a GIF!")
    @discord.app_commands.describe(target="Who to lick")
    async def lick_slash(self, interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, "lick")

    @discord.app_commands.command(name="punch", description="Punch someone with a GIF!")
    @discord.app_commands.describe(target="Who to punch")
    async def punch_slash(self, interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, "punch")

    @discord.app_commands.command(name="kick", description="Kick someone with a GIF!")
    @discord.app_commands.describe(target="Who to kick")
    async def kick_slash(self, interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, "kick")

    @discord.app_commands.command(name="fuck", description="Hold hands with someone! ( ͡° ͜ʖ ͡°)")
    @discord.app_commands.describe(target="Who to hold hands with")
    async def fuck_slash(self, interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, "fuck")

    @discord.app_commands.command(name="board", description="Show the current minigame board")
    async def board_slash(self, interaction: discord.Interaction):
        from bot.minigames import get_session, extract_board_snapshot, _BOARD_RE, _TTT_RE, _BSHIP_RE
        session = get_session(interaction.channel_id, interaction.user.id)
        if session is None:
            await interaction.response.send_message(embed=discord.Embed(
                description="❌ You don't have an active game session. Start one by mentioning me!",
                color=discord.Color.red()
            ))
            return
        pattern = {"chess": _BOARD_RE, "tictactoe": _TTT_RE, "battleship": _BSHIP_RE}.get(session.kind)
        if pattern is None:
            await interaction.response.send_message("❓ Unknown game type.")
            return
        board_embed = None
        async for msg in interaction.channel.history(limit=40):
            if msg.author == self.bot.user and pattern.search(msg.content):
                _, board_embed = extract_board_snapshot(msg.content, session.kind)
                if board_embed:
                    break
        if board_embed is None:
            await interaction.response.send_message(embed=discord.Embed(
                description="⚠️ No board snapshot found yet. Make a move first!",
                color=discord.Color.orange()
            ))
            return
        board_embed.set_footer(text=f"t!board — {session.kind.title()} • {interaction.user.display_name}")
        await interaction.response.send_message(embed=board_embed)

    @commands.command(name="hug")
    async def hug(self, ctx, target: discord.Member):
        await _run_interaction(ctx, target, "hug")

    @commands.command(name="kiss")
    async def kiss(self, ctx, target: discord.Member):
        await _run_interaction(ctx, target, "kiss")

    @commands.command(name="pat")
    async def pat(self, ctx, target: discord.Member):
        await _run_interaction(ctx, target, "pat")

    @commands.command(name="bite")
    async def bite(self, ctx, target: discord.Member):
        await _run_interaction(ctx, target, "bite")

    @commands.command(name="lick")
    async def lick(self, ctx, target: discord.Member):
        await _run_interaction(ctx, target, "lick")

    @commands.command(name="punch")
    async def punch(self, ctx, target: discord.Member):
        await _run_interaction(ctx, target, "punch")

    @commands.command(name="kick")
    async def kick(self, ctx, target: discord.Member):
        await _run_interaction(ctx, target, "kick")

    @commands.command(name="fuck")
    async def fuck(self, ctx, target: discord.Member):
        await _run_interaction(ctx, target, "fuck")

    @commands.command(name="tor")
    async def tor(self, ctx, action: str, target: discord.Member):
        await _run_interaction(ctx, target, action.lower())

    # -----------------------------------------------------------------------
    # t!board — show current minigame board
    # -----------------------------------------------------------------------

    @commands.command(name="board")
    async def board_cmd(self, ctx):
        from bot.minigames import get_session, extract_board_snapshot, _BOARD_RE, _TTT_RE, _BSHIP_RE
        session = get_session(ctx.channel.id, ctx.author.id)
        if session is None:
            await ctx.send(embed=discord.Embed(
                description="❌ You don't have an active game session. Start one by mentioning me!",
                color=discord.Color.red()
            ))
            return
        pattern = {"chess": _BOARD_RE, "tictactoe": _TTT_RE, "battleship": _BSHIP_RE}.get(session.kind)
        if pattern is None:
            await ctx.send("❓ Unknown game type.")
            return
        board_embed = None
        async for msg in ctx.channel.history(limit=40):
            if msg.author == self.bot.user and pattern.search(msg.content):
                _, board_embed = extract_board_snapshot(msg.content, session.kind)
                if board_embed:
                    break
        if board_embed is None:
            await ctx.send(embed=discord.Embed(
                description="⚠️ No board snapshot found yet. Make a move first!",
                color=discord.Color.orange()
            ))
            return
        board_embed.set_footer(text=f"t!board — {session.kind.title()} • {ctx.author.display_name}")
        await ctx.send(embed=board_embed)


async def setup(bot: commands.Bot):
    cog = InteractionsCog(bot)
    await bot.add_cog(cog)
    for cmd in (cog.hug_slash, cog.kiss_slash, cog.pat_slash, cog.bite_slash, cog.lick_slash,
                cog.punch_slash, cog.kick_slash, cog.fuck_slash, cog.board_slash):
        bot.tree.add_command(cmd)
