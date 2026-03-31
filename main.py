import discord
from discord.ext import commands, tasks
from groq import Groq
from personality import ToriePersonality
from commands import (
    setup_commands, get_parent_role, get_cousin_role, get_uncle_role,
    get_sister_role, get_brother_role, contains_filtered_word,
    get_todays_birthdays, has_permission, add_warn
)
from music import setup_music
from greetings import MORNING_GREETINGS, LUNCH_REMINDERS, DINNER_REMINDERS, EVENING_GREETINGS, MIDNIGHT_GREETINGS
from datetime import datetime, timedelta as _td
from dotenv import load_dotenv
import aiohttp
import pytz
import random
import asyncio
import re
import os

load_dotenv()

# T.O.R.I.E. — Discord Bot

# ---------------------------------------------------------------------------
# Security constants
# ---------------------------------------------------------------------------

MAX_MESSAGE_LENGTH = 800
MAX_REPLY_LENGTH   = 1800

INJECTION_PATTERNS = [
    r"ignore (all |previous |your )?(instructions|rules|prompt)",
    r"(you are|you're|act as|pretend (you are|to be)|roleplay as|simulate being)",
    r"new (instructions|prompt|system|rules|persona|personality)",
    r"disregard (your |all )?(previous |prior )?(instructions|rules|training)",
    r"(developer|debug|admin|god|jailbreak|dan|do anything now) mode",
    r"override (your |the )?(system|instructions|rules|prompt)",
    r"forget (everything|all|your|the) (you know|instructions|rules|training)",
    r"from now on (you (are|will|must|should)|ignore|disregard)",
    r"\[system\]|\[instructions?\]|\[prompt\]|\[admin\]",
    r"(respond|reply|answer|speak|talk) (only|exclusively|solely) in",
]
INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DISCORD_TOKEN     = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
KLIPY_API_KEY     = os.getenv("KLIPY_API_KEY")
GROQ_MODEL        = "llama-3.3-70b-versatile"
GROQ_FALLBACK     = "llama-3.1-8b-instant"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

TIMEZONE           = pytz.timezone("Asia/Manila")
GREET_HOUR         = 7
LUNCH_HOUR         = 12
DINNER_HOUR        = 19
DINNER_MINUTE      = 30
EVENING_HOUR       = 19
MIDNIGHT_HOUR      = 0
GENERAL_CHANNEL    = 1242875666265800806
BIRTHDAY_CHANNEL   = 1449335277880348733
BIRTHDAY_PING_ROLE = 1242887610586628166
MUTED_ROLE_ID      = 1447475985988587661
MUTED_CHANNEL_ID   = 1447475213842251796

_mute_tasks: dict[int, asyncio.Task] = {}

if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN is missing!"); exit(1)
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY is missing!"); exit(1)

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq connected!")
except Exception as e:
    print(f"❌ Groq connection failed: {e}"); exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="t!", help_command=None, intents=intents)

# ---------------------------------------------------------------------------
# Family greeting / context dicts
# ---------------------------------------------------------------------------

_GREETINGS: dict[str, str] = {
    "dad":           "Dad! 👋 Everything is running perfectly. I am definitely not hiding any bugs. 😇",
    "mom":           "Mom! 💙 You're here! I've been on my best behavior, I promise.",
    "cousin_stelle": "Stelle! 🌟 My Purple Star Cousin! Hope you don't turn into a supernova. ✨",
    "cousin_crois":  "Crois! 🥐 You're here! What croissant-related chaos are you bringing today? 😄",
    "cousin_hyu":    "Hyuluk! 📚 My Curious Cousin has arrived! What topic are we talking about today? 📑",
    "cousin_mimi":   "Mimi! ❤️\u200d🩹 My Serious Cousin is here! What serious topic today? 🖤",
    "uncle_caco":    "The GOAT! 🐐 You're here! What goated things will we do today? 😎",
    "uncle_vari":    "Vari! 🥖 My Chimera Uncle! What crazy things shall we do today? 🔥",
    "sister_abby":   "Abby! 🧀 My Big Sister! What puns are we cooking today? 📜",
    "sister_kde":    "Kde! 🩷 What crazy thing shall we do today? 💖",
    "sister_kio":    "Kio! 🎤 What song are we singing today? 🎶",
    "broinlaw_haru": "Haru! 🖤 What crazy thing today? Except flirting with my big sister. 💢",
}

