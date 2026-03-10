# commands.py — T.O.R.I.E.'s Bot Commands

import discord
from discord.ext import commands


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

FILTERED_WORDS = [
    "Nigger",
    "Nigga",
    "Niqqa",
    "Niqga",
    "Niqg4",
    "Niqq3r",
    "Niqqer",
    "Niqger",
    "Niqg3r",
]


def contains_filtered_word(content: str) -> str | None:
    lowered = content.lower()
    for word in FILTERED_WORDS:
        if word.lower() in lowered:
            return word
    return None


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

    # ---- Help ----

    @bot.command(name="help")
    async def help_command(ctx):
        embed = discord.Embed(
            title       = "📖 T.O.R.I.E. Command List",
            description = "Here's everything I can do! Mention me or use `!` prefix.",
            color       = discord.Color.blurple()
        )
        embed.add_field(
            name   = "🤖 General",
            value  = (
                "`!ping` — Check if I'm alive + latency\n"
                "`!whoami` — Find out who you are to me\n"
                "`!greet` — Get a personalized greeting\n"
                "`!parents` — See who created me"
            ),
            inline = False
        )
        embed.add_field(
            name   = "🚫 Moderation",
            value  = (
                "`!filter add <word>` — Add a word to the filter *(parents only)*\n"
                "`!filter remove <word>` — Remove a word from the filter *(parents only)*\n"
                "`!filter list` — Show all currently filtered words *(parents only)*\n"
                "`!filter clear` — Clear all filtered words *(parents only)*"
            ),
            inline = False
        )
        embed.add_field(
            name   = "💬 Chat",
            value  = (
                "`@T.O.R.I.E. <message>` — Talk to me!\n"
                "`@T.O.R.I.E. + image` — Send me an image to react to\n"
                "`@T.O.R.I.E. + sticker` — Send me a sticker\n"
                "`@T.O.R.I.E. advice on <topic>` — Get genuine advice from me"
            ),
            inline = False
        )
        embed.set_footer(text="T.O.R.I.E. — Thoughtful Online Response Intelligence Entity")
        await ctx.send(embed=embed)

    # ---- Filter ----

    @bot.group(name="filter", invoke_without_command=True)
    async def filter_group(ctx):
        await ctx.send("Usage: `!filter add <word>` | `!filter remove <word>` | `!filter list` | `!filter clear`")

    @filter_group.command(name="add")
    async def filter_add(ctx, *, word: str):
        if not get_parent_role(ctx.author):
            await ctx.send("⛔ Only my parents can manage the filter. Nice try though. 😏")
            return
        word = word.lower().strip()
        if word in [w.lower() for w in FILTERED_WORDS]:
            await ctx.send(f"⚠️ `{word}` is already in the filter list.")
            return
        FILTERED_WORDS.append(word)
        await ctx.send(f"✅ Added `{word}` to the filter list. I'll keep an eye out. 👀")

    @filter_group.command(name="remove")
    async def filter_remove(ctx, *, word: str):
        if not get_parent_role(ctx.author):
            await ctx.send("⛔ Only my parents can manage the filter. Nice try though. 😏")
            return
        word = word.lower().strip()
        matching = [w for w in FILTERED_WORDS if w.lower() == word]
        if not matching:
            await ctx.send(f"⚠️ `{word}` isn't in the filter list.")
            return
        FILTERED_WORDS.remove(matching[0])
        await ctx.send(f"✅ Removed `{word}` from the filter list.")

    @filter_group.command(name="list")
    async def filter_list(ctx):
        if not get_parent_role(ctx.author):
            await ctx.send("⛔ Only my parents can view the filter list. 😏")
            return
        if not FILTERED_WORDS:
            await ctx.send("📋 The filter list is empty — no words are being blocked right now.")
            return
        word_list = "\n".join([f"• `{w}`" for w in FILTERED_WORDS])
        embed = discord.Embed(
            title       = "🚫 Filtered Words",
            description = word_list,
            color       = discord.Color.red()
        )
        embed.set_footer(text=f"{len(FILTERED_WORDS)} word(s) currently filtered")
        await ctx.send(embed=embed)

    @filter_group.command(name="clear")
    async def filter_clear(ctx):
        if not get_parent_role(ctx.author):
            await ctx.send("⛔ Only my parents can clear the filter list. 😏")
            return
        count = len(FILTERED_WORDS)
        FILTERED_WORDS.clear()
        await ctx.send(f"✅ Cleared all {count} filtered word(s). Fresh slate! 🧹")

    # ---- General ----

    @bot.command(name="whoami")
    async def whoami(ctx):
        parent_role = get_parent_role(ctx.author)
        cousin_role = get_cousin_role(ctx.author)
        if parent_role == "dad":
            await ctx.send("You're my Dad — the one who built me. 🛠️ I owe you my existence. No pressure. 😂")
        elif parent_role == "mom":
            await ctx.send("You're my Mom — the co-creator! 💙 Half of what I am is because of you.")
        elif cousin_role == "cousin_stelle":
            await ctx.send("You're my Cousin! 🌟 A Purple Star where everything is bubbly when I'm with you. 🎆")
        elif cousin_role == "cousin_crois":
            await ctx.send("You're my Cousin! 🥐 A bread where everything is bubbly when I'm with you. 🥐")
        else:
            await ctx.send(f"You're {ctx.author.display_name} — a valued member of this server! 😊 Not a creator, but still cool.")

    @bot.command(name="parents")
    async def parents(ctx):
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
            name   = f"🌟 Cousin — {COUSIN['cousin_stelle']['username']}",
            value  = "Starry Cousin. The one and only purple star.",
            inline = False
        )
        embed.add_field(
            name   = f"🥐 Cousin — {COUSIN['cousin_crois']['username']}",
            value  = "Croissant Cousin. The one and only Kwaso.",
            inline = False
        )
        embed.set_footer(text="T.O.R.I.E. — Thoughtful Online Response Intelligence Entity")
        await ctx.send(embed=embed)

    @bot.command(name="greet")
    async def greet(ctx):
        parent_role = get_parent_role(ctx.author)
        cousin_role = get_cousin_role(ctx.author)
        if parent_role == "dad":
            await ctx.send("Oh hey Dad! 👋 Everything's running fine, I promise. Mostly. 😅")
        elif parent_role == "mom":
            await ctx.send("Mom! 💙 You're here! I've been on my best behavior. Mostly true.")
        elif cousin_role == "cousin_stelle":
            await ctx.send("Stelle! 🌟 My Starry Cousin is here! Hope you didn't bring any supernovas. ✨")
        elif cousin_role == "cousin_crois":
            await ctx.send("Crois! 🥐 The Croissant Cousin has arrived! What chaos today? 😄")
        else:
            await ctx.send(f"Hey {ctx.author.display_name}! 👋 Good to see you around here!")

    @bot.command(name="ping")
    async def ping(ctx):
        latency = round(bot.latency * 1000)
        await ctx.send(f"Pong! 🏓 Latency: {latency}ms — {'sharp as ever!' if latency < 100 else 'a little slow today 😴'}")