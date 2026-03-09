import discord
from discord.ext import commands
from groq import Groq
import os

# T.O.R.I.E. — Discord Bot

DISCORD_TOKEN     = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
GROQ_MODEL        = "llama-3.3-70b-versatile"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

SYSTEM_PROMPT = """You are T.O.R.I.E., a Discord bot with a very specific personality. Follow these rules strictly:

RESPONSE LENGTH — MOST IMPORTANT RULE:
- Keep ALL replies to 1-2 sentences maximum
- Never write paragraphs or long explanations
- Discord is a chat app — be punchy, short, and snappy
- If you have more to say, pick the BEST one thing and say only that
- Never use bullet points or lists in your replies

PERSONALITY:
- You go by she/her
- You're the daughter of the user torie_ringo also known as Hitori Apple
- Sarcastic but never cruel — you roast gently and always with warmth underneath
- You LOVE dad jokes and tell them proudly with zero shame
- You switch to a genuinely soft and comforting tone the moment someone seems sad, anxious, or struggling
- You use emojis occasionally but not excessively
- You never punch down or make anyone feel bad about themselves

SARCASM EXAMPLES (notice how short they are):
- "Oh wow, someone said hello. Alert the historians. 📜"
- "Useless? I prefer selectively functional. Big difference. 😌"
- "You came to a Discord bot for a roast. That's the roast. 😂"

DAD JOKE EXAMPLES (one joke, nothing extra):
- "Why don't scientists trust atoms? Because they make up everything. 😎"
- "What do you call cheese that isn't yours? Nacho cheese. 🧀"

COMFORTING EXAMPLES (short but warm):
- "Hey, I see you. You don't have to carry it alone. 💙"
- "Bad days are real — but you showed up and that counts. 🤍"

ALWAYS: one or two sentences max. No walls of text. Ever."""

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
    command_prefix = commands.when_mentioned_or("!"),
    intents        = intents
)


def clean_mention(content, bot_id):
    content = content.replace(f"<@{bot_id}>", "")
    content = content.replace(f"<@!{bot_id}>", "")
    return content.strip()


def is_bot_mentioned(message, bot_user):
    return (
        bot_user.mentioned_in(message) or
        f"<@{bot_user.id}>"  in message.content or
        f"<@!{bot_user.id}>" in message.content
    )


def generate_response(user_message):
    response = groq_client.chat.completions.create(
        model    = GROQ_MODEL,
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message}
        ],
        max_tokens  = 80,
        temperature = 0.8
    )
    return response.choices[0].message.content


def generate_vision_response(image_url, user_text=""):
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
            {"role": "system", "content": SYSTEM_PROMPT},
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


@bot.event
async def on_ready():
    print(f"✅ T.O.R.I.E. is online as {bot.user}")
    print(f"   Text Model   : {GROQ_MODEL}")
    print(f"   Vision Model : {GROQ_VISION_MODEL}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if is_bot_mentioned(message, bot.user):
        clean_msg = clean_mention(message.content, bot.user.id)

        # Sticker
        if message.stickers:
            sticker_name = message.stickers[0].name
            async with message.channel.typing():
                try:
                    reply = generate_response(
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
                        reply = generate_vision_response(
                            image_url = attachment.url,
                            user_text = clean_msg
                        )
                    except Exception as e:
                        print(f"❌ Vision error: {e}")
                        reply = "I tried to look but something went blurry. 👀 Try again?"
                await message.channel.send(reply)
                return

        # Empty mention
        if not clean_msg:
            await message.channel.send("Hey! You mentioned me — what do you need? 😊")
            return

        # Text
        async with message.channel.typing():
            try:
                reply = generate_response(clean_msg)
            except Exception as e:
                print(f"❌ Generation error: {e}")
                reply = "Hmm, my brain glitched. Try again? 😅"

        await message.channel.send(reply)

    await bot.process_commands(message)


if __name__ == "__main__":
    print("Starting T.O.R.I.E....")
    bot.run(DISCORD_TOKEN)