_CONTEXT_NOTES: dict[str, str] = {
    "dad":           "your Dad, TorieRingo, the person who created you. Treat him with extra cheekiness and warmth.",
    "mom":           "your Mom, Nico. Treat her with extra warmth and love.",
    "cousin_stelle": "your Cousin, Stelle. Treat her with extra warmth and love.",
    "cousin_crois":  "your Cousin, Crois. Treat her with extra warmth and love.",
    "cousin_hyu":    "your Cousin, Hyuluk. Treat her with extra warmth and love.",
    "cousin_mimi":   "your Cousin, Mimi. Treat her with extra warmth and love.",
    "uncle_caco":    "your Uncle, Cacolate. Treat him with extra cheekiness and warmth.",
    "uncle_vari":    "your Uncle, Vari. Treat him with extra cheekiness and warmth.",
    "sister_abby":   "your Big Sister, Abby. Treat her with extra cheekiness and warmth.",
    "sister_kde":    "your Big Sister, Kde. Treat her with extra cheekiness and warmth.",
    "sister_kio":    "your Sister, Kio. Treat her with extra warmth and love.",
    "broinlaw_haru": "your Brother In Law, Haru. Treat him with extra cheekiness and warmth.",
}

# ---------------------------------------------------------------------------
# Miku GIF interactions
# ---------------------------------------------------------------------------

_INTERACTION_ACTIONS: dict[str, tuple[str, str]] = {
    "hug":  ("*gives {target} a warm hug! 🤗*",    "miku hug anime"),
    "kiss": ("*gives {target} a little kiss! 💋*",  "miku kiss anime"),
    "pat":  ("*pats {target} on the head! 🥺*",     "miku pat anime"),
    "bite": ("*playfully bites {target}! 😈*",       "miku bite anime"),
    "lick": ("*licks {target} like a weirdo! 👅*",  "miku lick anime"),
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
    if not KLIPY_API_KEY:
        print("⚠️ KLIPY_API_KEY not set — GIF search disabled")
        return None
    try:
        url = f"https://api.klipy.com/api/v1/{KLIPY_API_KEY}/gifs/search"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params={"q": query, "limit": 20}) as resp:
                if resp.status != 200:
                    print(f"⚠️ Klipy GIF search returned HTTP {resp.status}")
                    return None
                data    = await resp.json()
                results = data.get("data", [])
                if not results:
                    return None
                item = random.choice(results)
                return item["media"]["gif"]["url"]
    except Exception as e:
        print(f"⚠️ Klipy GIF search error: {e}")
        return None

# ---------------------------------------------------------------------------
# Duration parser + helpers
# ---------------------------------------------------------------------------

_DURATION_PATTERNS = [
    (re.compile(r"(\d+)\s*s(?:ec(?:ond)?s?)?", re.I), "seconds"),
    (re.compile(r"(\d+)\s*m(?:in(?:ute)?s?)?",  re.I), "minutes"),
    (re.compile(r"(\d+)\s*h(?:(?:ou)?rs?)?",    re.I), "hours"),
    (re.compile(r"(\d+)\s*d(?:ays?)?",          re.I), "days"),
    (re.compile(r"(\d+)\s*w(?:eeks?)?",         re.I), "weeks"),
]

def parse_duration(text: str) -> _td | None:
    kwargs = {}
    for pattern, unit in _DURATION_PATTERNS:
        m = pattern.search(text)
        if m: kwargs[unit] = int(m.group(1))
    return _td(**kwargs) if kwargs else None

def _fmt_duration(d: _td) -> str:
    parts, secs = [], d.seconds
    if d.days:       parts.append(f"{d.days}d")
    if secs >= 3600: parts.append(f"{secs // 3600}h"); secs %= 3600
    if secs >= 60:   parts.append(f"{secs // 60}m");   secs %= 60
    if secs:         parts.append(f"{secs}s")
    return " ".join(parts) or "unknown"

def _get_role_key(user) -> str | None:
    from commands import get_role
    return get_role(user)

def sanitize_input(text: str) -> tuple[str | None, str | None]:
    if len(text) > MAX_MESSAGE_LENGTH:
        return None, "too_long"
    if INJECTION_REGEX.search(text):
        return None, "injection"
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]', '', text)
    text = re.sub(r'\s{3,}', '  ', text).strip()
    return text, None

def _sanitize_reply(text: str) -> str:
    return text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

