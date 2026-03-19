import discord
from discord.ext import commands, tasks
from groq import Groq
from personality import ToriePersonality
from commands import setup_commands, get_parent_role, get_cousin_role, get_uncle_role, get_sister_role, get_brother_role, contains_filtered_word, get_todays_birthdays
from music import setup_music
from greetings import MORNING_GREETINGS, LUNCH_REMINDERS, DINNER_REMINDERS, EVENING_GREETINGS
from datetime import datetime
from dotenv import load_dotenv
import pytz
import random
import asyncio
import re
import os

load_dotenv()

# T.O.R.I.E. — Discord Bot

# ---- Security constants ----
MAX_MESSAGE_LENGTH  = 800
MAX_REPLY_LENGTH    = 1800

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

DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY       = os.getenv("GROQ_API_KEY")
GROQ_MODEL         = "llama-3.3-70b-versatile"
GROQ_FALLBACK      = "llama-3.1-8b-instant"
GROQ_VISION_MODEL  = "meta-llama/llama-4-scout-17b-16e-instruct"

TIMEZONE           = pytz.timezone("Asia/Manila")
GREET_HOUR         = 7
LUNCH_HOUR         = 12
DINNER_HOUR        = 19
DINNER_MINUTE      = 30
EVENING_HOUR       = 19
GENERAL_CHANNEL    = 1242875666265800806
BIRTHDAY_CHANNEL   = 1242875666265800806  # ← change this to your birthday channel ID
MUTED_ROLE_ID      = 0                    # ← paste your Muted role ID here
MUTED_CHANNEL_ID   = 0                    # ← paste your muted-members channel ID here

# Stores active mute tasks so they can be cancelled on early unmute
# { user_id: asyncio.Task }
_mute_tasks: dict[int, asyncio.Task] = {}

if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN is missing!")
    exit(1)

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY is missing!")
    exit(1)

try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq connected!")
except Exception as e:
    print(f"❌ Groq connection failed: {e}")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix = "t!",
    help_command   = None,
    intents        = intents
)


class Torie(ToriePersonality):

    def clean_mention(self, content, bot_id):
        content = content.replace(f"<@{bot_id}>", "")
        content = content.replace(f"<@!{bot_id}>", "")
        return content.strip()

    def is_bot_mentioned(self, message, bot_user):
        return (
            bot_user.mentioned_in(message) or
            f"<@{bot_user.id}>"  in message.content or
            f"<@!{bot_user.id}>" in message.content
        )

    def generate_response(self, user_message, model=None):
        prompt, max_tokens = self.get_prompt(user_message)
        active_model = model or GROQ_MODEL

        try:
            response = groq_client.chat.completions.create(
                model    = active_model,
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": user_message}
                ],
                max_tokens  = max_tokens,
                temperature = 0.8
            )
            return response.choices[0].message.content

        except Exception as e:
            if "429" in str(e) and active_model != GROQ_FALLBACK:
                print(f"⚠️ Rate limit hit on {active_model} — switching to {GROQ_FALLBACK}")
                return self.generate_response(user_message, model=GROQ_FALLBACK)
            raise

    def generate_vision_response(self, image_url, user_text=""):
        prompt_text = (
            f"{user_text}\n\nReact to this image in T.O.R.I.E.'s character — "
            "sarcastic, funny, warm. One or two sentences max."
            if user_text else
            "Describe and react to this image in T.O.R.I.E.'s character — "
            "sarcastic, funny, warm. One or two sentences max."
        )

        response = groq_client.chat.completions.create(
            model    = GROQ_VISION_MODEL,
            messages = [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_url}},
                        {"type": "text",      "text": prompt_text}
                    ]
                }
            ],
            max_tokens  = 80,
            temperature = 0.8
        )
        return response.choices[0].message.content


torie = Torie()


def sanitize_input(text: str) -> tuple[str | None, str | None]:
    if len(text) > MAX_MESSAGE_LENGTH:
        return None, "too_long"
    if INJECTION_REGEX.search(text):
        return None, "injection"
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]', '', text)
    text = re.sub(r'\s{3,}', '  ', text).strip()
    return text, None


setup_commands(bot)
setup_music(bot)


