# commands.py — T.O.R.I.E.'s Bot Commands
 
import discord
import re
import os
from datetime import datetime
from discord.ext import commands
import pymongo
import aiohttp
import random
import os
 
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
_whitelist_col = None
_warn_col     = None
_perm_col     = None
 
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
        c = _get_client()
        if c: _birthday_col = c["torie"]["birthdays"]
    return _birthday_col
 
def get_filter_col():
    global _filter_col
    if _filter_col is None:
        c = _get_client()
        if c: _filter_col = c["torie"]["filtered_words"]
    return _filter_col

def get_whitelist_col():
    global _whitelist_col
    if _whitelist_col is None:
        c = _get_client()
        if c: _whitelist_col = c["torie"]["whitelisted_words"]
    return _whitelist_col
 
def get_warn_col():
    global _warn_col
    if _warn_col is None:
        c = _get_client()
        if c: _warn_col = c["torie"]["warns"]
    return _warn_col
 
def get_perm_col():
    global _perm_col
    if _perm_col is None:
        c = _get_client()
        if c: _perm_col = c["torie"]["permissions"]
    return _perm_col
 
 
# ---- Birthday helpers ----
 
def load_birthdays() -> dict:
    col = get_birthday_col()
    if col is None: return {}
    try:
        return {doc["_id"]: {k: v for k, v in doc.items() if k != "_id"} for doc in col.find()}
    except Exception as e:
        print(f"⚠️ Failed to load birthdays: {e}"); return {}
 
def save_birthday(user_id: str, data: dict):
    col = get_birthday_col()
    if col is None: return
    try:
        col.replace_one({"_id": user_id}, {"_id": user_id, **data}, upsert=True)
    except Exception as e:
        print(f"⚠️ Failed to save birthday: {e}")
 
def delete_birthday(user_id: str):
    col = get_birthday_col()
    if col is None: return
    try:
        col.delete_one({"_id": user_id})
    except Exception as e:
        print(f"⚠️ Failed to delete birthday: {e}")
 
 
# ---- Filter word helpers ----
 
def load_filter_words() -> list[str]:
    col = get_filter_col()
    if col is None: return []
    try:
        doc = col.find_one({"_id": "filter_list"})
        return doc["words"] if doc and "words" in doc else []
    except Exception as e:
        print(f"⚠️ Failed to load filter words: {e}"); return []
 
def save_filter_words():
    col = get_filter_col()
    if col is None: return
    try:
        col.replace_one({"_id": "filter_list"}, {"_id": "filter_list", "words": FILTERED_WORDS}, upsert=True)
    except Exception as e:
        print(f"⚠️ Failed to save filter words: {e}")
 
def _init_filter_words():
    for word in load_filter_words():
        if word not in FILTERED_WORDS:
            FILTERED_WORDS.append(word)
 
_init_filter_words()
BIRTHDAYS: dict = load_birthdays()
 
 
# ---- Warn helpers ----
 
def load_warns(user_id: str) -> list:
    col = get_warn_col()
    if col is None: return []
    try:
        doc = col.find_one({"_id": user_id})
        return doc["warns"] if doc and "warns" in doc else []
    except Exception as e:
        print(f"⚠️ Failed to load warns: {e}"); return []
 
def add_warn(user_id: str, reason: str, mod_name: str) -> int:
    col = get_warn_col()
    if col is None: return 0
    try:
        entry = {
            "reason": reason,
            "mod":    mod_name,
            "time":   datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        }
        col.update_one({"_id": user_id}, {"$push": {"warns": entry}}, upsert=True)
        doc = col.find_one({"_id": user_id})
        return len(doc["warns"]) if doc else 1
    except Exception as e:
        print(f"⚠️ Failed to add warn: {e}"); return 0
 
def clear_warns(user_id: str):
    col = get_warn_col()
    if col is None: return
    try:
        col.delete_one({"_id": user_id})
    except Exception as e:
        print(f"⚠️ Failed to clear warns: {e}")
 
 
# ---- Permission helpers ----
 
VALID_PERMS = {"mute", "unmute", "filter", "personality", "purge", "sendmsg", "warn", "mod"}
 
