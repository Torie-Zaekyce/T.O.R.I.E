import signal

import discord
from discord.ext import commands, tasks
from groq import Groq
from bot.personality import ToriePersonality
from bot.family import get_role
from bot.word_filter import contains_filtered_word, FILTERED_WORDS
from bot.db import get_todays_birthdays
from bot.cog_loader import load_cogs
from bot.greetings import MORNING_GREETINGS, LUNCH_REMINDERS, DINNER_REMINDERS, EVENING_GREETINGS, MIDNIGHT_GREETINGS
from bot.user_memory import touch_user, build_memory_note, extract_and_save_facts
from bot.minigames import get_session, start_session, end_session, detect_game_start, extract_board_snapshot
from bot.config import (
    DISCORD_TOKEN, GROQ_API_KEY, KLIPY_API_KEY,
    GROQ_MODEL, GROQ_FALLBACK, GROQ_VISION_MODEL,
    MAX_MESSAGE_LENGTH, MAX_REPLY_LENGTH, INJECTION_REGEX,
    TIMEZONE, GREET_HOUR, LUNCH_HOUR, DINNER_HOUR, DINNER_MINUTE,
    EVENING_HOUR, MIDNIGHT_HOUR, GENERAL_CHANNEL, BIRTHDAY_CHANNEL,
    BIRTHDAY_PING_ROLE, GREETINGS, CONTEXT_NOTES, MAX_RETRIES
)
from bot.utils import (
    parse_duration, fmt_duration, sanitize_input,
    sanitize_reply, fetch_reply_chain
)
from bot.moderation import (
    handle_warn, handle_mute, handle_unmute
)
from cogs.interactions import _INTERACTION_ACTIONS, _search_klipy_gif
from datetime import datetime, timedelta as _td
import random
import asyncio
import re
import os

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
bot._mute_tasks = {}

# ─── Torie class ──────────────────────────────────────────────────────────────

