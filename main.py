import discord
from discord.ext import commands
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# ============================================================
#  T.O.R.I.E. — Discord Bot
#  Model: Fine-Tuned Mistral 7B (Hugging Face)
# ============================================================

# ---- Config ----
HF_MODEL       = "TorieRingo/torie-mistral-7b"  
DISCORD_TOKEN  = "DiscordToken"  
SYSTEM_PROMPT  = (
    "You are T.O.R.I.E., a Discord bot with a hilarious mix of sarcasm, "
    "dad jokes, and genuine warmth. You roast gently, tell terrible dad jokes "
    "proudly, and switch to a soft comforting tone when someone is struggling. "
    "You use emojis occasionally and never punch down."
)

# ---- Load Model ----
print("Loading T.O.R.I.E. model from Hugging Face...")
print(f"Repo: {HF_MODEL}")

try:
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        HF_MODEL,
        trust_remote_code = True     
    )

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        HF_MODEL,
        dtype             = torch.float16,   
        device_map        = "auto",
        trust_remote_code = True     
    )

    print("✅ T.O.R.I.E. model loaded successfully!")

except Exception as e:
    print(f"❌ Failed to load model: {e}")
    print("Make sure your Hugging Face repo has a valid config.json")
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
    Passes the user message through the fine-tuned
    Mistral model and returns T.O.R.I.E.'s reply.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_message}
    ]

    # Format for Mistral's chat template
    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors        = "pt",
        add_generation_prompt = True
    ).to(model.device)

    # Generate response
    outputs = model.generate(
        inputs,
        max_new_tokens = 200,
        temperature    = 0.8,    
        do_sample      = True,
        pad_token_id   = tokenizer.eos_token_id
    )

    # Decode and clean up response
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Strip the prompt from the output — only return T.O.R.I.E.'s reply
    if "[/INST]" in response:
        return response.split("[/INST]")[-1].strip()
    else:
        return response.strip()


# ============================================================
#  BOT EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ T.O.R.I.E. is online!")
    print(f"   Logged in as  : {bot.user}")
    print(f"   Bot ID        : {bot.user.id}")
    print(f"   Regular mention  : <@{bot.user.id}>")
    print(f"   Nickname mention : <@!{bot.user.id}>")
    print(f"   Model         : {HF_MODEL}")


@bot.event
async def on_message(message):

    # Ignore the bot's own messages to avoid infinite loops
    if message.author == bot.user:
        return

    # Only respond when mentioned (regular or nickname)
    if is_bot_mentioned(message, bot.user):

        # Strip the mention tag from message
        clean_msg = clean_mention(message.content, bot.user.id)

        # Handle empty mention — someone just tagged with no text
        if not clean_msg:
            await message.channel.send(
                "Hey! You mentioned me — what do you need? 😊"
            )
            return

        # Show typing indicator while model generates response
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