# Family role → default permissions (without needing t!perm grant)
_FAMILY_DEFAULT_PERMS: dict[str, set] = {
    "dad":           {"mod"},
    "mom":           {"mod"},
    "cousin_stelle": {"mute", "unmute", "warn", "purge", "sendmsg"},
    "cousin_crois":  {"mute", "unmute", "warn", "purge", "sendmsg"},
    "cousin_hyu":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "cousin_mimi":   {"mute", "unmute", "warn", "purge", "sendmsg"},
    "uncle_caco":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "uncle_vari":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "sister_abby":   {"mute", "unmute", "warn", "purge", "sendmsg"},
    "sister_kde":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "sister_kio":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "broinlaw_haru": {"mute", "unmute", "warn", "purge", "sendmsg"},
}

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


# ---------------------------------------------------------------------------
# KLIPY GIF search  (replaces Tenor — Tenor shuts down June 2026)
#
# Endpoint : GET https://api.klipy.com/api/v1/{API_KEY}/gifs/search
# Params   : q (query string), limit (int)
# API key  : embedded in the URL path, NOT a query param
# Response : { "data": [ { "media": { "gif": { "url": "..." } } }, ... ] }
#
# Get your free key at https://klipy.com/developers
# ---------------------------------------------------------------------------

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
                data = await resp.json()
                results = data.get("data", {}).get("data", [])
                if not results:
                    return None
                random.shuffle(results)
                item = random.choice(results)
                return item["file"]["hd"]["gif"]["url"]
    except Exception as e:
        print(f"⚠️ Klipy GIF search error: {type(e).__name__}: {e}")
        return None

def load_user_perms(user_id: int) -> set:
    col = get_perm_col()
    if col is None: return set()
    try:
        doc = col.find_one({"_id": str(user_id)})
        return set(doc["perms"]) if doc and "perms" in doc else set()
    except Exception as e:
        print(f"⚠️ Failed to load permissions: {e}"); return set()
 
def grant_perm(user_id: int, perm: str) -> bool:
    col = get_perm_col()
    if col is None: return False
    try:
        col.update_one({"_id": str(user_id)}, {"$addToSet": {"perms": perm}}, upsert=True)
        return True
    except Exception as e:
        print(f"⚠️ Failed to grant perm: {e}"); return False
 
def revoke_perm(user_id: int, perm: str) -> bool:
    col = get_perm_col()
    if col is None: return False
    try:
        col.update_one({"_id": str(user_id)}, {"$pull": {"perms": perm}})
        return True
    except Exception as e:
        print(f"⚠️ Failed to revoke perm: {e}"); return False
 
def has_permission(user, perm: str) -> bool:
    """Check if user has a permission via MongoDB grant OR family role defaults."""
    db_perms = load_user_perms(user.id)
    if "mod" in db_perms or perm in db_perms:
        return True
    role = get_role(user)
    if role:
        defaults = _FAMILY_DEFAULT_PERMS.get(role, set())
        if "mod" in defaults or perm in defaults:
            return True
    return False
 
 
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
FILTER_WHITELIST = {
    "focus", "focused", "focusing", "refocus",
    "classic", "classico", "discuss", "discussion",
    "snicker", "snigger", "trigger", "bigger", "digger",
    "figure", "figures", "niggle", "niggly", "niggard",
    "assign", "assigned", "assignee", "significant",
}

