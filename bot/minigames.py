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

SESSION_TIMEOUT = 30 * 60

CHESS_START = re.compile(
    r"\b(chess|let'?s play|wanna play|play (a game|chess)|start (a game|chess))\b",
    re.IGNORECASE,
)
CHESS_END = re.compile(
    r"\b(checkmate|stalemate|i resign|i give up|draw|game over|gg|good game|let'?s stop)\b",
    re.IGNORECASE,
)

TICTACTOE_START = re.compile(
    r"\b(tic.?tac.?toe|tictactoe|noughts? and crosses|x and o|three in a row)\b",
    re.IGNORECASE,
)
TICTACTOE_END = re.compile(
    r"\b(you won|i won|draw|tie|game over|gg|good game|let'?s stop|quit)\b",
    re.IGNORECASE,
)

BATTLESHIP_START = re.compile(
    r"\b(battleship|naval|sink my|destroy my|hunt me)\b",
    re.IGNORECASE,
)
BATTLESHIP_END = re.compile(
    r"\b(you sank my|i sank your|all ships|game over|surrender|gg|good game)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# System notes
# ---------------------------------------------------------------------------

CHESS_SYSTEM_NOTE = (
    "You are playing a text-based chess game with the user via Discord reply chain. "
    "The full move history is in the conversation above — use it to reconstruct the current board. "
    "Accept moves in any common notation (e.g. 'e4', 'Nf3', 'knight to f3', 'pawn to e4'). "
    "After each move: confirm the move, make your own move, then announce whose turn it is next. "
    "Announce check ♟️, checkmate 🏁, stalemate 🤝 when they occur and declare the game over. "
    "Stay in character as T.O.R.I.E. — playful and a little competitive."
)

TICTACTOE_SYSTEM_NOTE = (
    "You are playing Tic Tac Toe with the user. "
    "Track the board mentally (3x3 grid, positions 1-9 top-left to bottom-right). "
    "User is X, you are O. "
    "After each move: place your O, announce the position, then ask for the user's move. "
    "Detect wins (three in a row) and draws (board full). Be playful and slightly competitive."
)

BATTLESHIP_SYSTEM_NOTE = (
    "You are playing Battleship with the user on a 10x10 grid (columns A-J, rows 1-10). "
    "You place your ships secretly. The user places theirs (ask them to list coordinates at start). "
    "Take turns calling coordinates. Respond 'Hit!' or 'Miss!' and then take your shot. "
    "Announce when a ship is fully sunk. First to sink all opponent ships wins. "
    "Be strategic and playful."
)

GAMES: dict[str, dict] = {
    "chess": {
        "start":       CHESS_START,
        "end":         CHESS_END,
        "system_note": CHESS_SYSTEM_NOTE,
    },
    "tictactoe": {
        "start":       TICTACTOE_START,
        "end":         TICTACTOE_END,
        "system_note": TICTACTOE_SYSTEM_NOTE,
    },
    "battleship": {
        "start":       BATTLESHIP_START,
        "end":         BATTLESHIP_END,
        "system_note": BATTLESHIP_SYSTEM_NOTE,
    },
}

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class Session:
    __slots__ = ("last_active", "kind", "system_note")

    def __init__(self, kind: str):
        game = GAMES.get(kind, {})
        self.last_active: float = asyncio.get_event_loop().time()
        self.kind:        str   = kind
        self.system_note: str   = game.get("system_note", "")

    def touch(self) -> None:
        self.last_active = asyncio.get_event_loop().time()

    def is_expired(self) -> bool:
        return (asyncio.get_event_loop().time() - self.last_active) > SESSION_TIMEOUT

    def is_ended_by(self, text: str) -> bool:
        end_re = GAMES.get(self.kind, {}).get("end")
        return bool(end_re and end_re.search(text))


_sessions: dict[tuple[int, int], Session] = {}


def get_session(channel_id: int, user_id: int) -> Session | None:
    key = (channel_id, user_id)
    s = _sessions.get(key)
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
    for kind, game in GAMES.items():
        if game["start"].search(text):
            return kind
    return None