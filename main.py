import discord
from discord.ext import commands, tasks
from groq import Groq
from personality import ToriePersonality
from commands import setup_commands, get_parent_role, get_cousin_role, get_uncle_role, get_sister_role, contains_filtered_word
from music import setup_music
from greetings import MORNING_GREETINGS, LUNCH_REMINDERS, DINNER_REMINDERS, EVENING_GREETINGS
from datetime import datetime
from dotenv import load_dotenv
import pytz
import random
import os

load_dotenv()

# T.O.R.I.E. — Discord Bot

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


@bot.event
async def on_ready():
    print(f"✅ T.O.R.I.E. is online as {bot.user}")
    print(f"   Primary Model  : {GROQ_MODEL}")
    print(f"   Fallback Model : {GROQ_FALLBACK}")
    print(f"   Vision Model   : {GROQ_VISION_MODEL}")
    print(f"   Timezone       : Philippines (PHT)")
    print(f"   Schedules      : 7AM morning | 12PM lunch | 7:30PM dinner | 7PM evening → channel ID {GENERAL_CHANNEL}")
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
                    contexted_msg = f"[Note: This message is from your Mom, Nen. Treat her with extra warmth and love.]\n{clean_msg}"
                elif cousin_role == "cousin_stelle":
                    contexted_msg = f"[Note: This message is from your Cousin, Stelle. Treat her with extra warmth and love.]\n{clean_msg}"
                elif cousin_role == "cousin_crois":
                    contexted_msg = f"[Note: This message is from your Cousin, Crois. Treat her with extra warmth and love.]\n{clean_msg}"
                elif uncle_role == "uncle_caco":
                    contexted_msg = f"[Note: This message is from your Uncle, Cacolate. Treat him with extra cheekiness and warmth.]\n{clean_msg}"
                elif uncle_role == "uncle_vari":
                    contexted_msg = f"[Note: This message is from your Uncle, Vari. Treat him with extra cheekiness and warmth.]\n{clean_msg}"
                elif sister_role == "sister_abby":
                    contexted_msg = f"[Note: This message is from your Big Sister, Abby. Treat her with extra cheekiness and warmth.]\n{clean_msg}"
                elif sister_role == "sister_kde":
                    contexted_msg = f"[Note: This message is from your Big Sister, Kde. Treat her with extra cheekiness and warmth.]\n{clean_msg}"
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

                # Hard block — strip @everyone and @here no matter what the AI outputs
                reply = reply.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")

            except Exception as e:
                print(f"❌ Generation error: {e}")
                reply = "Hmm, my brain glitched. Try again? 😅"

        await message.channel.send(reply)


if __name__ == "__main__":
    print("Starting T.O.R.I.E....")
    bot.run(DISCORD_TOKEN)