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


async def _send_board(
    bot: commands.Bot,
    channel: discord.TextChannel,
    author: discord.abc.User,
    session,
    send_func,
):
    from bot.minigames import extract_board_snapshot, _BOARD_RE, _TTT_RE, _BSHIP_RE
    pattern = {"chess": _BOARD_RE, "tictactoe": _TTT_RE, "battleship": _BSHIP_RE}.get(session.kind)
    if pattern is None:
        await send_func("❓ Unknown game type.")
        return
    board_embed = None
    async for msg in channel.history(limit=40):
        if msg.author == bot.user and pattern.search(msg.content):
            _, board_embed = extract_board_snapshot(msg.content, session.kind)
            if board_embed:
                break
    if board_embed is None:
        await send_func(embed=discord.Embed(
            description="⚠️ No board snapshot found yet. Make a move first!",
            color=discord.Color.orange()
        ))
        return
    board_embed.set_footer(text=f"t!board — {session.kind.title()} • {author.display_name}")
    await send_func(embed=board_embed)


def _make_interaction_prefix(action: str):
    async def callback(ctx, target: discord.Member):
        await _run_interaction(ctx, target, action)
    return callback


def _make_interaction_slash(action: str, desc: str):
    async def callback(interaction: discord.Interaction, target: discord.Member):
        await _run_interaction_slash(interaction, target, action)
    return discord.app_commands.Command(callback=callback, name=action, description=desc)


class InteractionsCog(commands.Cog, name="Interactions"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
        await _send_board(self.bot, interaction.channel, interaction.user, session, interaction.response.send_message)

    @commands.command(name="tor")
    async def tor(self, ctx, action: str, target: discord.Member):
        await _run_interaction(ctx, target, action.lower())

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
        await _send_board(self.bot, ctx.channel, ctx.author, session, ctx.send)


async def setup(bot: commands.Bot):
    cog = InteractionsCog(bot)
    await bot.add_cog(cog)
    for action in _INTERACTION_ACTIONS:
        bot.add_command(commands.Command(_make_interaction_prefix(action), name=action))
        bot.tree.add_command(_make_interaction_slash(action, f"{action.title()} someone with a GIF!"))
    bot.tree.add_command(cog.board_slash)
