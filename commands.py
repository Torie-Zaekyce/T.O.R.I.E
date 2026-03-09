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
        "username": "Nen",
        "id":       1370105227117592676,
        "title":    "Mom",
        "role":     "Co-Creator"
    }
}

COUSIN = {
    "cousin_stelle": {
        "username": "Stelle",
        "id":       993375226664591390,
        "title":    "Starry Cousin",
        "role":     "Purple Star"
    },
    
    "cousin_crois": {
        "username": "Crois",
        "id":       1276054519561846840,
        "title":    "Bread Cousin",
        "role":     "Croissant"
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

def is_cousin_stelle(user: discord.User | discord.Member) -> bool:
    return (
        user.id == COUSIN["cousin_stelle"]["id"] or
        str(user.name).lower() == COUSIN["cousin_stelle"]["username"].lower()
    )

def is_cousin_crois(user: discord.User | discord.Member) -> bool:
    return (
        user.id == COUSIN["cousin_crois"]["id"] or
        str(user.name).lower() == COUSIN["cousin_crois"]["username"].lower()
    )


def get_parent_role(user: discord.User | discord.Member) -> str | None:
    if is_dad(user):
        return "dad"
    if is_mom(user):
        return "mom"
    return None
    
def get_cousin_role(user: discord.User | discord.Member) -> str | None:
    if is_cousin_stelle(user):
        return "cousin_stelle"
    if is_cousin_crois(user):
        return "cousin_crois"
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
        elif role == "cousin_stelle":
            await ctx.send("You're my Cousin! 🌟 A Purple Star where everything is bubbly when I'm with you. 🎆")
        elif role == "cousin_crois":
            await ctx.send("You're my Cousin! 🥐 A bread where everything is bubbly when I'm with you. 🥐")
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
        embed.add_field(
            name   = f"💙 Cousin — {COUSIN['cousin_stelle']['username']}",
            value  = "Starry Cousin. The one and only purple star.",
            inline = False
        )
        embed.add_field(
            name   = f"💙 Cousin — {COUSIN['cousin_crois']['username']}",
            value  = "Croissant Cousin. The one and only Kwaso.",
            inline = False
        )
        embed.set_footer(text="T.O.R.I.E. — Thoughtful Online Response Intelligence Entity")
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