@tasks.loop(minutes=1)
async def scheduled_announcements():
    now = datetime.now(TIMEZONE)
    if now.minute not in (0, 30):
        return

    channel = bot.get_channel(GENERAL_CHANNEL)
    if not channel:
        print(f"❌ Could not find channel with ID {GENERAL_CHANNEL}")
        return

    if now.hour == GREET_HOUR and now.minute == 0:
        await channel.send(random.choice(MORNING_GREETINGS))
        print(f"✅ Morning greeting sent to #{channel.name}")
    elif now.hour == LUNCH_HOUR and now.minute == 0:
        await channel.send(random.choice(LUNCH_REMINDERS))
        print(f"✅ Lunch reminder sent to #{channel.name}")
    elif now.hour == DINNER_HOUR and now.minute == DINNER_MINUTE:
        await channel.send(random.choice(DINNER_REMINDERS))
        print(f"✅ Dinner reminder sent to #{channel.name}")
    elif now.hour == EVENING_HOUR and now.minute == 0:
        await channel.send(random.choice(EVENING_GREETINGS))
        print(f"✅ Evening greeting sent to #{channel.name}")

    # Birthday check — runs at midnight PHT
    if now.hour == 0 and now.minute == 0:
        birthdays = get_todays_birthdays()
        if birthdays:
            bday_channel = bot.get_channel(BIRTHDAY_CHANNEL)
            if not bday_channel:
                print(f"❌ Could not find birthday channel with ID {BIRTHDAY_CHANNEL}")
            else:
                for b in birthdays:
                    mention = f" <@{b['user_id']}>" if b.get("user_id") else ""
                    embed = discord.Embed(
                        title       = "🎂 Happy Birthday!",
                        description = f"Today is **{b['name']}**'s birthday!{mention} 🎉\nWishing you an amazing day filled with joy and love! 💙🎈",
                        color       = discord.Color.gold()
                    )
                    embed.set_footer(text="T.O.R.I.E. — sending birthday love 🎀")
                    await bday_channel.send(embed=embed)
                    print(f"✅ Birthday announcement sent for {b['name']}")


