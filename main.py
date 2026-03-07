import discord
from discord.ext import commands
import requests
import os

# ============================================================
#  T.O.R.I.E. — Discord Bot
#  Model: Your Fine-Tuned Mistral via Hugging Face Inference API
#  No local GPU needed — zero BSOD risk
# ============================================================

# ---- Config ----
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")       # from Railway variables
HF_TOKEN      = os.getenv("HF_TOKEN")            # from Railway variables
HF_MODEL      = "TorieRingo/torie-mistral-7b"    # your fine-tuned model

API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

SYSTEM_PROMPT = (
    "You are T.O.R.I.E., a Discord bot with a hilarious mix of sarcasm, "
    "dad jokes, and genuine warmth. You roast gently, tell terrible dad jokes "
    "proudly, and switch to a soft comforting tone when someone is struggling. "
    "You use emojis occasionally and never punch down."
)

# ---- Safety Checks ----
if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN is missing from environment variables!")
    exit(1)

if not HF_TOKEN:
    print("❌ HF_TOKEN is missing from environment variables!")
    exit(1)

print("✅ Environment variables loaded!")
print(f"✅ Using fine-tuned model: {HF_MODEL}")

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
    content = content.replace(f"<@{bot_id}>", "")    # regular mention
    content = content.replace(f"<@!{bot_id}>", "")   # nickname mention
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
    Sends message to Hugging Face Inference API.
    Your actual fine-tuned T.O.R.I.E. model runs on HF servers.
    Zero local GPU usage.
    """
    # Combine system prompt and user message into one input
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\nT.O.R.I.E.:"

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type":  "application/json"
    }

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens":  200,
            "temperature":     0.8,    # higher = more creative
            "do_sample":       True,
            "return_full_text": False  # only return new text not the prompt
        }
    }

    response = requests.post(API_URL, headers=headers, json=payload)

    # Handle model still loading — HF sometimes takes a moment on first call
    if response.status_code == 503:
        return "Give me a sec, my brain is warming up! 🧠 Try again in a moment."

    # Handle errors
    if response.status_code != 200:
        print(f"❌ HF API error {response.status_code}: {response.text}")
        return "Hmm, something went wrong on my end. Try again? 😅"

    result = response.json()

    # Extract the generated text
    if isinstance(result, list) and len(result) > 0:
        reply = result[0].get("generated_text", "").strip()

        # Clean up any leftover prompt artifacts
        if "T.O.R.I.E.:" in reply:
            reply = reply.split("T.O.R.I.E.:")[-1].strip()

        return reply if reply else "I had a thought but lost it. 😅 Try again?"

    return "🤖 Something went wrong — try again!"


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
