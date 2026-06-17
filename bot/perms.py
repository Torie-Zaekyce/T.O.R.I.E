# bot/perms.py — Permission system (family defaults + DB-granted perms)

from bot.family import get_role
from bot.db import load_user_perms

VALID_PERMS: set[str] = {"mute", "unmute", "filter", "personality", "purge", "sendmsg", "warn", "mod"}

_FAMILY_DEFAULT_PERMS: dict[str, set] = {
    "dad":           {"mod"},
    "mom":           {"mod"},
    "cousin_stelle": {"mute", "unmute", "warn", "purge", "sendmsg"},
    "cousin_crois":  {"mute", "unmute", "warn", "purge", "sendmsg"},
    "cousin_hyu":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "cousin_mimi":   {"mute", "unmute", "warn", "purge", "sendmsg"},
    "uncle_caco":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "uncle_vari":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "sister_abby":   {"mute", "unmute", "warn", "purge", "sendmsg"},
    "sister_kde":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "sister_kio":    {"mute", "unmute", "warn", "purge", "sendmsg"},
    "broinlaw_haru": {"mute", "unmute", "warn", "purge", "sendmsg"},
}


def has_permission(user, perm: str) -> bool:
    role = get_role(user)
    if role:
        defaults = _FAMILY_DEFAULT_PERMS.get(role, set())
        if "mod" in defaults or perm in defaults:
            return True
    db_perms = load_user_perms(user.id)
    return "mod" in db_perms or perm in db_perms


def family_defaults_for(role: str | None) -> set:
    return _FAMILY_DEFAULT_PERMS.get(role, set()) if role else set()
