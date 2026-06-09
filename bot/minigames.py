# bot/minigames.py — T.O.R.I.E. Minigame Session Manager
#
# Owns all stateful game logic (session lifecycle, per-game prompts,
# start/end detection). bot.py imports from here; adding a new game
# means only touching this file.
 
import asyncio
import re
 
# ---------------------------------------------------------------------------
# Session config
# ---------------------------------------------------------------------------
 
SESSION_TIMEOUT = 30 * 60  # 30 min inactivity → session expires
 
# ---------------------------------------------------------------------------
# Chess
# ---------------------------------------------------------------------------
 
CHESS_START = re.compile(
    r"\b(chess|let'?s play|wanna play|play (a game|chess)|start (a game|chess))\b",
    re.IGNORECASE,
)
CHESS_END = re.compile(
    r"\b(checkmate|stalemate|i resign|i give up|draw|game over|gg|good game|let'?s stop)\b",
    re.IGNORECASE,
)
CHESS_SYSTEM_NOTE = (
    "You are currently playing a text-based chess game with the user. "
    "Track the board state mentally across all turns. "
    "Accept moves in any common notation (e.g. 'e4', 'Nf3', 'knight to f3', 'pawn to e4'). "
    "After each move: confirm the move, describe the updated board state concisely, "
    "make your own move as White or Black (whichever you are), and ask for theirs. "
    "Stay in character as T.O.R.I.E. — be playful and a little competitive. "
    "Announce check, checkmate, or stalemate when they occur."
)
 
# ---------------------------------------------------------------------------
# Game registry — add new games here
#
# Each entry:
#   "kind": {
#       "start":       compiled regex that triggers the game
#       "end":         compiled regex that ends the game
#       "system_note": injected into the LLM system prompt for the duration
#   }
# ---------------------------------------------------------------------------
 
GAMES: dict[str, dict] = {
    "chess": {
        "start":       CHESS_START,
        "end":         CHESS_END,
        "system_note": CHESS_SYSTEM_NOTE,
    },
}
 
# ---------------------------------------------------------------------------
# Session class
# ---------------------------------------------------------------------------
 
class Session:
    __slots__ = ("history", "last_active", "kind", "system_note")
 
    def __init__(self, kind: str):
        game = GAMES.get(kind, {})
        self.history:     list[dict] = []
        self.last_active: float      = asyncio.get_event_loop().time()
        self.kind:        str        = kind
        self.system_note: str        = game.get("system_note", "")
 
    def touch(self) -> None:
        self.last_active = asyncio.get_event_loop().time()
 
    def is_expired(self) -> bool:
        return (asyncio.get_event_loop().time() - self.last_active) > SESSION_TIMEOUT
 
    def append(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
 
    def is_ended_by(self, text: str) -> bool:
        """Return True if the message triggers the end condition for this game."""
        end_re = GAMES.get(self.kind, {}).get("end")
        return bool(end_re and end_re.search(text))
 
# ---------------------------------------------------------------------------
# Session store  —  key: (channel_id, user_id)
# ---------------------------------------------------------------------------
 
_sessions: dict[tuple[int, int], Session] = {}
 
 
def get_session(channel_id: int, user_id: int) -> Session | None:
    """Return the active session or None (also evicts expired sessions)."""
    key = (channel_id, user_id)
    s   = _sessions.get(key)
    if s and s.is_expired():
        del _sessions[key]
        return None
    return s
 
 
def start_session(channel_id: int, user_id: int, kind: str) -> Session:
    key = (channel_id, user_id)
    _sessions[key] = Session(kind)
    return _sessions[key]
 
 
def end_session(channel_id: int, user_id: int) -> None:
    _sessions.pop((channel_id, user_id), None)
 
 
def detect_game_start(text: str) -> str | None:
    """
    Check text against every registered game's start pattern.
    Returns the matching game kind string, or None.
    """
    for kind, game in GAMES.items():
        if game["start"].search(text):
            return kind
    return None