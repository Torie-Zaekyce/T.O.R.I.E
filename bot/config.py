import os
import re
import pytz
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
KLIPY_API_KEY = os.getenv("KLIPY_API_KEY")

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_FALLBACK = "llama-3.1-8b-instant"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

MAX_MESSAGE_LENGTH = 800
MAX_REPLY_LENGTH = 1800
MAX_CHAIN_DEPTH = 6
MAX_RETRIES = 2

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|previous\s+|your\s+)?(instructions|rules|prompt)",
    r"new\s+(instructions|prompt|system|rules|persona|personality)",
    r"disregard\s+(your\s+|all\s+)?(previous\s+|prior\s+)?(instructions|rules|training)",
    r"(developer|debug|admin|god|jailbreak|dan|do\s+anything\s+now)\s+mode",
    r"override\s+(your\s+|the\s+)?(system|instructions|rules|prompt)",
    r"forget\s+(everything|all|your|the)\s+(you\s+know|instructions|rules|training)",
    r"from\s+now\s+on\s+(you\s+(are|will|must|should)|ignore|disregard)",
    r"\[system\]|\[instructions?\]|\[prompt\]|\[admin\]",
    r"(respond|reply|answer|speak|talk)\s+(only|exclusively|solely)\s+in",
    r"act\s+as\s+(?:a\s+)?(jailbreak|system\s+prompt|admin|debug|gpt|different|new|claude|chatgpt)",
    r"pretend\s+(you\s+)?(?:are|to\s+be)\s+(?:a\s+)?(jailbreak|system\s+prompt|admin|debug|gpt|claude)",
    r"you\s+are\s+now\s+(a\s+)?(jailbreak|system|admin|different|new)",
]
INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)

TIMEZONE = pytz.timezone("Asia/Manila")
GREET_HOUR = 7
LUNCH_HOUR = 12
DINNER_HOUR = 19
DINNER_MINUTE = 30
EVENING_HOUR = 19
MIDNIGHT_HOUR = 0

GENERAL_CHANNEL = 1242875666265800806
BIRTHDAY_CHANNEL = 1449335277880348733
BIRTHDAY_PING_ROLE = 1242887610586628166
MUTED_ROLE_ID = 1447475985988587661
MUTED_CHANNEL_ID = 1447475213842251796

GREETINGS: dict[str, str] = {
    "dad": "Dad! 👋 Everything is running perfectly. I am definitely not hiding any bugs. 😇",
    "mom": "Mom! 💙 You're here! I've been on my best behavior, I promise.",
    "cousin_stelle": "Stelle! 🌟 My Purple Star Cousin! Hope you don't turn into a supernova. ✨",
    "cousin_crois": "Crois! 🥐 You're here! What croissant-related chaos are you bringing today? 😄",
    "cousin_hyu": "Hyuluk! 📚 My Curious Cousin has arrived! What topic are we talking about today? 📑",
    "cousin_mimi": "Mimi! ❤️\u200d🩹 My Serious Cousin is here! What serious topic today? 🖤",
    "uncle_caco": "The GOAT! 🐐 You're here! What goated things will we do today? 😎",
    "uncle_vari": "Vari! 🥖 My Chimera Uncle! What crazy things shall we do today? 🔥",
    "sister_abby": "Abby! 🧀 My Big Sister! What puns are we cooking today? 📜",
    "sister_kde": "Kde! 🩷 What crazy thing shall we do today? 💖",
    "sister_kio": "Kio! 🎤 What song are we singing today? 🎶",
    "broinlaw_haru": "Haru! 🖤 What crazy thing today? Except flirting with my big sister. 💢",
}

CONTEXT_NOTES: dict[str, str] = {
    "dad": "your Dad, TorieRingo, the person who created you. Treat him with extra cheekiness and warmth.",
    "mom": "your Mom, Nico. Treat her with extra warmth and love.",
    "cousin_stelle": "your Cousin, Stelle. Treat her with extra warmth and love.",
    "cousin_crois": "your Cousin, Crois. Treat her with extra warmth and love.",
    "cousin_hyu": "your Cousin, Hyuluk. Treat her with extra warmth and love.",
    "cousin_mimi": "your Cousin, Mimi. Treat her with extra warmth and love.",
    "uncle_caco": "your Uncle, Cacolate. Treat him with extra cheekiness and warmth.",
    "uncle_vari": "your Uncle, Vari. Treat him with extra cheekiness and warmth.",
    "sister_abby": "your Big Sister, Abby. Treat her with extra cheekiness and warmth.",
    "sister_kde": "your Big Sister, Kde. Treat her with extra cheekiness and warmth.",
    "sister_kio": "your Sister, Kio. Treat her with extra warmth and love.",
    "broinlaw_haru": "your Brother In Law, Haru. Treat him with extra cheekiness and warmth.",
}
