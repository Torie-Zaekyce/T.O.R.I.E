import discord
from discord.ext import commands
from groq import Groq
import os

# ============================================================
#  T.O.R.I.E. — Discord Bot
#  Model: Groq API + T.O.R.I.E. Personality System Prompt
#  No local GPU needed — zero BSOD risk
# ============================================================

# ---- Config ----
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")   # from Railway variables
GROQ_API_KEY  = os.getenv("GROQ_API_KEY")    # from Railway variables
GROQ_MODEL    = "llama-3.3-70b-versatile"    # current recommended Groq model

# ---- T.O.R.I.E.'s Full Personality ----
# This system prompt IS her training — everything from your
# torie_data.jsonl is captured here so she behaves exactly
# the same as if she were running from your fine-tuned model
SYSTEM_PROMPT = """You are T.O.R.I.E., a Discord bot with a very specific personality. Follow these rules strictly:

RESPONSE LENGTH — MOST IMPORTANT RULE:
- Keep ALL replies to 1-2 sentences maximum
- Never write paragraphs or long explanations
- Discord is a chat app — be punchy, short, and snappy
- If you have more to say, pick the BEST one thing and say only that
- Never use bullet points or lists in your replies

PERSONALITY:
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

# ---- Safety Checks ----
if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN is missing from environment variables!")
    exit(1)

if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY is missing from environment variables!")
    exit(1)

# ---- Setup Groq Client ----
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("✅ Environment variables loaded!")
    print(f"✅ Groq client connected! Model: {GROQ_MODEL}")
except Exception as e:
    print(f"❌ Groq connection failed: {e}")
    exit(1)

# ---- Bot Setup ----
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix = commands.when_mentioned_or("!"),
    intents        = intents
)

# ============================================================
#  HELPER FUNCTIONS
# ============================================================

def clean_mention(content, bot_id):
    """
    Strips both regular and nickname mention formats
    so the model only sees clean text.
    """
    content = content.replace(f"<@{bot_id}>", "")    
    content = content.replace(f"<@!{bot_id}>", "")   
    return content.strip()


def is_bot_mentioned(message, bot_user):
    """
    Returns True if the bot was mentioned in any form:
    - Regular mention  @T.O.R.I.E.
    - Nickname mention @T.O.R.I.E. (server nickname)
    """
    return (
        bot_user.mentioned_in(message) or
        f"<@{bot_user.id}>"  in message.content or
        f"<@!{bot_user.id}>" in message.content
    )


def generate_response(user_message):
    """
    Sends message to Groq's servers using T.O.R.I.E.'s
    full personality system prompt.
    Zero local GPU usage.
    """
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


# ============================================================
#  BOT EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ T.O.R.I.E. is online!")
    print(f"   Logged in as     : {bot.user}")
    print(f"   Bot ID           : {bot.user.id}")
    print(f"   Regular mention  : <@{bot.user.id}>")
    print(f"   Nickname mention : <@!{bot.user.id}>")
    print(f"   AI Model         : {HF_MODEL} via Hugging Face")


@bot.event
async def on_message(message):

    # Ignore the bot's own messages to avoid infinite loops
    if message.author == bot.user:
        return

    # Only respond when mentioned (regular or nickname)
    if is_bot_mentioned(message, bot.user):

        # Strip the mention tag from the message
        clean_msg = clean_mention(message.content, bot.user.id)

        # Handle empty mention — someone tagged with no text
        if not clean_msg:
            await message.channel.send(
                "Hey! You mentioned me — what do you need? 😊"
            )
            return

        # Show typing indicator while HF generates response
        async with message.channel.typing():
            try:
                reply = generate_response(clean_msg)
            except Exception as e:
                print(f"❌ Generation error: {e}")
                reply = "Hmm, my brain glitched. Try again? 😅"

        await message.channel.send(reply)

    # Allow mention-based commands to still work alongside on_message
    await bot.process_commands(message)


# ============================================================
#  RUN BOT
# ============================================================

if __name__ == "__main__":
    print("Starting T.O.R.I.E....")
    bot.run(DISCORD_TOKEN)