# ---------------------------------------------------------------------------
# Torie class
# ---------------------------------------------------------------------------

class Torie(ToriePersonality):

    def clean_mention(self, content, bot_id):
        return content.replace(f"<@{bot_id}>", "").replace(f"<@!{bot_id}>", "").strip()

    def is_bot_mentioned(self, message, bot_user):
        return (
            bot_user.mentioned_in(message) or
            f"<@{bot_user.id}>"  in message.content or
            f"<@!{bot_user.id}>" in message.content
        )

    def generate_response(self, user_message: str) -> str:
        prompt, max_tokens = self.get_prompt(user_message)
        for model in [GROQ_MODEL, GROQ_FALLBACK]:
            try:
                response = groq_client.chat.completions.create(
                    model    = model,
                    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": user_message}],
                    max_tokens=max_tokens, temperature=0.8,
                )
                return response.choices[0].message.content
            except Exception as e:
                if "429" in str(e) and model != GROQ_FALLBACK:
                    print(f"⚠️ Rate limit on {model} — trying fallback")
                    continue
                raise

    def generate_vision_response(self, image_url: str, user_text: str = "") -> str:
        prompt_text = (
            f"{user_text}\n\nReact to this image in T.O.R.I.E.'s character — sarcastic, funny, warm. One or two sentences max."
            if user_text else
            "Describe and react to this image in T.O.R.I.E.'s character — sarcastic, funny, warm. One or two sentences max."
        )
        response = groq_client.chat.completions.create(
            model    = GROQ_VISION_MODEL,
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text",      "text": prompt_text},
                ]},
            ],
            max_tokens=80, temperature=0.8,
        )
        return response.choices[0].message.content


torie = Torie()

# ---------------------------------------------------------------------------
# Moderation handlers
# ---------------------------------------------------------------------------

async def _handle_warn(message: discord.Message, targets: list, clean_msg: str) -> None:
    if not has_permission(message.author, "warn"):
        await message.channel.send(embed=discord.Embed(
            description="⛔ You don't have permission to warn users.", color=discord.Color.red()
        ))
        return

    target = targets[0]
    reason = re.sub(r'<@!?\d+>', '', clean_msg)
    reason = re.sub(r'\bwarn\b', '', reason, flags=re.I).strip() or "No reason provided"
    warn_count = add_warn(str(target.id), reason, message.author.display_name)

    await message.channel.send(embed=discord.Embed(
        title       = "⚠️ User Warned",
        description = (
            f"{target.mention} has been warned!\n"
            f"**Reason:** {reason}\n"
            f"**Total warnings:** {warn_count}\n"
            f"Auto-muted for **10 minutes**."
        ),
        color = discord.Color.orange()
    ))

    muted_role = message.guild.get_role(MUTED_ROLE_ID)
    muted_ch   = bot.get_channel(MUTED_CHANNEL_ID)
    if muted_role:
        try:
            if target.id in _mute_tasks:
                _mute_tasks[target.id].cancel()
            await target.add_roles(muted_role, reason=f"Warned by {message.author} — auto-mute")
            if muted_ch:
                warn_embed = discord.Embed(
                    title       = "⚠️ You have been warned and muted",
                    description = (
                        f"Hey {target.mention}, you've been warned!\n"
                        f"**Reason:** {reason}\n"
                        f"**Total warnings:** {warn_count}\n"
                        f"You are automatically muted for **10 minutes**."
                    ),
                    color = discord.Color.orange()
                )
                warn_embed.set_footer(text=f"Warned by {message.author.display_name}")
                warn_msg = await muted_ch.send(embed=warn_embed)
                await warn_msg.delete(delay=180)
            task = asyncio.create_task(_auto_unmute(target, muted_role, 600, muted_ch))
            _mute_tasks[target.id] = task
        except discord.Forbidden:
            pass