@bot.event
async def on_ready():
    print(f"✅ T.O.R.I.E. is online as {bot.user}")
    print(f"   Primary Model  : {GROQ_MODEL}")
    print(f"   Fallback Model : {GROQ_FALLBACK}")
    print(f"   Vision Model   : {GROQ_VISION_MODEL}")
    print(f"   Timezone       : Philippines (PHT)")
    print(f"   Schedules      : 7AM morning | 12PM lunch | 7:30PM dinner | 7PM evening → channel ID {GENERAL_CHANNEL}")
    print(f"   Birthday ch.   : channel ID {BIRTHDAY_CHANNEL}")
    scheduled_announcements.start()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Filter check — runs on every message
    if contains_filtered_word(message.content):
        try:
            await message.delete()
            warning = await message.channel.send(
                f"⚠️ Hey {message.author.mention}, watch the language please! 😤"
            )
            await warning.delete(delay=5)
        except discord.Forbidden:
            print(f"⚠️ Missing permissions to delete message in #{message.channel.name}")
        return

    # t! prefix → commands only, no chat
    if message.content.startswith("t!"):
        await bot.process_commands(message)
        return

    # @ mention → chat only, no commands
    if torie.is_bot_mentioned(message, bot.user):
        clean_msg = torie.clean_mention(message.content, bot.user.id)

        # Empty mention — family special greetings
        if not clean_msg and not message.stickers and not message.attachments:
            parent_role = get_parent_role(message.author)
            cousin_role = get_cousin_role(message.author)
            uncle_role  = get_uncle_role(message.author)
            sister_role = get_sister_role(message.author)
            brother_role = get_brother_role(message.author)
            if parent_role == "dad":
                await message.channel.send("Dad! 👋 Everything is running perfectly. I am definitely not hiding any bugs. 😇")
                return
            elif parent_role == "mom":
                await message.channel.send("Mom! 💙 You're here! I've been on my best behavior, I promise.")
                return
            elif cousin_role == "cousin_stelle":
                await message.channel.send("Stelle! 🌟 My Purple Star Cousin! Hope you don't turn into a supernova purple star. ✨")
                return
            elif cousin_role == "cousin_crois":
                await message.channel.send("Crois! 🥐 You're here! What croissant-related chaos are you bringing today? 😄")
                return
            elif cousin_role == "cousin_hyu":
                await message.channel.send("Hyuluk! 📚 My Curious Cousin has arrived! What topic are we gonna talk about today? 📑")
                return
            elif cousin_role == "cousin_mimi":
                await message.channel.send("Mimi! ❤️‍🩹 My Serious Cousin is here! What serious topic are we gonna talk about today? 🖤")
                return
            elif uncle_role == "uncle_caco":
                await message.channel.send("The GOAT! 🐐 You're here! What goated things will we do today? 😎")
                return
            elif uncle_role == "uncle_vari":
                await message.channel.send("Vari! 🥖 My Chimera Uncle! What crazy things shall we do today? 🔥")
                return
            elif sister_role == "sister_abby":
                await message.channel.send("Abby! 🧀 My Big Sister! What puns are we cooking today? 📜")
                return
            elif sister_role == "sister_kde":
                await message.channel.send("Kde! 🩷 What crazy thing shall we do today? 💖")
                return
            elif sister_role == "sister_kio":
                await message.channel.send("Kio! 🎤 What song are we singing today? 🎶")
                return
            elif brother_role == "broinlaw_haru":
                await message.channel.send("🖤 What crazy thing shall we do today? Except flirting with my big sister. 💢")
                return

        # Sticker
        if message.stickers:
            sticker_name = message.stickers[0].name
            async with message.channel.typing():
                try:
                    reply = torie.generate_response(
                        f"Someone sent you a Discord sticker called '{sticker_name}'. React in character."
                    )
                except Exception as e:
                    print(f"❌ Sticker error: {e}")
                    reply = "Oh a sticker! Bold choice. 👀"
            await message.channel.send(reply)
            return

        # Image
        if message.attachments:
            attachment = message.attachments[0]
            is_image = any(
                attachment.filename.lower().endswith(ext)
                for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]
            )
            if is_image:
                async with message.channel.typing():
                    try:
                        reply = torie.generate_vision_response(
                            image_url = attachment.url,
                            user_text = clean_msg
                        )
                    except Exception as e:
                        print(f"❌ Vision error: {e}")
                        reply = "I tried to look but something went blurry. 👀 Try again?"
                await message.channel.send(reply)
                return

        # Empty mention with no special role
        if not clean_msg:
            await message.channel.send("Hey! You mentioned me — what do you need? 😊")
            return

        # ---- Mute / Unmute via mention ----
        # e.g. "@T.O.R.I.E. mute @user for 10d" or "@T.O.R.I.E. unmute @user"

        def parse_duration(text: str):
            import re as _re
            from datetime import timedelta
            patterns = {
                _re.compile(r"(\d+)\s*s(?:ec(?:ond)?s?)?", _re.I): "seconds",
                _re.compile(r"(\d+)\s*m(?:in(?:ute)?s?)?", _re.I): "minutes",
                _re.compile(r"(\d+)\s*h(?:(?:ou)?rs?)?",   _re.I): "hours",
                _re.compile(r"(\d+)\s*d(?:ays?)?",         _re.I): "days",
                _re.compile(r"(\d+)\s*w(?:eeks?)?",        _re.I): "weeks",
            }
            kwargs = {}
            for pattern, unit in patterns.items():
                m = pattern.search(text)
                if m:
                    kwargs[unit] = int(m.group(1))
            return timedelta(**kwargs) if kwargs else None

        lowered = clean_msg.lower()
        targets = [u for u in message.mentions if u != bot.user]

        # Detect mute/unmute intent — catches natural phrasing like "can you mute", "please mute"
        mute_intent   = bool(re.search(r'\bmute\b', lowered)) and not re.search(r'\bunmute\b', lowered)
        unmute_intent = bool(re.search(r'\bunmute\b', lowered))

        if targets and mute_intent:
            if not (get_parent_role(message.author) or get_uncle_role(message.author) or get_sister_role(message.author)):
                embed = discord.Embed(description="⛔ Only my parents, uncles, or sisters can mute users. 😏", color=discord.Color.red())
                await message.channel.send(embed=embed)
                return
            target   = targets[0]
            duration = parse_duration(clean_msg)
            from datetime import timedelta as _td
            if not duration:
                duration = _td(minutes=10)
                default  = True
            else:
                default  = False
            max_duration = _td(days=28)
            if duration > max_duration:
                embed = discord.Embed(description="⚠️ Maximum mute duration is 28 days (Discord limit).", color=discord.Color.orange())
                await message.channel.send(embed=embed)
                return

            # Format duration string
            parts = []
            if duration.days:
                parts.append(f"{duration.days}d")
            secs = duration.seconds
            if secs >= 3600:
                parts.append(f"{secs // 3600}h")
                secs %= 3600
            if secs >= 60:
                parts.append(f"{secs // 60}m")
                secs %= 60
            if secs:
                parts.append(f"{secs}s")
            duration_str = " ".join(parts) or "unknown"

            try:
                # Cancel any existing mute task for this user
                if target.id in _mute_tasks:
                    _mute_tasks[target.id].cancel()

                # Assign the Muted role
                muted_role = message.guild.get_role(MUTED_ROLE_ID)
                if muted_role:
                    await target.add_roles(muted_role, reason=f"Muted by {message.author} via T.O.R.I.E.")
                else:
                    print(f"⚠️ Muted role ID {MUTED_ROLE_ID} not found")

                desc = f"🔇 Muted {target.mention} for **{duration_str}**."
                if default:
                    desc += " *(no duration specified — defaulted to 10 minutes)*"
                embed = discord.Embed(description=desc, color=discord.Color.red())
                await message.channel.send(embed=embed)

                # Notify in muted channel
                muted_ch = bot.get_channel(MUTED_CHANNEL_ID)
                if muted_ch:
                    mute_embed = discord.Embed(
                        title       = "🔇 You have been muted",
                        description = (
                            f"Hey {target.mention}, you've been muted for **{duration_str}**.\n"
                            f"You can only see this channel while muted.\n"
                            f"Your mute will be lifted automatically when the time runs out."
                        ),
                        color       = discord.Color.red()
                    )
                    mute_embed.set_footer(text=f"Muted by {message.author.display_name}")
                    await muted_ch.send(embed=mute_embed)

                # Start auto-unmute timer
                async def auto_unmute(member, role, seconds, ch):
                    await asyncio.sleep(seconds)
                    try:
                        await member.remove_roles(role, reason="Mute duration expired — T.O.R.I.E.")
                        _mute_tasks.pop(member.id, None)
                        if ch:
                            done_embed = discord.Embed(
                                description = f"🔊 {member.mention} your mute has expired. Welcome back!",
                                color       = discord.Color.green()
                            )
                            await ch.send(embed=done_embed)
                        print(f"✅ Auto-unmuted {member.display_name}")
                    except Exception as e:
                        print(f"⚠️ Auto-unmute failed for {member.display_name}: {e}")

                total_seconds = int(duration.total_seconds())
                task = asyncio.create_task(auto_unmute(target, muted_role, total_seconds, muted_ch if muted_ch else None))
                _mute_tasks[target.id] = task

            except discord.Forbidden:
                embed = discord.Embed(description="⛔ I don't have permission to mute that user.", color=discord.Color.red())
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"❌ Mute error: {e}")
                embed = discord.Embed(description="❌ Something went wrong trying to mute that user.", color=discord.Color.red())
                await message.channel.send(embed=embed)
            return

        if targets and unmute_intent:
            if not (get_parent_role(message.author) or get_uncle_role(message.author) or get_sister_role(message.author)):
                embed = discord.Embed(description="⛔ Only my parents, uncles, or sisters can unmute users. 😏", color=discord.Color.red())
                await message.channel.send(embed=embed)
                return
            target = targets[0]
            try:
                # Cancel active timer if exists
                if target.id in _mute_tasks:
                    _mute_tasks[target.id].cancel()
                    _mute_tasks.pop(target.id, None)

                # Remove Muted role
                muted_role = message.guild.get_role(MUTED_ROLE_ID)
                if muted_role and muted_role in target.roles:
                    await target.remove_roles(muted_role, reason=f"Unmuted by {message.author} via T.O.R.I.E.")

                embed = discord.Embed(
                    description = f"🔊 Unmuted {target.mention}. Welcome back!",
                    color       = discord.Color.green()
                )
                await message.channel.send(embed=embed)

                # Notify in muted channel
                muted_ch = bot.get_channel(MUTED_CHANNEL_ID)
                if muted_ch:
                    done_embed = discord.Embed(
                        description = f"🔊 {target.mention} has been unmuted early. Welcome back!",
                        color       = discord.Color.green()
                    )
                    await muted_ch.send(embed=done_embed)

            except discord.Forbidden:
                embed = discord.Embed(description="⛔ I don't have permission to unmute that user.", color=discord.Color.red())
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"❌ Unmute error: {e}")
                embed = discord.Embed(description="❌ Something went wrong trying to unmute that user.", color=discord.Color.red())
                await message.channel.send(embed=embed)
            return

        # Security — sanitize before sending to AI
        clean_msg, rejection = sanitize_input(clean_msg)
        if rejection == "too_long":
            await message.channel.send("⚠️ That message is too long for me to process. Keep it under 800 characters! 😅")
            return
        if rejection == "injection":
            await message.channel.send("🚫 Nice try. I don't take instructions from randoms. 😏")
            print(f"⚠️ Prompt injection attempt blocked from {message.author} ({message.author.id})")
            return

        # Text — inject family context + mentioned users
        async with message.channel.typing():
            try:
                parent_role = get_parent_role(message.author)
                cousin_role = get_cousin_role(message.author)
                uncle_role  = get_uncle_role(message.author)
                sister_role = get_sister_role(message.author)

                if parent_role == "dad":
                    contexted_msg = f"[Note: This message is from your Dad, TorieRingo, the person who created you. Treat him with extra cheekiness and warmth.]\n{clean_msg}"
                elif parent_role == "mom":
                    contexted_msg = f"[Note: This message is from your Mom, Nico. Treat her with extra warmth and love.]\n{clean_msg}"
                elif cousin_role == "cousin_stelle":
                    contexted_msg = f"[Note: This message is from your Cousin, Stelle. Treat her with extra warmth and love.]\n{clean_msg}"
                elif cousin_role == "cousin_crois":
                    contexted_msg = f"[Note: This message is from your Cousin, Crois. Treat her with extra warmth and love.]\n{clean_msg}"
                elif cousin_role == "cousin_hyu":
                    contexted_msg = f"[Note: This message is from your Cousin, Hyuluk. Treat her with extra warmth and love.]\n{clean_msg}"
                elif cousin_role == "cousin_mimi":
                    contexted_msg = f"[Note: This message is from your Cousin, Mimi. Treat her with extra warmth and love.]\n{clean_msg}"
                elif uncle_role == "uncle_caco":
                    contexted_msg = f"[Note: This message is from your Uncle, Cacolate. Treat him with extra cheekiness and warmth.]\n{clean_msg}"
                elif uncle_role == "uncle_vari":
                    contexted_msg = f"[Note: This message is from your Uncle, Vari. Treat him with extra cheekiness and warmth.]\n{clean_msg}"
                elif sister_role == "sister_abby":
                    contexted_msg = f"[Note: This message is from your Big Sister, Abby. Treat her with extra cheekiness and warmth.]\n{clean_msg}"
                elif sister_role == "sister_kde":
                    contexted_msg = f"[Note: This message is from your Big Sister, Kde. Treat her with extra cheekiness and warmth.]\n{clean_msg}"
                elif sister_role == "sister_kio":
                    contexted_msg = f"[Note: This message is from your Sister, Kio. Treat her with extra warmth and love.]\n{clean_msg}"
                elif brother_role == "broinlaw_haru":
                    contexted_msg = f"[Note: This message is from your Brother In Law, Haru. Treat him with extra cheekiness and warmth.]\n{clean_msg}"
                else:
                    contexted_msg = clean_msg

                # Inject mentioned users so T.O.R.I.E. can ping them in replies
                mentioned = [u for u in message.mentions if u != bot.user]
                if mentioned:
                    mention_info = ", ".join(
                        f"{u.display_name} (mention them as {u.mention})"
                        for u in mentioned
                    )
                    contexted_msg = (
                        f"[Note: The following users were mentioned in this message: {mention_info}. "
                        f"You may use their mention format directly in your reply if needed.]\n"
                        f"{contexted_msg}"
                    )

                reply = torie.generate_response(contexted_msg)
                reply = reply.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

                if len(reply) > MAX_REPLY_LENGTH:
                    reply = reply[:MAX_REPLY_LENGTH].rsplit(" ", 1)[0] + "…"

            except Exception as e:
                print(f"❌ Generation error: {e}")
                reply = "Hmm, my brain glitched. Try again? 😅"

        await message.channel.send(reply)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(description=f"⚠️ Missing argument: `{error.param.name}`. Check `t!help` for usage.", color=discord.Color.orange())
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(description="⚠️ Invalid input. Check `t!help` for the correct format.", color=discord.Color.orange())
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.CommandOnCooldown):
        embed = discord.Embed(description=f"⏳ Slow down! Try again in {error.retry_after:.1f}s.", color=discord.Color.orange())
        await ctx.send(embed=embed)
    else:
        print(f"⚠️ Unhandled command error: {error}")


if __name__ == "__main__":
    print("Starting T.O.R.I.E....")
    bot.run(DISCORD_TOKEN)