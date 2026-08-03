# bot/chat_activity.py — Spontaneous chat join + greeting detection helpers

import re
import time
from collections import deque

GREET_MAX_CHARS = 60

GREETING_WORDS = {
    "hi", "hello", "hey", "heya", "hiya", "yo", "yoo", "sup", "suuup", "howdy",
    "halo", "helo", "hallo", "hola", "hai", "henlo", "henloo",
    "hii", "hiii", "hiiii", "helloo", "hellooo", "heyy", "heyyy", "heyyyy",
    "gm", "gn", "mn", "morning", "mornin", "afternoon", "evening",
}
GREETING_PHRASES = {"good morning", "good afternoon", "good evening"}

_NON_WORD_RE = re.compile(r"[^\w\s]")


def is_greeting(content: str) -> bool:
    """True if a message is essentially a hello (short, opens with a greeting)."""
    if not content or len(content) > GREET_MAX_CHARS:
        return False
    text = _NON_WORD_RE.sub(" ", content.lower())
    tokens = text.split()
    if not tokens:
        return False
    if tokens[0] in GREETING_WORDS:
        return True
    if len(tokens) >= 2 and " ".join(tokens[:2]) in GREETING_PHRASES:
        return True
    return False


class ChatActivityTracker:
    """Per-channel sliding window of recent messages for lively-chat detection."""

    _PRUNE_AFTER = 3600
    _MAX_CHANNELS = 100

    def __init__(self, maxlen: int = 40):
        self._maxlen = maxlen
        self._messages: dict[int, deque] = {}

    def record(self, channel_id: int, author_id: int, author_name: str, content: str) -> None:
        now = time.time()
        dq = self._messages.setdefault(channel_id, deque(maxlen=self._maxlen))
        dq.append((now, author_id, author_name, content))
        if len(self._messages) > self._MAX_CHANNELS:
            self._prune(now)

    def recent(self, channel_id: int, window: int) -> list:
        cutoff = time.time() - window
        dq = self._messages.get(channel_id)
        if not dq:
            return []
        return [m for m in dq if m[0] >= cutoff]

    def clear(self, channel_id: int) -> None:
        self._messages.pop(channel_id, None)

    def _prune(self, now: float) -> None:
        stale = [cid for cid, dq in self._messages.items() if dq and now - dq[-1][0] > self._PRUNE_AFTER]
        for cid in stale:
            self._messages.pop(cid, None)


class GreetingGuard:
    """Anti-spam guard so the bot only greets the first hello in a burst."""

    def __init__(self):
        self._channel_last: dict[int, float] = {}
        self._user_last: dict[int, float] = {}

    def allow(self, channel_id: int, user_id: int, channel_cd: int, user_cd: int) -> bool:
        now = time.time()
        if now - self._channel_last.get(channel_id, 0) < channel_cd:
            return False
        if now - self._user_last.get(user_id, 0) < user_cd:
            return False
        self._channel_last[channel_id] = now
        self._user_last[user_id] = now
        return True