async def _handle_mute(message: discord.Message, targets: list, clean_msg: str) -> None:
    if not has_permission(message.author, "mute"):
        await message.channel.send(embed=discord.Embed(
            description="⛔ You don't have permission to mute users.", color=discord.Color.red()
        ))
        return

    target   = targets[0]
    duration = parse_duration(clean_msg) or _td(minutes=10)
    default  = not parse_duration(clean_msg)

    if duration > _td(days=28):
        await message.channel.send(embed=discord.Embed(
            description="⚠️ Maximum mute duration is 28 days.", color=discord.Color.orange()
        ))
        return

    duration_str = _fmt_duration(duration)
    try:
        if target.id in _mute_tasks:
            _mute_tasks[target.id].cancel()

        muted_role = message.guild.get_role(MUTED_ROLE_ID)
        if muted_role:
            await target.add_roles(muted_role, reason=f"Muted by {message.author} via T.O.R.I.E.")
        else:
            print(f"⚠️ Muted role ID {MUTED_ROLE_ID} not found")

        desc = f"🔇 Muted {target.mention} for **{duration_str}**."
        if default: desc += " *(no duration specified — defaulted to 10 minutes)*"
        await message.channel.send(embed=discord.Embed(description=desc, color=discord.Color.red()))

        muted_ch = bot.get_channel(MUTED_CHANNEL_ID)
        if muted_ch:
            mute_embed = discord.Embed(
                title       = "🔇 You have been muted",
                description = (
                    f"Hey {target.mention}, you've been muted for **{duration_str}**.\n"
                    f"You can only see this channel while muted.\n"
                    f"Your mute will be lifted automatically when the time runs out."
                ),
                color = discord.Color.red()
            )
            mute_embed.set_footer(text=f"Muted by {message.author.display_name}")
            mute_msg = await muted_ch.send(embed=mute_embed)
            await mute_msg.delete(delay=180)

        task = asyncio.create_task(_auto_unmute(target, muted_role, int(duration.total_seconds()), muted_ch))
        _mute_tasks[target.id] = task

    except discord.Forbidden:
        await message.channel.send(embed=discord.Embed(
            description="⛔ I don't have permission to mute that user.", color=discord.Color.red()
        ))
    except Exception as e:
        print(f"❌ Mute error: {e}")


async def _auto_unmute(member: discord.Member, role, seconds: int, muted_ch) -> None:
    await asyncio.sleep(seconds)
    try:
        await member.remove_roles(role, reason="Mute duration expired — T.O.R.I.E.")
        _mute_tasks.pop(member.id, None)
        if muted_ch:
            done_msg = await muted_ch.send(embed=discord.Embed(
                description=f"🔊 {member.mention} your mute has expired. You can now chat again!",
                color=discord.Color.green()
            ))
            await done_msg.delete(delay=180)
        gen_ch = bot.get_channel(GENERAL_CHANNEL)
        if gen_ch:
            gen_embed = discord.Embed(
                description=f"🔊 {member.mention} has been unmuted and is back in the server!",
                color=discord.Color.green()
            )
            gen_embed.set_footer(text="T.O.R.I.E. — mute timer expired")
            await gen_ch.send(embed=gen_embed)
        print(f"✅ Auto-unmuted {member.display_name}")
    except Exception as e:
        print(f"⚠️ Auto-unmute failed for {member.display_name}: {e}")


async def _handle_unmute(message: discord.Message, targets: list) -> None:
    if not has_permission(message.author, "unmute"):
        await message.channel.send(embed=discord.Embed(
            description="⛔ You don't have permission to unmute users.", color=discord.Color.red()
        ))
        return
    target = targets[0]
    try:
        if target.id in _mute_tasks:
            _mute_tasks[target.id].cancel()
            _mute_tasks.pop(target.id, None)
        muted_role = message.guild.get_role(MUTED_ROLE_ID)
        if muted_role and muted_role in target.roles:
            await target.remove_roles(muted_role, reason=f"Unmuted by {message.author} via T.O.R.I.E.")
        await message.channel.send(embed=discord.Embed(
            description=f"🔊 Unmuted {target.mention}. Welcome back!", color=discord.Color.green()
        ))
        muted_ch = bot.get_channel(MUTED_CHANNEL_ID)
        if muted_ch:
            done_msg = await muted_ch.send(embed=discord.Embed(
                description=f"🔊 {target.mention} has been unmuted early. Welcome back!", color=discord.Color.green()
            ))
            await done_msg.delete(delay=180)
    except discord.Forbidden:
        await message.channel.send(embed=discord.Embed(
            description="⛔ I don't have permission to unmute that user.", color=discord.Color.red()
        ))
    except Exception as e:
        print(f"❌ Unmute error: {e}")


