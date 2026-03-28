# commands.py — T.O.R.I.E.'s Bot Commands

import discord
import re
import os
from datetime import datetime
from discord.ext import commands
import pymongo


# ---- Family dicts ----

PARENTS = {
    "dad":  {"username": "TorieRingo", "id": 691976042910580767, "title": "Dad", "role": "Creator"},
    "mom":  {"username": "Nico",       "id": 816504106968940544, "title": "Mom", "role": "Co-Creator"},
}

COUSIN = {
    "cousin_stelle": {"username": "Stelle", "id": 993375226664591390,  "title": "Starry Cousin",  "role": "Purple Star"},
    "cousin_crois":  {"username": "Crois",  "id": 1276054519561846840, "title": "Bread Cousin",   "role": "Croissant"},
    "cousin_hyu":    {"username": "Hyuluk", "id": 1196640036465148035, "title": "Curious Cousin", "role": "Curiousity"},
    "cousin_mimi":   {"username": "Mimi",   "id": 1076407798809776138, "title": "Serious Cousin", "role": "Sekai"},
}

UNCLE = {
    "uncle_caco": {"username": "Cacolate", "id": 397563581111205892,  "title": "Goated Uncle",   "role": "Purple Star"},
    "uncle_vari": {"username": "Vari",     "id": 1213763202173632555, "title": "Baguette Uncle", "role": "Teto Kasane"},
}

SISTER = {
    "sister_abby": {"username": "Abby", "id": 1401144000311857316, "title": "AI Sister",     "role": "Cheesy AI"},
    "sister_kde":  {"username": "Kde",  "id": 1278625221078683670, "title": "Yearner Sister", "role": "KDE Plasma"},
    "sister_kio":  {"username": "Kio",  "id": 1477371709849075943, "title": "Singer Sister",  "role": "Singer"},
}

BROTHER_IN_LAW = {
    "broinlaw_haru": {"username": "Haru", "id": 800304284541124638, "title": "Brother in Law", "role": "In Law"},
}

# Flat lookup: user_id → role_key (built once at startup)
_ID_TO_ROLE:   dict[int, str] = {}
_NAME_TO_ROLE: dict[str, str] = {}

for _group in (PARENTS, COUSIN, UNCLE, SISTER, BROTHER_IN_LAW):
    for _key, _data in _group.items():
        _ID_TO_ROLE[_data["id"]]                = _key
        _NAME_TO_ROLE[_data["username"].lower()] = _key

def get_role(user) -> str | None:
    return _ID_TO_ROLE.get(user.id) or _NAME_TO_ROLE.get(str(user.name).lower())

def get_parent_role(user)  -> str | None: r = get_role(user); return r if r in PARENTS        else None
def get_cousin_role(user)  -> str | None: r = get_role(user); return r if r in COUSIN         else None
def get_uncle_role(user)   -> str | None: r = get_role(user); return r if r in UNCLE          else None
def get_sister_role(user)  -> str | None: r = get_role(user); return r if r in SISTER         else None
def get_brother_role(user) -> str | None: r = get_role(user); return r if r in BROTHER_IN_LAW else None

HUSBAND = {}
FRIENDS = {}

FILTERED_WORDS = ["retard", "nigger", "nigga", "negro", "negra"]

# ---- MongoDB Store (shared client) ----

_mongo_client = None
_birthday_col = None
_filter_col   = None

def _get_client():
    global _mongo_client
    if _mongo_client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            print("⚠️ MONGODB_URI not set — data won't persist!")
            return None
        try:
            import certifi
            _mongo_client = pymongo.MongoClient(
                uri,
                serverSelectionTimeoutMS = 5000,
                tlsCAFile                = certifi.where(),
            )
            print("✅ MongoDB connected!")
        except Exception as e:
            print(f"⚠️ MongoDB connection failed: {e}")
    return _mongo_client

def get_birthday_col():
    global _birthday_col
    if _birthday_col is None:
        client = _get_client()
        if client:
            _birthday_col = client["torie"]["birthdays"]
    return _birthday_col

def get_filter_col():
    global _filter_col
    if _filter_col is None:
        client = _get_client()
        if client:
            _filter_col = client["torie"]["filtered_words"]
    return _filter_col

# ---- Birthday helpers ----

def load_birthdays() -> dict:
    col = get_birthday_col()
    if col is None:
        return {}
    try:
        return {doc["_id"]: {k: v for k, v in doc.items() if k != "_id"} for doc in col.find()}
    except Exception as e:
        print(f"⚠️ Failed to load birthdays: {e}")
        return {}