def contains_filtered_word(content: str) -> str | None:
    original_words = re.findall(r'\b\w+\b', content.lower())

    if set(original_words).issubset(FILTER_WHITELIST):
        return None

    normalized = normalize(content)
    for word in FILTERED_WORDS:
        norm_word = normalize(word)
        if norm_word not in normalized:
            continue
        if any(norm_word in normalize(w) for w in original_words if w in FILTER_WHITELIST):
            continue
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
            "`t!purge <1-100>` — Delete recent messages *(perm: purge)*"
        ))
        embed.add_field(name="🚫 Moderation", inline=False, value=(
            "`t!filter add/remove/list/clear <word>` — Word filter *(perm: filter)*\n"
            "`@T.O.R.I.E. mute @user 10m` — Mute a user *(perm: mute)*\n"
            "`@T.O.R.I.E. unmute @user` — Unmute *(perm: unmute)*\n"
            "`@T.O.R.I.E. warn @user [reason]` — Warn + auto-mute 10min *(perm: warn)*\n"
            "`t!warns @user` — Check warn history\n"
            "`t!warns @user clear` — Clear warns *(perm: warn)*\n"
            "`/sendmsg #channel <message>` — Anonymous message *(perm: sendmsg)*"
        ))
        embed.add_field(name="🔑 Permissions", inline=False, value=(
            "`t!perm add @user <perm>` — Grant a permission *(parents only)*\n"
            "`t!perm remove @user <perm>` — Revoke a permission *(parents only)*\n"
            "`t!perm list [@user]` — View permissions\n"
            "Perms: `mute` `unmute` `filter` `personality` `purge` `sendmsg` `warn` `mod`"
        ))
        embed.add_field(name="💬 Chat!", inline=False, value=(
            "`@T.O.R.I.E. <message>` — Talk to me!\n"
            "`@T.O.R.I.E. hug/kiss/pat/bite/lick/punch/kick/fuck @user` — Anime GIF interaction\n"
            "`tor <action> @user` — Catch-all shortcut (e.g. `tor punch @user`)\n"
            "`t!hug/kiss/pat/bite/lick/punch/kick/fuck @user` — Shortcut version\n"
            "`@T.O.R.I.E. + image` — React to an image\n"
            "`@T.O.R.I.E. advice on <topic>` — Get genuine advice"
        ))
        embed.add_field(name="🎂 Birthdays", inline=False, value=(
            "`t!birthday add <MM-DD>` — Register your birthday 🎉\n"
            "`t!birthday remove` — Remove your birthday\n"
            "`t!birthday list` — See everyone's birthdays\n"
            "`t!birthday today` — Check today's birthdays"
        ))
        embed.add_field(name="🧠 Personality", inline=False, value=(
            "`t!personality add <trait>` — Add a trait *(perm: personality)*\n"
            "`t!personality remove <number>` — Remove a trait *(perm: personality)*\n"
            "`t!personality list` — See active traits\n"
            "`t!personality clear` — Clear all traits *(perm: personality)*"
        ))
        embed.add_field(name="🎵 Music", inline=False, value=(
            "`t!play <song>` `t!skip` `t!pause` `t!resume`\n"
            "`t!queue` `t!clearqueue` `t!shuffle` `t!loop song/queue/off`\n"
            "`t!nowplaying` `t!volume <1-100>` `t!stop`"
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
        if not has_permission(ctx.author, "filter"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to manage the filter.", color=discord.Color.red()))
            return
        word = word.lower().strip()
        if word in [w.lower() for w in FILTERED_WORDS]:
            await ctx.send(embed=discord.Embed(description=f"⚠️ `{word}` is already in the filter list.", color=discord.Color.orange()))
            return
        FILTERED_WORDS.append(word)
        save_filter_words()
        await ctx.send(embed=discord.Embed(description=f"✅ Added `{word}` to the filter list. 👀", color=discord.Color.green()))
 
    @filter_group.command(name="remove")
    async def filter_remove(ctx, *, word: str):
        if not has_permission(ctx.author, "filter"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to manage the filter.", color=discord.Color.red()))
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
        if not has_permission(ctx.author, "filter"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to view the filter list.", color=discord.Color.red()))
            return
        if not FILTERED_WORDS:
            await ctx.send(embed=discord.Embed(description="📋 The filter list is empty.", color=discord.Color.greyple()))
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
        if not has_permission(ctx.author, "filter"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to clear the filter.", color=discord.Color.red()))
            return
        count = len(FILTERED_WORDS)
        FILTERED_WORDS.clear()
        save_filter_words()
        await ctx.send(embed=discord.Embed(description=f"✅ Cleared all {count} filtered word(s). 🧹", color=discord.Color.green()))
 
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
        embed.set_footer(text="Example: t!birthday add 03-15 → registers March 15")
        await ctx.send(embed=embed)
 
    @birthday_group.command(name="add")
    async def birthday_add(ctx, date: str = None):
        if not date or len(date) > 10:
            await ctx.send(embed=discord.Embed(description="⚠️ Please provide your birthday. Example: `t!birthday add 03-15`", color=discord.Color.orange()))
            return
        try:
            parsed = datetime.strptime(date.strip(), "%m-%d")
        except ValueError:
            await ctx.send(embed=discord.Embed(description="⚠️ Invalid date format. Use `MM-DD`.", color=discord.Color.orange()))
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
            await ctx.send(embed=discord.Embed(description="⚠️ You don't have a birthday registered!", color=discord.Color.orange()))
            return
        del BIRTHDAYS[key]
        delete_birthday(key)
        await ctx.send(embed=discord.Embed(description=f"✅ Removed your birthday, {ctx.author.mention}.", color=discord.Color.green()))
 
    @birthday_group.command(name="list")
    async def birthday_list(ctx):
        if not BIRTHDAYS:
            await ctx.send(embed=discord.Embed(description="📋 No birthdays registered yet! 🎂", color=discord.Color.greyple()))
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
            embed.set_footer(text=f"Page {page + 1} of {total_pages} • {len(BIRTHDAYS)} registered")
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
                    await interaction.response.send_message("Only the command author can flip pages!", ephemeral=True); return
                self.page -= 1; self.update_buttons()
                await interaction.response.edit_message(embed=build_embed(self.page), view=self)
            @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
            async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the command author can flip pages!", ephemeral=True); return
                self.page += 1; self.update_buttons()
                await interaction.response.edit_message(embed=build_embed(self.page), view=self)
            async def on_timeout(self):
                for child in self.children: child.disabled = True
                try: await self.message.edit(view=self)
                except Exception: pass
 
        view = BirthdayView()
        view.message = await ctx.send(embed=build_embed(0), view=view)
 
    @birthday_group.command(name="today")
    async def birthday_today(ctx):
        todays = get_todays_birthdays()
        if not todays:
            await ctx.send(embed=discord.Embed(description="📋 No birthdays today! 😄", color=discord.Color.greyple()))
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
        if not has_permission(ctx.author, "personality"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to update personality.", color=discord.Color.red()))
            return
        from personality import CUSTOM_TRAITS
        CUSTOM_TRAITS.append(trait.strip())
        await ctx.send(embed=discord.Embed(
            title="🧠 Personality Updated!",
            description=f"New trait added: \"{trait.strip()}\"\nI'll keep that in mind! 🧠",
            color=discord.Color.blurple()
        ))
 
    @personality_group.command(name="remove")
    async def personality_remove(ctx, index: int):
        if not has_permission(ctx.author, "personality"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to update personality.", color=discord.Color.red()))
            return
        from personality import CUSTOM_TRAITS
        if index < 1 or index > len(CUSTOM_TRAITS):
            await ctx.send(embed=discord.Embed(description="⚠️ Invalid number. Use `t!personality list` to see traits.", color=discord.Color.orange()))
            return
        removed = CUSTOM_TRAITS.pop(index - 1)
        await ctx.send(embed=discord.Embed(description=f"✅ Removed trait #{index}: \"{removed}\"", color=discord.Color.green()))
 
    @personality_group.command(name="list")
    async def personality_list(ctx):
        from personality import CUSTOM_TRAITS
        if not CUSTOM_TRAITS:
            await ctx.send(embed=discord.Embed(description="📋 No custom traits yet. Use `t!personality add <trait>`.", color=discord.Color.greyple()))
            return
        embed = discord.Embed(
            title       = "🧠 Custom Personality Traits",
            description = "\n".join(f"`{i+1}.` {trait}" for i, trait in enumerate(CUSTOM_TRAITS)),
            color       = discord.Color.blurple()
        )
        embed.set_footer(text=f"{len(CUSTOM_TRAITS)} trait(s) active")
        await ctx.send(embed=embed)
 
    @personality_group.command(name="clear")
    async def personality_clear(ctx):
        if not has_permission(ctx.author, "personality"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to clear personality traits.", color=discord.Color.red()))
            return
        from personality import CUSTOM_TRAITS
        count = len(CUSTOM_TRAITS)
        CUSTOM_TRAITS.clear()
        await ctx.send(embed=discord.Embed(description=f"✅ Cleared all {count} trait(s). Back to default me! 😊", color=discord.Color.green()))
 
    # ---- Warns ----
 
    @bot.command(name="warns")
    async def warns_cmd(ctx, member: discord.Member = None, action: str = None):
        if not member:
            await ctx.send(embed=discord.Embed(
                description="Usage: `t!warns @user` — view warns | `t!warns @user clear` — clear warns",
                color=discord.Color.orange()
            ))
            return
 
        if action and action.lower() == "clear":
            if not has_permission(ctx.author, "warn"):
                await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to clear warnings.", color=discord.Color.red()))
                return
            clear_warns(str(member.id))
            await ctx.send(embed=discord.Embed(description=f"✅ Cleared all warnings for {member.mention}.", color=discord.Color.green()))
            return
 
        warns = load_warns(str(member.id))
        if not warns:
            await ctx.send(embed=discord.Embed(description=f"✅ {member.mention} has no warnings. Clean record! 🌟", color=discord.Color.green()))
            return
        lines = []
        for i, w in enumerate(warns, 1):
            lines.append(f"`{i}.` **{w.get('reason', 'No reason')}** — by {w.get('mod', '?')} at {w.get('time', '?')}")
        embed = discord.Embed(
            title       = f"⚠️ Warnings — {member.display_name}",
            description = "\n".join(lines),
            color       = discord.Color.orange()
        )
        embed.set_footer(text=f"{len(warns)} warning(s) total")
        await ctx.send(embed=embed)
 
    # ---- Permissions ----
 
    @bot.group(name="perm", invoke_without_command=True)
    async def perm_group(ctx):
        await ctx.send(embed=discord.Embed(
            title       = "🔑 Permission Commands",
            description = (
                "`t!perm add @user <perm>` — Grant a permission\n"
                "`t!perm remove @user <perm>` — Revoke a permission\n"
                "`t!perm list [@user]` — View permissions\n\n"
                f"**Valid perms:** `{'` `'.join(sorted(VALID_PERMS))}`\n"
                "`mod` grants all permissions at once."
            ),
            color = discord.Color.blurple()
        ))
 
    @perm_group.command(name="add")
    async def perm_add(ctx, member: discord.Member, perm: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can grant permissions.", color=discord.Color.red()))
            return
        perm = perm.lower()
        if perm not in VALID_PERMS:
            await ctx.send(embed=discord.Embed(description=f"⚠️ Invalid permission. Valid: `{'` `'.join(sorted(VALID_PERMS))}`", color=discord.Color.orange()))
            return
        grant_perm(member.id, perm)
        await ctx.send(embed=discord.Embed(description=f"✅ Granted `{perm}` to {member.mention}.", color=discord.Color.green()))
 
    @perm_group.command(name="remove")
    async def perm_remove(ctx, member: discord.Member, perm: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can revoke permissions.", color=discord.Color.red()))
            return
        perm = perm.lower()
        revoke_perm(member.id, perm)
        await ctx.send(embed=discord.Embed(description=f"✅ Revoked `{perm}` from {member.mention}.", color=discord.Color.green()))
 
    @perm_group.command(name="list")
    async def perm_list(ctx, member: discord.Member = None):
        target      = member or ctx.author
        db_perms    = load_user_perms(target.id)
        role        = get_role(target)
        fam_perms   = _FAMILY_DEFAULT_PERMS.get(role, set()) if role else set()
        lines = []
        if db_perms:
            lines.append(f"**Granted:** `{'` `'.join(sorted(db_perms))}`")
        if fam_perms:
            lines.append(f"**Family defaults:** `{'` `'.join(sorted(fam_perms))}`")
        if not lines:
            lines.append("No permissions assigned.")
        embed = discord.Embed(
            title       = f"🔑 Permissions — {target.display_name}",
            description = "\n".join(lines),
            color       = discord.Color.blurple()
        )
        await ctx.send(embed=embed)
 
    # ---- General ----
 
    _WHOAMI_RESPONSES = {
        "dad":           "You're my Dad — the one who built me. 🛠️ I owe you my existence. No pressure. 😂",
        "mom":           "You're my Mom — the co-creator! 💙 Half of what I am is because of you.",
        "cousin_stelle": "You're my Cousin! 🌟 A Purple Star where everything is bubbly when I'm with you. 🎆",
        "cousin_crois":  "You're my Cousin! 🥐 A bread where everything is bubbly when I'm with you. 🥐",
        "cousin_hyu":    "You're my Cousin! 📚 A Curious cousin where everything is bubbly when I'm with you. 📑",
        "cousin_mimi":   "You're my Cousin! ❤️\u200d🩹 A Serious yet sweet cousin, everything is bubbly when I'm with you. 🖤",
        "uncle_caco":    "You're my Uncle! 🐐 The GOATED UNCLE, stay GOATED! 😎",
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
        "cousin_mimi":   "Mimi! ❤️\u200d🩹 My Serious Cousin is here! What serious topic today? 🖤",
        "uncle_caco":    "Goated Uncle! 🐐 What goated things shall we do today? 😎",
        "uncle_vari":    "Chimera Uncle! 🥖 What crazy things shall we do today? 🔥",
        "sister_abby":   "Big Sister! 🧀 What puns are we cooking today? 📜",
        "sister_kde":    "Big Sister! 🩷 What crazy thing shall we do today? 💖",
        "sister_kio":    "Sister Kio! 🩷 What crazy thing shall we do today? 💖",
        "broinlaw_haru": "Brother in law! 🖤 What crazy thing today? Except flirting with my big sister. 💢",
    }
 
    @bot.command(name="whoami")
    async def whoami(ctx):
        await ctx.send(_WHOAMI_RESPONSES.get(get_role(ctx.author), "Hello! valued member of this server! 😊 Not a creator, but still cool."))
 
    @bot.command(name="greet")
    async def greet(ctx):
        await ctx.send(_GREET_RESPONSES.get(get_role(ctx.author), "Heya! 👋 Good to see you around here!"))
 
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
        if not has_permission(ctx.author, "purge"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to purge messages.", color=discord.Color.red()))
            return
        if amount is None or not (1 <= amount <= 100):
            await ctx.send(embed=discord.Embed(description="⚠️ Please provide a number between 1 and 100. Example: `t!purge 50`", color=discord.Color.orange()))
            return
        try:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=amount)
            confirm = await ctx.send(f"🗑️ Deleted **{len(deleted)}** message(s).")
            await confirm.delete(delay=3)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="⛔ I don't have permission to delete messages here.", color=discord.Color.red()))
        except Exception as e:
            print(f"❌ Purge error: {e}")
 
    # ---- Slash: /sendmsg ----
    
    @bot.tree.command(name="sendmsg", description="Send an anonymous message to a channel as T.O.R.I.E.")
    @discord.app_commands.describe(channel="The channel to send to", message="The message to send")
    async def sendmsg(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        if not has_permission(interaction.user, "sendmsg"):
            await interaction.response.send_message("⛔ You don't have permission to use this command.", ephemeral=True)
            return
        if not message.strip():
            await interaction.response.send_message("⚠️ Message cannot be empty.", ephemeral=True)
            return
        if len(message) > 2000:
            await interaction.response.send_message("⚠️ Message is too long (max 2000 chars).", ephemeral=True)
            return
        message = message.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        try:
            await channel.send(message)
            await interaction.response.send_message(f"✅ Message sent to {channel.mention}.", ephemeral=True)
            print(f"📨 /sendmsg by {interaction.user} → #{channel.name}")
        except discord.Forbidden:
            await interaction.response.send_message(f"⛔ No permission to send in {channel.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("❌ Something went wrong.", ephemeral=True)
            print(f"❌ /sendmsg error: {e}")

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

        embed = discord.Embed(description=text, color=discord.Color.pink())
        if gif_url:
            embed.set_image(url=gif_url)
        embed.set_footer(text="T.O.R.I.E. GIFs Powered by KLIPY GIF")
        await ctx.send(embed=embed)

    @bot.command(name="hug")
    async def cmd_hug(ctx, target: discord.Member):
        await _run_interaction(ctx, target, "hug")

    @bot.command(name="kiss")
    async def cmd_kiss(ctx, target: discord.Member):
        await _run_interaction(ctx, target, "kiss")

    @bot.command(name="pat")
    async def cmd_pat(ctx, target: discord.Member):
        await _run_interaction(ctx, target, "pat")

    @bot.command(name="bite")
    async def cmd_bite(ctx, target: discord.Member):
        await _run_interaction(ctx, target, "bite")

    @bot.command(name="lick")
    async def cmd_lick(ctx, target: discord.Member):
        await _run_interaction(ctx, target, "lick")

    @bot.command(name="punch")
    async def cmd_punch(ctx, target: discord.Member):
        await _run_interaction(ctx, target, "punch")

    @bot.command(name="kick")
    async def cmd_kick(ctx, target: discord.Member):
        await _run_interaction(ctx, target, "kick")

    @bot.command(name="fuck")
    async def cmd_fuck(ctx, target: discord.Member):
        await _run_interaction(ctx, target, "fuck")

    @bot.command(name="tor")
    async def cmd_tor(ctx, action: str, target: discord.Member):
        """Catch-all shortcut: t!tor punch @user"""
        await _run_interaction(ctx, target, action.lower())