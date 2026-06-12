# bot/minigames.py — T.O.R.I.E. Minigame Session Manager
#
# Owns all stateful game logic (session lifecycle, per-game prompts,
# start/end detection). bot.py imports from here; adding a new game
# means only touching this file.

import asyncio
import re
import discord
from random import randint
 
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
CHESS_SYSTEM_NOTE = (
    "You are currently playing a text-based chess game with the user. "
    "Track the board state mentally across all turns. "
    "Accept moves in any common notation (e.g. 'e4', 'Nf3', 'knight to f3', 'pawn to e4'). "
    "After each move: confirm the move, describe the updated board state concisely, "
    "make your own move as White or Black (whichever you are), and ask for theirs. "
    "Stay in character as T.O.R.I.E. — be playful and a little competitive. "
    "Announce check, checkmate, or stalemate when they occur."
)

TICTACTOE_SYSTEM_NOTE = (
    "You are playing Tic Tac Toe with the user. "
    "Track the board state mentally (3x3 grid). "
    "User is X, you are O. Positions are numbered 1-9 (top-left to bottom-right). "
    "After each move: announce where you placed O, and ask for the user's next move. "
    "Detect when someone wins (three in a row) or if the board is full (draw). "
    "Be playful and slightly competitive."
)

BATTLESHIP_SYSTEM_NOTE = (
    "You are playing Battleship with the user. "
    "The user places ships on a 10x10 grid (A-J columns, 1-10 rows). "
    "You place your ships secretly. Take turns calling out coordinates to find each other's ships. "
    "When you get a hit, say 'Hit!' and continue. When you miss, say 'Miss!' and let them go. "
    "Announce when a ship is sunk (all positions found). First to sink all opponent ships wins. "
    "Be strategic and playful. Maintain the game state mentally."
)
 
GAMES: dict[str, dict] = {
    "chess": {
        "start": CHESS_START,
        "end": CHESS_END,
        "system_note": CHESS_SYSTEM_NOTE,
    },
    "tictactoe": {
        "start": TICTACTOE_START,
        "end": TICTACTOE_END,
        "system_note": TICTACTOE_SYSTEM_NOTE,
    },
    "battleship": {
        "start": BATTLESHIP_START,
        "end": BATTLESHIP_END,
        "system_note": BATTLESHIP_SYSTEM_NOTE,
    },
}
 
class Session:
    __slots__ = ("history", "last_active", "kind", "system_note", "board_state")

    def __init__(self, kind: str):
        game = GAMES.get(kind, {})
        self.history: list[dict] = []
        self.last_active: float = asyncio.get_event_loop().time()
        self.kind: str = kind
        self.system_note: str = game.get("system_note", "")
        self.board_state: dict = self._init_board(kind)

    def _init_board(self, kind: str) -> dict:
        """Initialize game board based on game type."""
        if kind == "tictactoe":
            return {"grid": [" "] * 9, "turn": "user"}
        elif kind == "battleship":
            return {
                "player_board": [["~"] * 10 for _ in range(10)],
                "bot_board": [["~"] * 10 for _ in range(10)],
                "bot_revealed": [["~"] * 10 for _ in range(10)],
                "turn": "user",
            }
        return {}

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
 
_sessions: dict[tuple[int, int], Session] = {}


def get_session(channel_id: int, user_id: int) -> Session | None:
    """Return the active session or None (also evicts expired sessions)."""
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
    """
    Check text against every registered game's start pattern.
    Returns the matching game kind string, or None.
    """
    for kind, game in GAMES.items():
        if game["start"].search(text):
            return kind
    return None


def render_chess_embed(fen: str = None, title: str = "♟ Chess") -> discord.Embed:
    """
    Render Chess board as an embed. If FEN provided, parse it; otherwise show empty board.
    Uses Unicode chess symbols.
    """
    piece_map = {
        'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
        'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
        '.': '·',
    }
    
    lines = []
    lines.append("  A B C D E F G H")
    
    board_default = [
        "8 ♜ ♞ ♝ ♛ ♚ ♝ ♞ ♜",
        "7 ♟ ♟ ♟ ♟ ♟ ♟ ♟ ♟",
        "6 · · · · · · · ·",
        "5 · · · · · · · ·",
        "4 · · · · · · · ·",
        "3 · · · · · · · ·",
        "2 ♙ ♙ ♙ ♙ ♙ ♙ ♙ ♙",
        "1 ♖ ♘ ♗ ♕ ♔ ♗ ♘ ♖",
    ]
    
    board_str = "\n".join(board_default)
    embed = discord.Embed(
        title=title,
        description=f"```\n{board_str}\n```\nUse standard notation (e.g., e4, Nf3, O-O castling)",
        color=discord.Color.from_rgb(210, 180, 140)
    )
    return embed


def render_tictactoe_embed(grid: list[str]) -> discord.Embed:
    """Render Tic Tac Toe board as an embed with emoji grid."""
    emoji_map = {" ": "⬜", "X": "❌", "O": "⭕"}

    lines = []
    for i in range(0, 9, 3):
        row = "".join(emoji_map[grid[i + j]] for j in range(3))
        lines.append(row)

    board_str = "\n".join(lines)
    embed = discord.Embed(
        title="🎮 Tic Tac Toe",
        description=f"```\n{board_str}\n```\nPositions: 1️⃣2️⃣3️⃣ / 4️⃣5️⃣6️⃣ / 7️⃣8️⃣9️⃣",
        color=discord.Color.blurple()
    )
    return embed


def render_battleship_embed(board: list[list[str]], title: str = "🚢 Battleship") -> discord.Embed:
    """Render Battleship board as an embed with grid."""
    emoji_map = {"~": "🌊", "X": "💥", "O": "✅", "S": "🚢"}

    header = " " + " ".join("ABCDEFGHIJ")
    lines = [header]

    for i, row in enumerate(board, 1):
        row_str = str(i).rjust(2) + " " + " ".join(emoji_map.get(cell, cell) for cell in row)
        lines.append(row_str)

    board_str = "\n".join(lines)
    embed = discord.Embed(
        title=title,
        description=f"```\n{board_str}\n```",
        color=discord.Color.dark_blue()
    )
    return embed