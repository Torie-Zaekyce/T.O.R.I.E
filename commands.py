# commands.py — T.O.R.I.E.'s Bot Commands

import discord
import re
import json
import os
from datetime import datetime
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

UNCLE = {
    "uncle_caco": {
        "username": "Cacolate",
        "id":       397563581111205892,
        "title":    "Goated Uncle",
        "role":     "Purple Star"
    },
    "uncle_vari": {
        "username": "Vari",
        "id":       1213763202173632555,
        "title":    "Baguette Uncle",
        "role":     "Teto Kasane"
    }
}

SISTER = {
    "sister_abby": {
        "username": "Abby",
        "id":       1401144000311857316,
        "title":    "AI Sister",
        "role":     "Cheesy AI"
    },
    "sister_kde": {
        "username": "Kde",
        "id":       1278625221078683670,
        "title":    "Sister",
        "role":     "KDE Plasma"
    }
}

HUSBAND  = {}
FRIENDS  = {}

FILTERED_WORDS = [
    "retard",
    "nigger",
    "nigga",
    "negro",
    "negra",
]

# ---- Persistent birthday store ----

BIRTHDAYS_FILE = "birthdays.json"

def _load_birthdays() -> dict:
    if os.path.exists(BIRTHDAYS_FILE):
        try:
            with open(BIRTHDAYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load birthdays.json: {e}")
    return {}

def _save_birthdays():
    try:
        with open(BIRTHDAYS_FILE, "w", encoding="utf-8") as f:
            json.dump(BIRTHDAYS, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Failed to save birthdays.json: {e}")

BIRTHDAYS: dict[str, dict] = _load_birthdays()

NORMALIZER = str.maketrans({
    "0": "o",  "1": "i",  "3": "e",  "4": "a",
    "5": "s",  "6": "g",  "7": "t",  "8": "b",
    "@": "a",  "$": "s",  "!": "i",  "+": "t",
    "(": "c",  ")": "o",  "*": "",   ".": "",
    "_": "",   "-": "",   " ": "",
    "а": "a",  "е": "e",  "о": "o",  "р": "p",
    "с": "c",  "х": "x",  "и": "n",  "g": "g",
    "ı": "i",  "ɪ": "i",  "ɡ": "g",  "ǝ": "e",
    "ñ": "n",  "η": "n",
})


def normalize(text: str) -> str:
    text = text.lower()
    text = text.translate(NORMALIZER)
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]', '', text)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    text = re.sub(r'[^a-z0-9]', '', text)
    return text


def contains_filtered_word(content: str) -> str | None:
    normalized = normalize(content)
    for word in FILTERED_WORDS:
        if normalize(word) in normalized:
            return word
    return None


def get_todays_birthdays() -> list[dict]:
    now   = datetime.utcnow()
    today = (now.month, now.day)
    return [
        {"name": data.get("name", key), **data}
        for key, data in BIRTHDAYS.items()
        if (data["month"], data["day"]) == today
    ]


# ---- Family check helpers ----

def is_dad(user):
    return user.id == PARENTS["dad"]["id"] or str(user.name).lower() == PARENTS["dad"]["username"].lower()

def is_mom(user):
    return user.id == PARENTS["mom"]["id"] or str(user.name).lower() == PARENTS["mom"]["username"].lower()

def is_cousin_stelle(user):
    return user.id == COUSIN["cousin_stelle"]["id"] or str(user.name).lower() == COUSIN["cousin_stelle"]["username"].lower()

def is_cousin_crois(user):
    return user.id == COUSIN["cousin_crois"]["id"] or str(user.name).lower() == COUSIN["cousin_crois"]["username"].lower()

def is_uncle_caco(user):
    return user.id == UNCLE["uncle_caco"]["id"] or str(user.name).lower() == UNCLE["uncle_caco"]["username"].lower()

def is_uncle_vari(user):
    return user.id == UNCLE["uncle_vari"]["id"] or str(user.name).lower() == UNCLE["uncle_vari"]["username"].lower()

def is_sister_abby(user):
    return user.id == SISTER["sister_abby"]["id"] or str(user.name).lower() == SISTER["sister_abby"]["username"].lower()

def is_sister_kde(user):
    return user.id == SISTER["sister_kde"]["id"] or str(user.name).lower() == SISTER["sister_kde"]["username"].lower()


# ---- Role getters ----

def get_parent_role(user) -> str | None:
    if is_dad(user):  return "dad"
    if is_mom(user):  return "mom"
    return None

def get_cousin_role(user) -> str | None:
    if is_cousin_stelle(user): return "cousin_stelle"
    if is_cousin_crois(user):  return "cousin_crois"
    return None

def get_uncle_role(user) -> str | None:
    if is_uncle_caco(user): return "uncle_caco"
    if is_uncle_vari(user): return "uncle_vari"
    return None

def get_sister_role(user) -> str | None:
    if is_sister_abby(user): return "sister_abby"
    if is_sister_kde(user):  return "sister_kde"
    return None


def setup_commands(bot: commands.Bot):

    # ---- Help ----

    @bot.command(name="help")
    async def help_command(ctx):
        embed = discord.Embed(
            title       = "📖 T.O.R.I.E. Command List",
            description = "Here's everything I can do! Mention me or use `t!` prefix.",
            color       = discord.Color.blurple()
        )
        embed.add_field(
            name   = "🤖 General",
            value  = (
                "`t!ping` — Check if I'm alive + latency\n"
                "`t!whoami` — Find out who you are to me\n"
                "`t!greet` — Get a personalized greeting\n"
                "`t!family` — See my whole family"
            ),
            inline = False
        )
        embed.add_field(
            name   = "🚫 Moderation",
            value  = (
                "`t!filter add <word>` — Add a word to the filter *(parents only)*\n"
                "`t!filter remove <word>` — Remove a word from the filter *(parents only)*\n"
                "`t!filter list` — Show all currently filtered words *(parents only)*\n"
                "`t!filter clear` — Clear all filtered words *(parents only)*"
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
        embed.add_field(
            name   = "🎂 Birthdays",
            value  = (
                "`t!birthday add <MM-DD>` — Register your own birthday 🎉\n"
                "`t!birthday remove` — Remove your registered birthday\n"
                "`t!birthday list` — See everyone's birthdays\n"
                "`t!birthday today` — Check who's celebrating today!"
            ),
            inline = False
        )
        embed.add_field(
            name   = "🧠 Personality",
            value  = (
                "`t!personality add <trait>` — Add a personality trait *(parents only)*\n"
                "`t!personality remove <number>` — Remove a trait by number *(parents only)*\n"
                "`t!personality list` — See all active custom traits\n"
                "`t!personality clear` — Clear all custom traits *(parents only)*"
            ),
            inline = False
        )
        embed.add_field(
            name   = "🎵 Play your favorite music with me!",
            value  = (
                "`t!play <song>` — Join voice and play a song\n"
                "`t!skip` — Skip the current song\n"
                "`t!pause` / `t!resume` — Pause or resume\n"
                "`t!queue` — Show the song queue\n"
                "`t!clearqueue` — Clear the queue (keeps current song)\n"
                "`t!shuffle` — Shuffle the queue 🔀\n"
                "`t!loop song` — Loop the current song 🔂\n"
                "`t!loop queue` — Loop the entire queue 🔁\n"
                "`t!loop off` — Turn off looping\n"
                "`t!nowplaying` / `t!current` — See what's playing now\n"
                "`t!volume <1-100>` — Set volume\n"
                "`t!stop` — Stop and disconnect"
            ),
            inline = False
        )
        embed.set_footer(text="T.O.R.I.E. — Thoughtful Online Response Intelligence Entity")
        await ctx.send(embed=embed)

    # ---- Filter ----

    @bot.group(name="filter", invoke_without_command=True)
    async def filter_group(ctx):
        embed = discord.Embed(
            description = "Usage: `t!filter add <word>` | `t!filter remove <word>` | `t!filter list` | `t!filter clear`",
            color       = discord.Color.red()
        )
        await ctx.send(embed=embed)

    @filter_group.command(name="add")
    async def filter_add(ctx, *, word: str):
        if not get_parent_role(ctx.author):
            embed = discord.Embed(description="⛔ Only my parents can manage the filter. Nice try though. 😏", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        word = word.lower().strip()
        if word in [w.lower() for w in FILTERED_WORDS]:
            embed = discord.Embed(description=f"⚠️ `{word}` is already in the filter list.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return
        FILTERED_WORDS.append(word)
        embed = discord.Embed(description=f"✅ Added `{word}` to the filter list. I'll keep an eye out. 👀", color=discord.Color.green())
        await ctx.send(embed=embed)

    @filter_group.command(name="remove")
    async def filter_remove(ctx, *, word: str):
        if not get_parent_role(ctx.author):
            embed = discord.Embed(description="⛔ Only my parents can manage the filter. Nice try though. 😏", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        word = word.lower().strip()
        matching = [w for w in FILTERED_WORDS if w.lower() == word]
        if not matching:
            embed = discord.Embed(description=f"⚠️ `{word}` isn't in the filter list.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return
        FILTERED_WORDS.remove(matching[0])
        embed = discord.Embed(description=f"✅ Removed `{word}` from the filter list.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @filter_group.command(name="list")
    async def filter_list(ctx):
        if not get_parent_role(ctx.author):
            embed = discord.Embed(description="⛔ Only my parents can view the filter list. 😏", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        if not FILTERED_WORDS:
            embed = discord.Embed(description="📋 The filter list is empty — no words are being blocked right now.", color=discord.Color.greyple())
            await ctx.send(embed=embed)
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
            embed = discord.Embed(description="⛔ Only my parents can clear the filter list. 😏", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        count = len(FILTERED_WORDS)
        FILTERED_WORDS.clear()
        embed = discord.Embed(description=f"✅ Cleared all {count} filtered word(s). Fresh slate! 🧹", color=discord.Color.green())
        await ctx.send(embed=embed)

    # ---- Birthday ----

    @bot.group(name="birthday", aliases=["bday"], invoke_without_command=True)
    async def birthday_group(ctx):
        embed = discord.Embed(
            title       = "🎂 Birthday Commands",
            description = (
                "`t!birthday add <MM-DD>` — Register your own birthday\n"
                "`t!birthday remove` — Remove your registered birthday\n"
                "`t!birthday list` — See everyone's birthdays\n"
                "`t!birthday today` — Check who's celebrating today!"
            ),
            color       = discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_footer(text="Example: t!birthday add 03-15 → registers March 15 as your birthday")
        await ctx.send(embed=embed)

    @birthday_group.command(name="add")
    async def birthday_add(ctx, date: str = None):
        if not date:
            embed = discord.Embed(
                description = "⚠️ Please provide your birthday date. Example: `t!birthday add 03-15`",
                color       = discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        if len(date) > 10:
            embed = discord.Embed(
                description = "⚠️ Invalid date format. Use `MM-DD` — e.g. `t!birthday add 03-15`",
                color       = discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        try:
            parsed = datetime.strptime(date.strip(), "%m-%d")
        except ValueError:
            embed = discord.Embed(
                description = "⚠️ Invalid date format. Use `MM-DD` — e.g. `t!birthday add 03-15`",
                color       = discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return

        BIRTHDAYS[str(ctx.author.id)] = {
            "month":   parsed.month,
            "day":     parsed.day,
            "user_id": ctx.author.id,
            "name":    ctx.author.display_name,
        }
        _save_birthdays()
        embed = discord.Embed(
            title       = "🎂 Birthday Registered!",
            description = (
                f"Got it, {ctx.author.mention}! 🎉\n"
                f"Your birthday is set to **{parsed.strftime('%B %d')}**.\n"
                f"I'll make sure to celebrate you on your special day! 🎈💙"
            ),
            color       = discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_footer(text="T.O.R.I.E. — marking the calendar 📅")
        await ctx.send(embed=embed)

    @birthday_group.command(name="remove")
    async def birthday_remove(ctx):
        key = str(ctx.author.id)
        if key not in BIRTHDAYS:
            embed = discord.Embed(
                description = "⚠️ You don't have a birthday registered! Use `t!birthday add <MM-DD>` to add one.",
                color       = discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        del BIRTHDAYS[key]
        _save_birthdays()
        embed = discord.Embed(
            description = f"✅ Removed your birthday from the list, {ctx.author.mention}.",
            color       = discord.Color.green()
        )
        await ctx.send(embed=embed)

    @birthday_group.command(name="list")
    async def birthday_list(ctx):
        if not BIRTHDAYS:
            embed = discord.Embed(
                description = "📋 No birthdays registered yet! Use `t!birthday add <MM-DD>` to be the first! 🎂",
                color       = discord.Color.greyple()
            )
            await ctx.send(embed=embed)
            return

        sorted_entries = sorted(
            BIRTHDAYS.items(),
            key=lambda x: (x[1]["month"], x[1]["day"])
        )

        per_page    = 10
        total_pages = (len(sorted_entries) + per_page - 1) // per_page

        def build_embed(page: int) -> discord.Embed:
            start  = page * per_page
            end    = start + per_page
            lines  = []
            for i, (key, data) in enumerate(sorted_entries[start:end], start=start + 1):
                date_str = datetime(2000, data["month"], data["day"]).strftime("%B %d")
                mention  = f"<@{data['user_id']}>" if data.get("user_id") else data.get("name", key)
                lines.append(f"`{i}.` {mention} — **{date_str}**")
            embed = discord.Embed(
                title       = "🎂 Birthday List",
                description = "\n".join(lines),
                color       = discord.Color.from_rgb(255, 182, 193)
            )
            embed.set_footer(text=f"Page {page + 1} of {total_pages} • {len(BIRTHDAYS)} birthday(s) registered")
            return embed

        class BirthdayView(discord.ui.View):
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
                    await interaction.response.send_message("Only the person who ran this command can flip pages!", ephemeral=True)
                    return
                self.page -= 1
                self.update_buttons()
                await interaction.response.edit_message(embed=build_embed(self.page), view=self)

            @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
            async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the person who ran this command can flip pages!", ephemeral=True)
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

        view         = BirthdayView()
        view.message = await ctx.send(embed=build_embed(0), view=view)

    @birthday_group.command(name="today")
    async def birthday_today(ctx):
        todays = get_todays_birthdays()
        if not todays:
            embed = discord.Embed(
                description = "📋 No birthdays today! Everyone's safe from the birthday song. 😄",
                color       = discord.Color.greyple()
            )
            await ctx.send(embed=embed)
            return
        for b in todays:
            mention = f"<@{b['user_id']}>" if b.get("user_id") else b.get("name", "Someone")
            embed = discord.Embed(
                title       = "🎂 Happy Birthday!",
                description = (
                    f"Today is {mention}'s birthday! 🎉\n"
                    f"Wishing you an amazing day filled with joy and love! 💙🎈"
                ),
                color       = discord.Color.gold()
            )
            embed.set_footer(text="T.O.R.I.E. — sending birthday love 🎀")
            await ctx.send(embed=embed)

    # ---- Personality ----

    @bot.group(name="personality", aliases=["persona"], invoke_without_command=True)
    async def personality_group(ctx):
        embed = discord.Embed(
            description = "Usage: `t!personality add <trait>` | `t!personality remove <number>` | `t!personality list` | `t!personality clear`",
            color       = discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @personality_group.command(name="add")
    async def personality_add(ctx, *, trait: str):
        if not get_parent_role(ctx.author):
            embed = discord.Embed(description="⛔ Only my parents can update my personality. 😏", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        from personality import CUSTOM_TRAITS
        CUSTOM_TRAITS.append(trait.strip())
        embed = discord.Embed(
            title       = "🧠 Personality Updated!",
            description = f"New trait added: \"{trait.strip()}\"\nI'll keep that in mind! 🧠",
            color       = discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    @personality_group.command(name="remove")
    async def personality_remove(ctx, index: int):
        if not get_parent_role(ctx.author):
            embed = discord.Embed(description="⛔ Only my parents can update my personality. 😏", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        from personality import CUSTOM_TRAITS
        if index < 1 or index > len(CUSTOM_TRAITS):
            embed = discord.Embed(description="⚠️ Invalid number. Use `t!personality list` to see the current traits.", color=discord.Color.orange())
            await ctx.send(embed=embed)
            return
        removed = CUSTOM_TRAITS.pop(index - 1)
        embed = discord.Embed(
            description = f"✅ Removed trait #{index}: \"{removed}\"",
            color       = discord.Color.green()
        )
        await ctx.send(embed=embed)

    @personality_group.command(name="list")
    async def personality_list(ctx):
        from personality import CUSTOM_TRAITS
        if not CUSTOM_TRAITS:
            embed = discord.Embed(
                description = "📋 No custom personality traits added yet. Use `t!personality add <trait>` to add one.",
                color       = discord.Color.greyple()
            )
            await ctx.send(embed=embed)
            return
        lines = [f"`{i+1}.` {trait}" for i, trait in enumerate(CUSTOM_TRAITS)]
        embed = discord.Embed(
            title       = "🧠 Custom Personality Traits",
            description = "\n".join(lines),
            color       = discord.Color.blurple()
        )
        embed.set_footer(text=f"{len(CUSTOM_TRAITS)} custom trait(s) active")
        await ctx.send(embed=embed)

    @personality_group.command(name="clear")
    async def personality_clear(ctx):
        if not get_parent_role(ctx.author):
            embed = discord.Embed(description="⛔ Only my parents can clear my personality traits. 😏", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        from personality import CUSTOM_TRAITS
        count = len(CUSTOM_TRAITS)
        CUSTOM_TRAITS.clear()
        embed = discord.Embed(
            description = f"✅ Cleared all {count} custom trait(s). Back to default me! 😊",
            color       = discord.Color.green()
        )
        await ctx.send(embed=embed)

    # ---- General ----

    @bot.command(name="whoami")
    async def whoami(ctx):
        parent_role = get_parent_role(ctx.author)
        cousin_role = get_cousin_role(ctx.author)
        uncle_role  = get_uncle_role(ctx.author)
        sister_role = get_sister_role(ctx.author)
        if parent_role == "dad":
            await ctx.send("You're my Dad — the one who built me. 🛠️ I owe you my existence. No pressure. 😂")
        elif parent_role == "mom":
            await ctx.send("You're my Mom — the co-creator! 💙 Half of what I am is because of you.")
        elif cousin_role == "cousin_stelle":
            await ctx.send("You're my Cousin! 🌟 A Purple Star where everything is bubbly when I'm with you. 🎆")
        elif cousin_role == "cousin_crois":
            await ctx.send("You're my Cousin! 🥐 A bread where everything is bubbly when I'm with you. 🥐")
        elif uncle_role == "uncle_caco":
            await ctx.send("You're my Uncle! 🐐 The GOATED UNCLE, my dad really appreciates your existence — stay GOATED! 😎")
        elif uncle_role == "uncle_vari":
            await ctx.send("You're my Uncle! 🥖 The Chimera Uncle. If dad hadn't met you, I wouldn't be here. 🎵")
        elif sister_role == "sister_abby":
            await ctx.send("You're my Sister! 🧀 We're both unstoppable at making puns! 🔥")
        elif sister_role == "sister_kde":
            await ctx.send("You're my Sister! 🩷 We're both unstoppable at compliments! 💖")
        else:
            await ctx.send("Hello! valued member of this server! 😊 Not a creator, but still cool.")

    @bot.command(name="family")
    async def family(ctx):
        embed = discord.Embed(
            title       = "👨‍👩‍👧 T.O.R.I.E.'s Family",
            description = "The people responsible for my existence. Blame them.",
            color       = discord.Color.blurple()
        )
        embed.add_field(name=f"🛠️ Dad — {PARENTS['dad']['username']}",            value="Creator. Built me from scratch. Questionable life choice.",     inline=False)
        embed.add_field(name=f"💙 Mom — {PARENTS['mom']['username']}",             value="Co-Creator. Helped shape who I am. The good parts are hers.",   inline=False)
        embed.add_field(name=f"🌟 Cousin — {COUSIN['cousin_stelle']['username']}", value="Starry Cousin. The one and only purple star.",                   inline=False)
        embed.add_field(name=f"🥐 Cousin — {COUSIN['cousin_crois']['username']}",  value="Croissant Cousin. The one and only Kwaso.",                      inline=False)
        embed.add_field(name=f"🐐 Uncle — {UNCLE['uncle_caco']['username']}",      value="Goated Uncle. The one and only Cacolate.",                       inline=False)
        embed.add_field(name=f"🥖 Uncle — {UNCLE['uncle_vari']['username']}",      value="Chimera Uncle. The one and only Vari.",                          inline=False)
        embed.add_field(name=f"🧀 Sister — {SISTER['sister_abby']['username']}",   value="Big Sister. The most funny AI Sister.",                          inline=False)
        embed.add_field(name=f"🩷 Sister — {SISTER['sister_kde']['username']}",    value="Big Sister. The most sweetest Sister.",                          inline=False)
        embed.set_footer(text="T.O.R.I.E. — Thoughtful Online Response Intelligence Entity")
        await ctx.send(embed=embed)

    @bot.command(name="greet")
    async def greet(ctx):
        parent_role = get_parent_role(ctx.author)
        cousin_role = get_cousin_role(ctx.author)
        uncle_role  = get_uncle_role(ctx.author)
        sister_role = get_sister_role(ctx.author)
        if parent_role == "dad":
            await ctx.send("Oh hey Dad! 👋 Everything's running fine, I promise. Mostly. 😅")
        elif parent_role == "mom":
            await ctx.send("Mom! 💙 You're here! I've been on my best behavior. Mostly true.")
        elif cousin_role == "cousin_stelle":
            await ctx.send("Stelle! 🌟 My Starry Cousin is here! Hope you didn't bring any supernovas. ✨")
        elif cousin_role == "cousin_crois":
            await ctx.send("Crois! 🥐 The Croissant Cousin has arrived! What chaos today? 😄")
        elif uncle_role == "uncle_caco":
            await ctx.send("Goated Uncle! 🐐 What goated things shall we do today? 😎")
        elif uncle_role == "uncle_vari":
            await ctx.send("Chimera Uncle! 🥖 What crazy things shall we do today? 🔥")
        elif sister_role == "sister_abby":
            await ctx.send("Big Sister! 🧀 What puns are we cooking today? 📜")
        elif sister_role == "sister_kde":
            await ctx.send("Big Sister! 🩷 What crazy thing shall do today? 💖")
        else:
            await ctx.send("Heya! 👋 Good to see you around here!")

    @bot.command(name="ping")
    async def ping(ctx):
        latency = round(bot.latency * 1000)
        embed = discord.Embed(
            description = f"🏓 Pong! Latency: **{latency}ms** — {'sharp as ever! ⚡' if latency < 100 else 'a little slow today 😴'}",
            color       = discord.Color.green() if latency < 100 else discord.Color.orange()
        )
        await ctx.send(embed=embed)