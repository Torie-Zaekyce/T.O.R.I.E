import asyncio
import re
import discord
from datetime import timedelta as _td
from bot.config import INJECTION_REGEX, MAX_MESSAGE_LENGTH, MAX_REPLY_LENGTH

def parse_duration(text: str) -> _td | None:
    """Parse duration strings like '10m', '2h', '3d' into timedelta."""
    patterns = [
        (re.compile(r"(\d+)\s*s(?:ec(?:ond)?s?)?", re.I), "seconds"),
        (re.compile(r"(\d+)\s*m(?:in(?:ute)?s?)?", re.I), "minutes"),
        (re.compile(r"(\d+)\s*h(?:(?:ou)?rs?)?", re.I), "hours"),
        (re.compile(r"(\d+)\s*d(?:ays?)?", re.I), "days"),
        (re.compile(r"(\d+)\s*w(?:eeks?)?", re.I), "weeks"),
    ]
    kwargs = {}
    for pattern, unit in patterns:
        m = pattern.search(text)
        if m:
            kwargs[unit] = int(m.group(1))
    return _td(**kwargs) if kwargs else None


def fmt_duration(d: _td) -> str:
    """Format a timedelta into human-readable string like '1d 2h 30m'."""
    parts, secs = [], d.seconds
    if d.days:
        parts.append(f"{d.days}d")
    if secs >= 3600:
        parts.append(f"{secs // 3600}h")
        secs %= 3600
    if secs >= 60:
        parts.append(f"{secs // 60}m")
        secs %= 60
    if secs:
        parts.append(f"{secs}s")
    return " ".join(parts) or "unknown"


def sanitize_input(text: str) -> tuple[str | None, str | None]:
    """
    Check and clean input text.
    Returns: (cleaned_text, rejection_reason)
    - rejection_reason can be: None, "too_long", "injection"
    """
    if len(text) > MAX_MESSAGE_LENGTH:
        return None, "too_long"
    if INJECTION_REGEX.search(text):
        return None, "injection"
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]', '', text)
    text = re.sub(r'\s{3,}', '  ', text).strip()
    return text, None


def sanitize_reply(text: str) -> str:
    """Remove dangerous mentions and injected instructions from bot replies."""
    text = text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    if INJECTION_REGEX.search(text):
        return "I'm not sure what you're talking about. 😅"
    if len(text) > MAX_REPLY_LENGTH:
        text = text[:MAX_REPLY_LENGTH].rsplit(" ", 1)[0] + "…"
    return text


async def fetch_reply_chain(message: discord.Message, max_depth: int = 6) -> list[dict]:
    """
    Walk up the Discord reply chain and return an ordered list of
    {"role": "user"|"assistant", "content": str} dicts, oldest first.
    """
    chain = []
    current = message
    for _ in range(max_depth):
        ref = current.reference
        if not ref:
            break
        try:
            if isinstance(ref.resolved, discord.Message):
                parent = ref.resolved
            else:
                await asyncio.sleep(0.3)
                parent = await current.channel.fetch_message(ref.message_id)
        except discord.HTTPException:
            break

        content = parent.content or ""
        content = re.sub(r"<@!?\d+>\s*", "", content).strip()
        if not content:
            current = parent
            continue

        # Drop the entire chain if any parent message contains prompt injection
        if INJECTION_REGEX.search(content):
            return []

        role = "assistant" if parent.author.bot else "user"
        if role == "user":
            content = f"{parent.author.display_name}: {content}"

        chain.append({"role": role, "content": content})
        current = parent

    chain.reverse()
    return chain
