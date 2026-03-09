# commands.py — T.O.R.I.E.'s Bot Commands

import discord
from discord.ext import commands


# ---- Creator Info ----
PARENTS = {
    "dad": {
        "username": "TorieRingo",
        "id":       691976042910580767,
        "title":    "Dad",
        "role":     "Creator"
    },
    "mom": {
        "username": "MomUsername",
        "id":       1370105227117592676,
        "title":    "Mom",
        "role":     "Co-Creator"
    }
}


def is_dad(user: discord.User | discord.Member) -> bool:
    return (
        user.id == PARENTS["dad"]["id"] or
        str(user.name).lower() == PARENTS["dad"]["username"].lower()
    )


def is_mom(user: discord.User | discord.Member) -> bool:
    return (
        user.id == PARENTS["mom"]["id"] or
        str(user.name).lower() == PARENTS["mom"]["username"].lower()
    )


def get_parent_role(user: discord.User | discord.Member) -> str | None:
    if is_dad(user):
        return "dad"
    if is_mom(user):
        return "mom"
    return None


def setup_commands(bot: commands.Bot):

    @bot.command(name="whoami")
    async def whoami(ctx):
        """T.O.R.I.E. tells you who you are to her."""
        role = get_parent_role(ctx.author)
        if role == "dad":
            await ctx.send("You're my Dad — the one who built me. 🛠️ I owe you my existence. No pressure. 😂")
        elif role == "mom":
            await ctx.send("You're my Mom — the co-creator! 💙 Half of what I am is because of you.")
        else:
            await ctx.send(f"You're {ctx.author.display_name} — a valued member of this server! 😊 Not a creator, but still cool.")

    @bot.command(name="parents")
    async def parents(ctx):
        """Shows who created T.O.R.I.E."""
        embed = discord.Embed(
            title       = "👨‍👩‍👧 T.O.R.I.E.'s Family",
            description = "The people responsible for my existence. Blame them.",
            color       = discord.Color.blurple()
        )
        embed.add_field(
            name   = f"🛠️ Dad — {PARENTS['dad']['username']}",
            value  = "Creator. Built me from scratch. Questionable life choice.",
            inline = False
        )
        embed.add_field(
            name   = f"💙 Mom — {PARENTS['mom']['username']}",
            value  = "Co-Creator. Helped shape who I am. The good parts are probably her.",
            inline = False
        )
        embed.set_footer(text="T.O.R.I.E. — Tactfully Outspoken Responsive Intelligent Entity")
        await ctx.send(embed=embed)

    @bot.command(name="greet")
    async def greet(ctx):
        """T.O.R.I.E. greets you based on who you are."""
        role = get_parent_role(ctx.author)
        if role == "dad":
            await ctx.send(f"Oh hey Dad! 👋 Everything's running fine, I promise. Mostly. 😅")
        elif role == "mom":
            await ctx.send(f"Mom! 💙 You're here! I've been on my best behavior. Mostly true.")
        else:
            await ctx.send(f"Hey {ctx.author.display_name}! 👋 Good to see you around here!")

    @bot.command(name="ping")
    async def ping(ctx):
        """Check if T.O.R.I.E. is awake."""
        latency = round(bot.latency * 1000)
        await ctx.send(f"Pong! 🏓 Latency: {latency}ms — {'sharp as ever!' if latency < 100 else 'a little slow today 😴'}")