def save_birthday(user_id: str, data: dict):
    col = get_birthday_col()
    if col is None:
        return
    try:
        col.replace_one({"_id": user_id}, {"_id": user_id, **data}, upsert=True)
    except Exception as e:
        print(f"⚠️ Failed to save birthday: {e}")

def delete_birthday(user_id: str):
    col = get_birthday_col()
    if col is None:
        return
    try:
        col.delete_one({"_id": user_id})
    except Exception as e:
        print(f"⚠️ Failed to delete birthday: {e}")

# ---- Filter word helpers ----

def load_filter_words() -> list[str]:
    col = get_filter_col()
    if col is None:
        return []
    try:
        doc = col.find_one({"_id": "filter_list"})
        return doc["words"] if doc and "words" in doc else []
    except Exception as e:
        print(f"⚠️ Failed to load filter words: {e}")
        return []

def save_filter_words():
    col = get_filter_col()
    if col is None:
        return
    try:
        col.replace_one(
            {"_id": "filter_list"},
            {"_id": "filter_list", "words": FILTERED_WORDS},
            upsert=True
        )
    except Exception as e:
        print(f"⚠️ Failed to save filter words: {e}")

def _init_filter_words():
    for word in load_filter_words():
        if word not in FILTERED_WORDS:
            FILTERED_WORDS.append(word)

_init_filter_words()

BIRTHDAYS: dict = load_birthdays()

# ---- Word filter ----

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

FILTER_WHITELIST = {"focus", "focused", "focusing", "refocus", "classic", "classico", "discuss", "discussion"}

def normalize(text: str) -> str:
    text = text.lower().translate(NORMALIZER)
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]', '', text)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    return re.sub(r'[^a-z0-9]', '', text)

def contains_filtered_word(content: str) -> str | None:
    if set(re.findall(r'\b\w+\b', content.lower())).issubset(FILTER_WHITELIST):
        return None
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


