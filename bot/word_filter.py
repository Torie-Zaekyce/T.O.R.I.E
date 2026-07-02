# bot/word_filter.py — Word filter: normalization, cache, and detection

import re
from bot.db import load_filter_words, save_filter_words

# ---------------------------------------------------------------------------
# Core filter list (hard-coded defaults + DB-persisted additions)
# ---------------------------------------------------------------------------

FILTERED_WORDS: list[str] = ["retard", "nigger", "nigga", "negro", "negra"]

FILTER_WHITELIST: set[str] = {
    "focus", "focused", "focusing", "refocus",
    "classic", "classico", "discuss", "discussion",
    "snicker", "snigger", "trigger", "bigger", "digger",
    "figure", "figures", "niggle", "niggly", "niggard",
    "assign", "assigned", "assignee", "significant",
    "vinegar", "renegade",
}

# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------

NORMALIZER = str.maketrans({
    "0": "o",  "1": "i",  "3": "e",  "4": "a",
    "5": "s",  "6": "g",  "7": "t",  "8": "b",
    "@": "a",  "$": "s",  "!": "i",  "+": "t",
    "(": "c",  ")": "o",  "*": "",   ".": "",
    "_": "",   "-": "",   " ": "",
    "а": "a",  "е": "e",  "о": "o",  "р": "p",
    "с": "c",  "х": "x",  "и": "n",  "g": "g",
    "ı": "i",  "ɪ": "i",  "ɡ": "g",  "ǝ": "e",
    "ñ": "n",  "η": "n",
})

_ZERO_WIDTH_RE      = re.compile(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff]')
_REPEAT_CHAR_RE     = re.compile(r'(.)\1{2,}')
_NON_ALPHANUMERIC_RE = re.compile(r'[^a-z0-9]')
_WORD_BOUNDARY_RE   = re.compile(r"\b\w+\b")


def normalize(text: str) -> str:
    text = text.lower().translate(NORMALIZER)
    text = _ZERO_WIDTH_RE.sub('', text)
    text = _REPEAT_CHAR_RE.sub(r'\1\1', text)
    return _NON_ALPHANUMERIC_RE.sub('', text)


# ---------------------------------------------------------------------------
# Filter cache (rebuilt whenever FILTERED_WORDS changes)
# ---------------------------------------------------------------------------

_NORM_SLURS:   dict[str, str] = {}
_MAX_SLUR_LEN: int            = 0


def rebuild_filter_cache() -> None:
    global _NORM_SLURS, _MAX_SLUR_LEN
    _NORM_SLURS   = {normalize(w): w for w in FILTERED_WORDS}
    _MAX_SLUR_LEN = max(len(k) for k in _NORM_SLURS) if _NORM_SLURS else 0


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def contains_filtered_word(content: str) -> str | None:
    tokens = _WORD_BOUNDARY_RE.findall(content.lower())
    for token in tokens:
        if token in FILTER_WHITELIST:
            continue
        normed = normalize(token)
        if normed in _NORM_SLURS:
            return _NORM_SLURS[normed]

    norm_full = normalize(content)
    for slur_norm, slur_orig in _NORM_SLURS.items():
        idx = norm_full.find(slur_norm)
        if idx == -1:
            continue
        slur_end = idx + len(slur_norm)
        # Skip if this substring overlap is inside a whitelisted word
        overrides_whitelist = False
        for wl_word in FILTER_WHITELIST:
            wl_norm = normalize(wl_word)
            wl_idx = norm_full.find(wl_norm)
            if wl_idx != -1:
                wl_end = wl_idx + len(wl_norm)
                if idx < wl_end and slur_end > wl_idx:
                    overrides_whitelist = True
                    break
        if not overrides_whitelist:
            return slur_orig

    return None


# ---------------------------------------------------------------------------
# Public helpers for the filter cog
# ---------------------------------------------------------------------------

def add_word(word: str) -> bool:
    """Add word to the filter list. Returns False if already present."""
    if word in [w.lower() for w in FILTERED_WORDS]:
        return False
    FILTERED_WORDS.append(word)
    rebuild_filter_cache()
    save_filter_words(FILTERED_WORDS)
    return True


def remove_word(word: str) -> bool:
    """Remove word from the filter list. Returns False if not found."""
    matching = [w for w in FILTERED_WORDS if w.lower() == word]
    if not matching:
        return False
    FILTERED_WORDS.remove(matching[0])
    rebuild_filter_cache()
    save_filter_words(FILTERED_WORDS)
    return True


def clear_all_words() -> int:
    """Clear every word. Returns the count removed."""
    count = len(FILTERED_WORDS)
    FILTERED_WORDS.clear()
    rebuild_filter_cache()
    save_filter_words(FILTERED_WORDS)
    return count


# ---------------------------------------------------------------------------
# Initialise from DB on import
# ---------------------------------------------------------------------------

def _init_filter_words():
    for word in load_filter_words():
        if word not in FILTERED_WORDS:
            FILTERED_WORDS.append(word)


_init_filter_words()
rebuild_filter_cache()