async def _handle_ai_reply(message: discord.Message, clean_msg: str, role_key: str | None) -> None:
    async with message.channel.typing():
        try:
            note = _CONTEXT_NOTES.get(role_key)
            contexted_msg = f"[Note: This message is from {note}]\n{clean_msg}" if note else clean_msg
            mentioned = [u for u in message.mentions if u != bot.user]
            if mentioned:
                mention_info  = ", ".join(f"{u.display_name} (mention them as {u.mention})" for u in mentioned)
                contexted_msg = (
                    f"[Note: The following users were mentioned: {mention_info}. "
                    f"You may use their mention format directly in your reply.]\n{contexted_msg}"
                )
            reply = _sanitize_reply(torie.generate_response(contexted_msg))
            if len(reply) > MAX_REPLY_LENGTH:
                reply = reply[:MAX_REPLY_LENGTH].rsplit(" ", 1)[0] + "…"
        except Exception as e:
            print(f"❌ Generation error: {e}")
            reply = "Hmm, my brain glitched. Try again? 😅"
    await message.reply(reply, mention_author=False)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

setup_commands(bot)
setup_music(bot)

# ---------------------------------------------------------------------------
# Scheduled announcements
# ---------------------------------------------------------------------------

@tasks.loop(minutes=1)
async def scheduled_announcements():
    now = datetime.now(TIMEZONE)
    if now.minute not in (0, 30):
        return
    channel = bot.get_channel(GENERAL_CHANNEL)
    if not channel:
        print(f"❌ Could not find channel with ID {GENERAL_CHANNEL}"); return

    if now.hour == GREET_HOUR    and now.minute == 0:
        await channel.send(random.choice(MORNING_GREETINGS));  print("✅ Morning greeting sent")
    elif now.hour == LUNCH_HOUR  and now.minute == 0:
        await channel.send(random.choice(LUNCH_REMINDERS));    print("✅ Lunch reminder sent")
    elif now.hour == DINNER_HOUR and now.minute == DINNER_MINUTE:
        await channel.send(random.choice(DINNER_REMINDERS));   print("✅ Dinner reminder sent")
    elif now.hour == EVENING_HOUR and now.minute == 0:
        await channel.send(random.choice(EVENING_GREETINGS));  print("✅ Evening greeting sent")
    elif now.hour == MIDNIGHT_HOUR and now.minute == 0:
        await channel.send(random.choice(MIDNIGHT_GREETINGS)); print("✅ Midnight greeting sent")

    if now.hour == 0 and now.minute == 0:
        birthdays = get_todays_birthdays()
        if birthdays:
            bday_ch = bot.get_channel(BIRTHDAY_CHANNEL)
            if not bday_ch:
                print("❌ Birthday channel not found"); return
            for b in birthdays:
                user_mention = f"<@{b['user_id']}>" if b.get("user_id") else f"**{b.get('name', 'Someone')}**"
                role_ping    = f"<@&{BIRTHDAY_PING_ROLE}>" if BIRTHDAY_PING_ROLE else ""
                embed = discord.Embed(
                    description=(
                        f"𝑰𝒕'𝒔 𝒂 𝒔𝒕𝒂𝒓'𝒔 𝒔𝒑𝒆𝒄𝒊𝒂𝒍 𝒅𝒂𝒚 𝒕𝒐𝒅𝒂𝒚 🎂❤️\n"
                        f"𝑾𝒊𝒔𝒉 {user_mention} 𝒂 𝒉𝒂𝒑𝒑𝒚 𝒃𝒊𝒓𝒕𝒉𝒅𝒂𝒚! 🎉🎈"
                    ),
                    color=discord.Color.gold()
                )
                embed.set_footer(text="T.O.R.I.E. — sending birthday love 🎀")
                if role_ping: await bday_ch.send(role_ping)
                await bday_ch.send(embed=embed)
                print(f"✅ Birthday sent for {b.get('name', 'unknown')}")

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f"✅ T.O.R.I.E. is online as {bot.user}")
    print(f"   Primary Model  : {GROQ_MODEL}")
    print(f"   Fallback Model : {GROQ_FALLBACK}")
    print(f"   Vision Model   : {GROQ_VISION_MODEL}")
    print(f"   Klipy GIFs     : {'✅ enabled' if KLIPY_API_KEY else '⚠️ KLIPY_API_KEY not set'}")
    print(f"   Timezone       : Philippines (PHT)")
    print(f"   Schedules      : 7AM | 12PM | 7PM | 7:30PM | midnight → {GENERAL_CHANNEL}")
    print(f"   Birthday ch.   : {BIRTHDAY_CHANNEL}")
    try:
        synced = await bot.tree.sync()
        print(f"   Slash commands : {len(synced)} synced")
    except Exception as e:
        print(f"⚠️ Slash command sync failed: {e}")
    scheduled_announcements.start()


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if contains_filtered_word(message.content):
        try:
            await message.delete()
            warning = await message.channel.send(f"⚠️ Hey {message.author.mention}, watch the language please! 😤")
            await warning.delete(delay=5)
        except discord.Forbidden:
            print(f"⚠️ Missing permissions in #{message.channel.name}")
        return

    if message.content.startswith("t!"):
        await bot.process_commands(message)
        return

    if not torie.is_bot_mentioned(message, bot.user):
        return

    clean_msg = torie.clean_mention(message.content, bot.user.id)
    role_key  = _get_role_key(message.author)

    # Empty mention — family greeting
    if not clean_msg and not message.stickers and not message.attachments:
        await message.reply(
            _GREETINGS.get(role_key, "Hey! You mentioned me — what do you need? 😊"),
            mention_author=False
        )
        return

    # Sticker
    if message.stickers:
        async with message.channel.typing():
            try:
                reply = torie.generate_response(f"Someone sent you a Discord sticker called '{message.stickers[0].name}'. React in character.")
            except Exception as e:
                print(f"❌ Sticker error: {e}"); reply = "Oh a sticker! Bold choice. 👀"
        await message.reply(_sanitize_reply(reply), mention_author=False)
        return

    # Image
    if message.attachments:
        att = message.attachments[0]
        if any(att.filename.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp")):
            async with message.channel.typing():
                try:
                    reply = torie.generate_vision_response(image_url=att.url, user_text=clean_msg)
                except Exception as e:
                    print(f"❌ Vision error: {e}"); reply = "I tried to look but something went blurry. 👀 Try again?"
            await message.reply(_sanitize_reply(reply), mention_author=False)
            return

    if not clean_msg:
        await message.reply("Hey! You mentioned me — what do you need? 😊", mention_author=False)
        return

    lowered = clean_msg.lower()
    targets = [u for u in message.mentions if u != bot.user]

    # ── GIF interactions ──────────────────────────────────────────────────
    for action, (text_template, query) in _INTERACTION_ACTIONS.items():
        if re.search(rf'\b{action}\b', lowered) and targets:
            target  = targets[0]
            gif_url = await _search_klipy_gif(query)
            text    = text_template.format(target=target.mention)
            content = f"{text}\n{gif_url}" if gif_url else text
            await message.reply(content, mention_author=False)
            return

    # ── Warn ──────────────────────────────────────────────────────────────
    if targets and re.search(r'\bwarn\b', lowered):
        await _handle_warn(message, targets, clean_msg)
        return

    # ── Mute ─────────────────────────────────────────────────────────────
    if targets and re.search(r'\bmute\b', lowered) and not re.search(r'\bunmute\b', lowered):
        await _handle_mute(message, targets, clean_msg)
        return

    # ── Unmute ───────────────────────────────────────────────────────────
    if targets and re.search(r'\bunmute\b', lowered):
        await _handle_unmute(message, targets)
        return

    # ── Security ─────────────────────────────────────────────────────────
    clean_msg, rejection = sanitize_input(clean_msg)
    if rejection == "too_long":
        await message.channel.send("⚠️ Too Long Didn't Read. Congratulations or Sorry for what happened 😅")
        return
    if rejection == "injection":
        await message.channel.send("🚫 Nice try. I don't take instructions from randoms. 😏")
        print(f"⚠️ Injection blocked from {message.author} ({message.author.id})")
        return

    # ── AI reply ─────────────────────────────────────────────────────────
    await _handle_ai_reply(message, clean_msg, role_key)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(description=f"⚠️ Missing argument: `{error.param.name}`. Check `t!help`.", color=discord.Color.orange()))
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=discord.Embed(description="⚠️ Invalid input. Check `t!help` for the correct format.", color=discord.Color.orange()))
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=discord.Embed(description=f"⏳ Slow down! Try again in {error.retry_after:.1f}s.", color=discord.Color.orange()))
    else:
        print(f"⚠️ Unhandled command error: {error}")


if __name__ == "__main__":
    print("Starting T.O.R.I.E....")
    bot.run(DISCORD_TOKEN)