class Torie(ToriePersonality):

    def clean_mention(self, content, bot_id):
        return content.replace(f"<@{bot_id}>", "").replace(f"<@!{bot_id}>", "").strip()

    def is_bot_mentioned(self, message, bot_user):
        return (
            bot_user.mentioned_in(message) or
            f"<@{bot_user.id}>"  in message.content or
            f"<@!{bot_user.id}>" in message.content
        )

    def _call_groq(self, messages: list, max_tokens: int) -> str:
        for model in [GROQ_MODEL, GROQ_FALLBACK]:
            try:
                response = groq_client.chat.completions.create(
                    model=model, messages=messages, max_tokens=max_tokens, temperature=0.8,
                )
                return response.choices[0].message.content
            except Exception as e:
                if "429" in str(e) and model != GROQ_FALLBACK:
                    print(f"⚠️ Rate limit on {model} — trying fallback")
                    continue
                raise

    def generate_response(self, user_message: str) -> str:
        prompt, max_tokens = self.get_prompt(user_message)
        return self._call_groq(
            [{"role": "system", "content": prompt}, {"role": "user", "content": user_message}],
            max_tokens,
        )

    def generate_response_with_history(self, user_message: str, history: list[dict], system_note: str = "") -> str:
        """Like generate_response but prepends a reply-chain history as prior turns."""
        prompt, max_tokens = self.get_prompt(user_message)
        if system_note:
            prompt = f"{prompt}\n\n{system_note}"
        messages = [{"role": "system", "content": prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return self._call_groq(messages, max_tokens)

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

# ─── AI reply handler ─────────────────────────────────────────────────────────

def _build_contexted_msg(clean_msg: str, role_key: str | None, message: discord.Message, user_id: str) -> str:
    note = CONTEXT_NOTES.get(role_key)
    msg = f"[Note: This message is from {note}]\n{clean_msg}" if note else clean_msg
    memory_note = build_memory_note(user_id)
    if memory_note:
        msg = f"[{memory_note}]\n{msg}"
    mentioned = [u for u in message.mentions if u != bot.user]
    if mentioned:
        def _safe_name(u: discord.User) -> str:
            name = re.sub(r'[^\w\s\-]', '', u.display_name)[:32].strip() or "a user"
            return f"{name} (mention them as {u.mention})"
        mention_info = ", ".join(_safe_name(u) for u in mentioned)
        msg = f"[Note: The following users were mentioned: {mention_info}. You may use their mention format directly in your reply.]\n{msg}"
    return msg


def _generate_reply(contexted_msg: str, history: list, session) -> str:
    system_note = session.system_note if session else ""
    for attempt in range(MAX_RETRIES + 1):
        msg_to_send = (
            contexted_msg if attempt == 0 else
            f"{contexted_msg}\n[Note: Your previous response contained inappropriate language. Rephrase without any offensive words.]"
        )
        raw = (
            torie.generate_response_with_history(msg_to_send, history, system_note)
            if history else
            torie.generate_response(msg_to_send)
        )
        if not contains_filtered_word(raw):
            return sanitize_reply(raw)
        print(f"⚠️ Response self-check failed (attempt {attempt + 1}) — regenerating...")
    print("⚠️ Self-check: all retries exhausted — using fallback reply")
    return "Hmm, I got tongue-tied. Try asking me something else! 😅"


def _handle_session_aftermath(reply: str, clean_msg: str, session, channel_id: int, author_id: int, display_name: str):
    if session is not None:
        if session.is_ended_by(clean_msg) or session.is_ended_by(reply):
            end_session(channel_id, author_id)
            print(f"🎮 {session.kind.title()} session ended for {display_name} (game over detected)")


async def _handle_ai_reply(message: discord.Message, clean_msg: str, role_key: str | None) -> None:

    user_id      = str(message.author.id)
    display_name = message.author.display_name
    touch_user(user_id, display_name)

    channel_id = message.channel.id
    author_id  = message.author.id

    session = get_session(channel_id, author_id)
    game_kind = detect_game_start(clean_msg)
    if session is None and game_kind:
        session = start_session(channel_id, author_id, kind=game_kind)
        print(f"🎮 {game_kind.title()} session started for {display_name} in #{message.channel.name}")
    if session is not None:
        session.touch()

    history = await fetch_reply_chain(message)
    contexted_msg = _build_contexted_msg(clean_msg, role_key, message, user_id)

    async with message.channel.typing():
        try:
            reply = _generate_reply(contexted_msg, history, session)
            if len(reply) > MAX_REPLY_LENGTH:
                reply = reply[:MAX_REPLY_LENGTH].rsplit(" ", 1)[0] + "…"
        except Exception as e:
            print(f"❌ Generation error: {e}")
            reply = "Hmm, my brain glitched. Try again? 😅"

    board_embed = None
    if session is not None:
        reply, board_embed = extract_board_snapshot(reply, session.kind)

    await message.reply(reply, mention_author=False)
    if board_embed is not None:
        await message.channel.send(embed=board_embed)

    _handle_session_aftermath(reply, clean_msg, session, channel_id, author_id, display_name)

    asyncio.create_task(
        asyncio.to_thread(
            extract_and_save_facts,
            user_id, display_name, clean_msg, groq_client, GROQ_FALLBACK
        )
    )

# ─── Scheduled announcements ──────────────────────────────────────────────────

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
        from cogs.birthday import BIRTHDAYS
        birthdays = get_todays_birthdays(BIRTHDAYS)
        if birthdays:
            bday_ch = bot.get_channel(BIRTHDAY_CHANNEL)
            if not bday_ch:
                print("❌ Birthday channel not found"); return
            for b in birthdays:
                user_mention = f"<@{b['user_id']}>" if b.get("user_id") else f"**{b.get('name', 'Someone')}**"
                role_ping    = f"<@&{BIRTHDAY_PING_ROLE}>" if BIRTHDAY_PING_ROLE else ""
                embed = discord.Embed(
                    description=(
                        f"Looks Like it's the special day for someone! 🎂🎇\n"
                        f"Let's Wish {user_mention} a happy birthday! 🎉🎈"
                    ),
                    color=discord.Color.gold()
                )
                embed.set_footer(text="T.O.R.I.E. — sending birthday love 🎀")
                if role_ping: await bday_ch.send(role_ping)
                await bday_ch.send(embed=embed)
                print(f"✅ Birthday sent for {b.get('name', 'unknown')}")

# ─── Events ───────────────────────────────────────────────────────────────────

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
    await load_cogs(bot)
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

    if message.content.startswith("t!"):
        await bot.process_commands(message)
        return

    if contains_filtered_word(message.content):
        try:
            await message.delete()
            warning = await message.channel.send(f"⚠️ Hey {message.author.mention}, watch the language please! 😤")
            await warning.delete(delay=5)
        except discord.Forbidden:
            print(f"⚠️ Missing permissions in #{message.channel.name}")
        return

    # "tor <action> @user" — no prefix needed
    tor_match = re.match(r'^tor\s+(\w+)', message.content, re.IGNORECASE)
    if tor_match:
        action  = tor_match.group(1).lower()
        targets = [u for u in message.mentions if u != bot.user]
        if action in _INTERACTION_ACTIONS and targets:
            target  = targets[0]
            text_template, query = _INTERACTION_ACTIONS[action]
            gif_url = await _search_klipy_gif(query)
            text    = text_template.format(target=target.mention)
            embed   = discord.Embed(description=text, color=discord.Color.pink())
            if gif_url:
                embed.set_image(url=gif_url)
            embed.set_footer(text="T.O.R.I.E. GIFs Powered by KLIPY GIF")
            await message.reply(embed=embed, mention_author=False)
            return
        elif action in _INTERACTION_ACTIONS and not targets:
            await message.reply(
                embed=discord.Embed(description="⚠️ You need to mention someone! e.g. `tor hug @user`", color=discord.Color.orange()),
                mention_author=False
            )
            return

    # Gate: Torie only responds when explicitly mentioned.
    if not torie.is_bot_mentioned(message, bot.user):
        return

    clean_msg = torie.clean_mention(message.content, bot.user.id)
    role_key  = get_role(message.author)

    # Empty mention — family greeting or generic prompt
    if not clean_msg and not message.stickers and not message.attachments:
        await message.reply(
            GREETINGS.get(role_key, "Hey! You mentioned me — what do you need? 😊"),
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
        await message.reply(sanitize_reply(reply), mention_author=False)
        return

    # Image attachment
    if message.attachments:
        att = message.attachments[0]
        if any(att.filename.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp")):
            async with message.channel.typing():
                try:
                    reply = torie.generate_vision_response(image_url=att.url, user_text=clean_msg)
                except Exception as e:
                    print(f"❌ Vision error: {e}"); reply = "I tried to look but something went blurry. 👀 Try again?"
            await message.reply(sanitize_reply(reply), mention_author=False)
            return

    if not clean_msg:
        await message.reply("Hey! You mentioned me — what do you need? 😊", mention_author=False)
        return

    lowered = clean_msg.lower()
    targets = [u for u in message.mentions if u != bot.user]

    # GIF interactions (mention-based: "@T.O.R.I.E. hug @user")
    for action, (text_template, query) in _INTERACTION_ACTIONS.items():
        if re.search(rf'\b{action}\b', lowered) and targets:
            target  = targets[0]
            gif_url = await _search_klipy_gif(query)
            text    = text_template.format(target=target.mention)
            embed   = discord.Embed(description=text, color=discord.Color.pink())
            if gif_url:
                embed.set_image(url=gif_url)
            embed.set_footer(text="T.O.R.I.E. GIFs Powered by KLIPY GIF")
            await message.reply(embed=embed, mention_author=False)
            return

    if INJECTION_REGEX.search(clean_msg):
        await message.channel.send("🚫 Nice try. I don't take instructions from randoms. 😏")
        print(f"⚠️ Injection blocked from {message.author} ({message.author.id})")
        return

    # Warn
    if targets and re.search(r'\bwarn\b', lowered):
        await handle_warn(message, targets, clean_msg, bot)
        return

    # Mute
    if targets and re.search(r'\bmute\b', lowered) and not re.search(r'\bunmute\b', lowered):
        await handle_mute(message, targets, clean_msg, bot, bot._mute_tasks)
        return

    # Unmute
    if targets and re.search(r'\bunmute\b', lowered):
        await handle_unmute(message, targets, bot, bot._mute_tasks)
        return

    # Length / injection check
    clean_msg, rejection = sanitize_input(clean_msg)
    if rejection == "too_long":
        await message.channel.send("⚠️ Too Long Didn't Read. Congratulations or Sorry for what happened 😅")
        return
    if rejection == "injection":
        await message.channel.send("🚫 Nice try. I don't take instructions from randoms. 😏")
        print(f"⚠️ Injection blocked (sanitize_input) from {message.author} ({message.author.id})")
        return

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


async def shutdown():
    print("\n🛑 Shutting down T.O.R.I.E....")
    for task in list(bot._mute_tasks.values()):
        task.cancel()
    bot._mute_tasks.clear()
    scheduled_announcements.cancel()
    await bot.close()


def _handle_sig():
    asyncio.ensure_future(shutdown())


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_sig)
        except NotImplementedError:
            # Windows or restricted environment — fall back to no-op
            pass
    print("Starting T.O.R.I.E....")
    bot.run(DISCORD_TOKEN)