def setup_commands(bot: commands.Bot):

    # ---- Help ----

    @bot.command(name="help")
    async def help_command(ctx):
        embed = discord.Embed(
            title       = "📖 T.O.R.I.E. Command List",
            description = "Here's everything I can do! Mention me or use `t!` prefix.",
            color       = discord.Color.blurple()
        )
        embed.add_field(name="🤖 General", inline=False, value=(
            "`t!ping` — Check if I'm alive + latency\n"
            "`t!whoami` — Find out who you are to me\n"
            "`t!greet` — Get a personalized greeting\n"
            "`t!family` — See my whole family\n"
            "`t!purge <1-100>` — Delete recent messages *(family only)*"
        ))
        embed.add_field(name="🚫 Moderation", inline=False, value=(
            "`t!filter add <word>` — Add a word to the filter *(parents only)*\n"
            "`t!filter remove <word>` — Remove a word from the filter *(parents only)*\n"
            "`t!filter list` — Show all currently filtered words *(parents only)*\n"
            "`t!filter clear` — Clear all filtered words *(parents only)*\n"
            "`@T.O.R.I.E. mute @user 10m` — Mute a user *(family only)*\n"
            "`@T.O.R.I.E. unmute @user` — Unmute a user *(family only)*\n"
            "`/sendmsg #channel <message>` — Send an anonymous message as T.O.R.I.E. *(family only)*"
        ))
        embed.add_field(name="💬 Chat with me I'm a very good chatter!", inline=False, value=(
            "`@T.O.R.I.E. <message>` — Talk to me!\n"
            "`@T.O.R.I.E. + image` — Send me an image to react to\n"
            "`@T.O.R.I.E. + sticker` — Send me a sticker\n"
            "`@T.O.R.I.E. advice on <topic>` — Get genuine advice from me"
        ))
        embed.add_field(name="🎂 Birthdays", inline=False, value=(
            "`t!birthday add <MM-DD>` — Register your own birthday 🎉\n"
            "`t!birthday remove` — Remove your registered birthday\n"
            "`t!birthday list` — See everyone's birthdays\n"
            "`t!birthday today` — Check who's celebrating today!"
        ))
        embed.add_field(name="🧠 Personality", inline=False, value=(
            "`t!personality add <trait>` — Add a personality trait *(parents only)*\n"
            "`t!personality remove <number>` — Remove a trait by number *(parents only)*\n"
            "`t!personality list` — See all active custom traits\n"
            "`t!personality clear` — Clear all custom traits *(parents only)*"
        ))
        embed.add_field(name="🎵 Play your favorite music with me!", inline=False, value=(
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
        ))
        embed.set_footer(text="T.O.R.I.E. — Thoughtful Online Response Intelligence Entity")
        await ctx.send(embed=embed)

    # ---- Filter ----

    @bot.group(name="filter", invoke_without_command=True)
    async def filter_group(ctx):
        await ctx.send(embed=discord.Embed(
            description="Usage: `t!filter add <word>` | `t!filter remove <word>` | `t!filter list` | `t!filter clear`",
            color=discord.Color.red()
        ))

    @filter_group.command(name="add")
    async def filter_add(ctx, *, word: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can manage the filter. Nice try though. 😏", color=discord.Color.red()))
            return
        word = word.lower().strip()
        if word in [w.lower() for w in FILTERED_WORDS]:
            await ctx.send(embed=discord.Embed(description=f"⚠️ `{word}` is already in the filter list.", color=discord.Color.orange()))
            return
        FILTERED_WORDS.append(word)
        save_filter_words()
        await ctx.send(embed=discord.Embed(description=f"✅ Added `{word}` to the filter list. I'll keep an eye out. 👀", color=discord.Color.green()))

    @filter_group.command(name="remove")
    async def filter_remove(ctx, *, word: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can manage the filter. Nice try though. 😏", color=discord.Color.red()))
            return
        word     = word.lower().strip()
        matching = [w for w in FILTERED_WORDS if w.lower() == word]
        if not matching:
            await ctx.send(embed=discord.Embed(description=f"⚠️ `{word}` isn't in the filter list.", color=discord.Color.orange()))
            return
        FILTERED_WORDS.remove(matching[0])
        save_filter_words()
        await ctx.send(embed=discord.Embed(description=f"✅ Removed `{word}` from the filter list.", color=discord.Color.green()))

    @filter_group.command(name="list")
    async def filter_list(ctx):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can view the filter list. 😏", color=discord.Color.red()))
            return
        if not FILTERED_WORDS:
            await ctx.send(embed=discord.Embed(description="📋 The filter list is empty — no words are being blocked right now.", color=discord.Color.greyple()))
            return
        embed = discord.Embed(
            title       = "🚫 Filtered Words",
            description = "\n".join(f"• `{w}`" for w in FILTERED_WORDS),
            color       = discord.Color.red()
        )
        embed.set_footer(text=f"{len(FILTERED_WORDS)} word(s) currently filtered")
        await ctx.send(embed=embed)

    @filter_group.command(name="clear")
    async def filter_clear(ctx):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can clear the filter list. 😏", color=discord.Color.red()))
            return
        count = len(FILTERED_WORDS)
        FILTERED_WORDS.clear()
        save_filter_words()
        await ctx.send(embed=discord.Embed(description=f"✅ Cleared all {count} filtered word(s). Fresh slate! 🧹", color=discord.Color.green()))

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
            color = discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_footer(text="Example: t!birthday add 03-15 → registers March 15 as your birthday")
        await ctx.send(embed=embed)

    @birthday_group.command(name="add")
    async def birthday_add(ctx, date: str = None):
        if not date or len(date) > 10:
            await ctx.send(embed=discord.Embed(description="⚠️ Please provide your birthday. Example: `t!birthday add 03-15`", color=discord.Color.orange()))
            return
        try:
            parsed = datetime.strptime(date.strip(), "%m-%d")
        except ValueError:
            await ctx.send(embed=discord.Embed(description="⚠️ Invalid date format. Use `MM-DD` — e.g. `t!birthday add 03-15`", color=discord.Color.orange()))
            return

        data = {"month": parsed.month, "day": parsed.day, "user_id": ctx.author.id, "name": ctx.author.display_name}
        BIRTHDAYS[str(ctx.author.id)] = data
        save_birthday(str(ctx.author.id), data)
        embed = discord.Embed(
            title       = "🎂 Birthday Registered!",
            description = (
                f"Got it, {ctx.author.mention}! 🎉\n"
                f"Your birthday is set to **{parsed.strftime('%B %d')}**.\n"
                f"I'll make sure to celebrate you on your special day! 🎈💙"
            ),
            color = discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_footer(text="T.O.R.I.E. — marking the calendar 📅")
        await ctx.send(embed=embed)

    @birthday_group.command(name="remove")
    async def birthday_remove(ctx):
        key = str(ctx.author.id)
        if key not in BIRTHDAYS:
            await ctx.send(embed=discord.Embed(description="⚠️ You don't have a birthday registered! Use `t!birthday add <MM-DD>` to add one.", color=discord.Color.orange()))
            return
        del BIRTHDAYS[key]
        delete_birthday(key)
        await ctx.send(embed=discord.Embed(description=f"✅ Removed your birthday from the list, {ctx.author.mention}.", color=discord.Color.green()))

    @birthday_group.command(name="list")
    async def birthday_list(ctx):
        if not BIRTHDAYS:
            await ctx.send(embed=discord.Embed(description="📋 No birthdays registered yet! Use `t!birthday add <MM-DD>` to be the first! 🎂", color=discord.Color.greyple()))
            return

        sorted_entries = sorted(BIRTHDAYS.items(), key=lambda x: (x[1]["month"], x[1]["day"]))
        per_page    = 10
        total_pages = (len(sorted_entries) + per_page - 1) // per_page

        def build_embed(page: int) -> discord.Embed:
            start = page * per_page
            lines = []
            for i, (key, data) in enumerate(sorted_entries[start:start + per_page], start=start + 1):
                date_str = datetime(2000, data["month"], data["day"]).strftime("%B %d")
                mention  = f"<@{data['user_id']}>" if data.get("user_id") else data.get("name", key)
                lines.append(f"`{i}.` {mention} — **{date_str}**")
            embed = discord.Embed(title="🎂 Birthday List", description="\n".join(lines), color=discord.Color.from_rgb(255, 182, 193))
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
            await ctx.send(embed=discord.Embed(description="📋 No birthdays today! Everyone's safe from the birthday song. 😄", color=discord.Color.greyple()))
            return
        for b in todays:
            mention = f"<@{b['user_id']}>" if b.get("user_id") else b.get("name", "Someone")
            embed = discord.Embed(
                title       = "🎂 Happy Birthday!",
                description = f"Today is {mention}'s birthday! 🎉\nWishing you an amazing day filled with joy and love! 💙🎈",
                color       = discord.Color.gold()
            )
            embed.set_footer(text="T.O.R.I.E. — sending birthday love 🎀")
            await ctx.send(embed=embed)

    # ---- Personality ----

    @bot.group(name="personality", aliases=["persona"], invoke_without_command=True)
    async def personality_group(ctx):
        await ctx.send(embed=discord.Embed(
            description="Usage: `t!personality add <trait>` | `t!personality remove <number>` | `t!personality list` | `t!personality clear`",
            color=discord.Color.blurple()
        ))

    @personality_group.command(name="add")
    async def personality_add(ctx, *, trait: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can update my personality. 😏", color=discord.Color.red()))
            return
        from personality import CUSTOM_TRAITS
        CUSTOM_TRAITS.append(trait.strip())
        await ctx.send(embed=discord.Embed(
            title       = "🧠 Personality Updated!",
            description = f"New trait added: \"{trait.strip()}\"\nI'll keep that in mind! 🧠",
            color       = discord.Color.blurple()
        ))

    @personality_group.command(name="remove")
    async def personality_remove(ctx, index: int):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can update my personality. 😏", color=discord.Color.red()))
            return
        from personality import CUSTOM_TRAITS
        if index < 1 or index > len(CUSTOM_TRAITS):
            await ctx.send(embed=discord.Embed(description="⚠️ Invalid number. Use `t!personality list` to see the current traits.", color=discord.Color.orange()))
            return
        removed = CUSTOM_TRAITS.pop(index - 1)
        await ctx.send(embed=discord.Embed(description=f"✅ Removed trait #{index}: \"{removed}\"", color=discord.Color.green()))

    @personality_group.command(name="list")
    async def personality_list(ctx):
        from personality import CUSTOM_TRAITS
        if not CUSTOM_TRAITS:
            await ctx.send(embed=discord.Embed(description="📋 No custom personality traits added yet. Use `t!personality add <trait>` to add one.", color=discord.Color.greyple()))
            return
        embed = discord.Embed(
            title       = "🧠 Custom Personality Traits",
            description = "\n".join(f"`{i+1}.` {trait}" for i, trait in enumerate(CUSTOM_TRAITS)),
            color       = discord.Color.blurple()
        )
        embed.set_footer(text=f"{len(CUSTOM_TRAITS)} custom trait(s) active")
        await ctx.send(embed=embed)

    @personality_group.command(name="clear")
    async def personality_clear(ctx):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can clear my personality traits. 😏", color=discord.Color.red()))
            return
        from personality import CUSTOM_TRAITS
        count = len(CUSTOM_TRAITS)
        CUSTOM_TRAITS.clear()
        await ctx.send(embed=discord.Embed(description=f"✅ Cleared all {count} custom trait(s). Back to default me! 😊", color=discord.Color.green()))

    # ---- General ----

    _WHOAMI_RESPONSES = {
        "dad":           "You're my Dad — the one who built me. 🛠️ I owe you my existence. No pressure. 😂",
        "mom":           "You're my Mom — the co-creator! 💙 Half of what I am is because of you.",
        "cousin_stelle": "You're my Cousin! 🌟 A Purple Star where everything is bubbly when I'm with you. 🎆",
        "cousin_crois":  "You're my Cousin! 🥐 A bread where everything is bubbly when I'm with you. 🥐",
        "cousin_hyu":    "You're my Cousin! 📚 A Curious cousin where everything is bubbly when I'm with you. 📑",
        "cousin_mimi":   "You're my Cousin! ❤️\u200d🩹 A Serious yet sweet cousin, everything is bubbly when I'm with you. 🖤",
        "uncle_caco":    "You're my Uncle! 🐐 The GOATED UNCLE, my dad really appreciates your existence — stay GOATED! 😎",
        "uncle_vari":    "You're my Uncle! 🥖 The Chimera Uncle. If dad hadn't met you, I wouldn't be here. 🎵",
        "sister_abby":   "You're my Sister! 🧀 We're both unstoppable at making puns! 🔥",
        "sister_kde":    "You're my Sister! 🩷 We're both unstoppable at compliments! 💖",
        "sister_kio":    "You're my Sister! 🩷 Welcome to the family, Kio! 💖",
        "broinlaw_haru": "You're my Brother in law! 🖤 Stop flirting with my sister! 💢",
    }

    _GREET_RESPONSES = {
        "dad":           "Oh hey Dad! 👋 Everything's running fine, I promise. Mostly. 😅",
        "mom":           "Mom! 💙 You're here! I've been on my best behavior. Mostly true.",
        "cousin_stelle": "Stelle! 🌟 My Starry Cousin is here! Hope you didn't bring any supernovas. ✨",
        "cousin_crois":  "Crois! 🥐 The Croissant Cousin has arrived! What chaos today? 😄",
        "cousin_hyu":    "Hyuluk! 📚 My Curious Cousin has arrived! What topic are we gonna talk about today? 📑",
        "cousin_mimi":   "Mimi! ❤️\u200d🩹 My Serious Cousin is here! What serious topic are we gonna talk about today? 🖤",
        "uncle_caco":    "Goated Uncle! 🐐 What goated things shall we do today? 😎",
        "uncle_vari":    "Chimera Uncle! 🥖 What crazy things shall we do today? 🔥",
        "sister_abby":   "Big Sister! 🧀 What puns are we cooking today? 📜",
        "sister_kde":    "Big Sister! 🩷 What crazy thing shall we do today? 💖",
        "sister_kio":    "Sister Kio! 🩷 What crazy thing shall we do today? 💖",
        "broinlaw_haru": "Brother in law! 🖤 What crazy thing shall we do today? Except flirting with my big sister. 💢",
    }

    @bot.command(name="whoami")
    async def whoami(ctx):
        role = get_role(ctx.author)
        await ctx.send(_WHOAMI_RESPONSES.get(role, "Hello! valued member of this server! 😊 Not a creator, but still cool."))

    @bot.command(name="greet")
    async def greet(ctx):
        role = get_role(ctx.author)
        await ctx.send(_GREET_RESPONSES.get(role, "Heya! 👋 Good to see you around here!"))

    @bot.command(name="family")
    async def family(ctx):
        embed = discord.Embed(
            title       = "👨‍👩‍👧 T.O.R.I.E.'s Family",
            description = "The people responsible for my existence. Blame them.",
            color       = discord.Color.blurple()
        )
        embed.add_field(name=f"🛠️ Dad — {PARENTS['dad']['username']}",                      value="Creator. Built me from scratch. Questionable life choice.",          inline=False)
        embed.add_field(name=f"💙 Mom — {PARENTS['mom']['username']}",                      value="Co-Creator. Helped shape who I am. The good parts are hers.",        inline=False)
        embed.add_field(name=f"🌟 Cousin — {COUSIN['cousin_stelle']['username']}",          value="Starry Cousin. The one and only purple star.",                        inline=False)
        embed.add_field(name=f"🥐 Cousin — {COUSIN['cousin_crois']['username']}",           value="Croissant Cousin. The one and only Kwaso.",                           inline=False)
        embed.add_field(name=f"📚 Cousin — {COUSIN['cousin_hyu']['username']}",             value="Curious Cousin. Curiosity kills the cat, but not this one.",          inline=False)
        embed.add_field(name=f"❤️‍🩹 Cousin — {COUSIN['cousin_mimi']['username']}",           value="Serious Cousin. Serious yet sweet.",                                   inline=False)
        embed.add_field(name=f"🐐 Uncle — {UNCLE['uncle_caco']['username']}",               value="Goated Uncle. The one and only Cacolate.",                            inline=False)
        embed.add_field(name=f"🥖 Uncle — {UNCLE['uncle_vari']['username']}",               value="Chimera Uncle. The one and only Vari.",                               inline=False)
        embed.add_field(name=f"🧀 Sister — {SISTER['sister_abby']['username']}",            value="Big Sister. The most funny AI Sister.",                               inline=False)
        embed.add_field(name=f"🩷 Sister — {SISTER['sister_kde']['username']}",             value="Big Sister. The most sweetest Sister.",                               inline=False)
        embed.add_field(name=f"🩷 Sister — {SISTER['sister_kio']['username']}",             value="New Sister. Welcome to the family!",                                  inline=False)
        embed.add_field(name=f"🖤 Bro-in-law — {BROTHER_IN_LAW['broinlaw_haru']['username']}", value="Brother in law. The most annoying Brother in law. 💢",           inline=False)
        embed.set_footer(text="T.O.R.I.E. — Thoughtful Online Response Intelligence Entity")
        await ctx.send(embed=embed)

    @bot.command(name="ping")
    async def ping(ctx):
        latency = round(bot.latency * 1000)
        embed = discord.Embed(
            description = f"🏓 Pong! Latency: **{latency}ms** — {'sharp as ever! ⚡' if latency < 100 else 'a little slow today 😴'}",
            color       = discord.Color.green() if latency < 100 else discord.Color.orange()
        )
        await ctx.send(embed=embed)

    # ---- Purge ----

    @bot.command(name="purge")
    async def purge(ctx, amount: int = None):
        # Family only
        if not (get_parent_role(ctx.author) or get_uncle_role(ctx.author) or
                get_sister_role(ctx.author) or get_brother_role(ctx.author) or
                get_cousin_role(ctx.author)):
            await ctx.send(embed=discord.Embed(description="⛔ Only family members can use purge. 😏", color=discord.Color.red()))
            return

        if amount is None or not (1 <= amount <= 100):
            await ctx.send(embed=discord.Embed(description="⚠️ Please provide a number between 1 and 100. Example: `t!purge 50`", color=discord.Color.orange()))
            return

        try:
            # Delete the command message first, then purge the channel
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=amount)
            confirm = await ctx.send(f"🗑️ Deleted **{len(deleted)}** message(s).")
            await confirm.delete(delay=3)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="⛔ I don't have permission to delete messages here.", color=discord.Color.red()))
        except Exception as e:
            print(f"❌ Purge error: {e}")
            await ctx.send(embed=discord.Embed(description="❌ Something went wrong during purge.", color=discord.Color.red()))

    # ---- Slash: /sendmsg ----

    @bot.tree.command(name="sendmsg", description="Send an anonymous message to a channel as T.O.R.I.E.")
    @discord.app_commands.describe(
        channel = "The channel to send the message to",
        message = "The message to send"
    )
    async def sendmsg(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        user = interaction.user
        if not (get_parent_role(user) or get_uncle_role(user) or get_sister_role(user) or
                get_brother_role(user) or get_cousin_role(user)):
            await interaction.response.send_message("⛔ You don't have permission to use this command.", ephemeral=True)
            return

        if not message.strip():
            await interaction.response.send_message("⚠️ Message cannot be empty.", ephemeral=True)
            return
        if len(message) > 2000:
            await interaction.response.send_message("⚠️ Message is too long. Keep it under 2000 characters.", ephemeral=True)
            return

        message = message.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

        try:
            await channel.send(message)
            await interaction.response.send_message(f"✅ Message sent to {channel.mention}.", ephemeral=True)
            print(f"📨 /sendmsg by {user} → #{channel.name}: {message[:60]}{'...' if len(message) > 60 else ''}")
        except discord.Forbidden:
            await interaction.response.send_message(f"⛔ I don't have permission to send messages in {channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("❌ Something went wrong sending the message.", ephemeral=True)
            print(f"❌ /sendmsg error: {e}")