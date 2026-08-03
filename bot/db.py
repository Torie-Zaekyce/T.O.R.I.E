# bot/db.py — MongoDB singleton and all collection/CRUD helpers

import os
from datetime import datetime

from bot.config import TIMEZONE

import pymongo

_MONGO_UNAVAILABLE = object()
_mongo_client = None
_birthday_col = None
_filter_col   = None
_warn_col     = None
_perm_col     = None


def _get_client():
    global _mongo_client
    if _mongo_client is _MONGO_UNAVAILABLE:
        return None
    if _mongo_client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            print("⚠️ MONGODB_URI not set — data won't persist!")
            _mongo_client = _MONGO_UNAVAILABLE
            return None
        try:
            import certifi
            _mongo_client = pymongo.MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                tlsCAFile=certifi.where(),
            )
            print("✅ MongoDB connected!")
        except Exception as e:
            print(f"⚠️ MongoDB connection failed: {e}")
            _mongo_client = _MONGO_UNAVAILABLE
            return None
    return _mongo_client


def get_birthday_col():
    global _birthday_col
    if _birthday_col is None:
        c = _get_client()
        if c:
            _birthday_col = c["torie"]["birthdays"]
    return _birthday_col


def get_filter_col():
    global _filter_col
    if _filter_col is None:
        c = _get_client()
        if c:
            _filter_col = c["torie"]["filtered_words"]
    return _filter_col


def get_warn_col():
    global _warn_col
    if _warn_col is None:
        c = _get_client()
        if c:
            _warn_col = c["torie"]["warns"]
    return _warn_col


def get_perm_col():
    global _perm_col
    if _perm_col is None:
        c = _get_client()
        if c:
            _perm_col = c["torie"]["permissions"]
    return _perm_col


_memory_col = None

def get_memory_col():
    global _memory_col
    if _memory_col is None:
        c = _get_client()
        if c:
            _memory_col = c["torie"]["user_memory"]
    return _memory_col


def load_birthdays() -> dict:
    col = get_birthday_col()
    if col is None:
        return {}
    try:
        return {doc["_id"]: {k: v for k, v in doc.items() if k != "_id"} for doc in col.find()}
    except Exception as e:
        print(f"⚠️ Failed to load birthdays: {e}")
        return {}


def save_birthday(user_id: str, data: dict):
    col = get_birthday_col()
    if col is None:
        return
    try:
        col.replace_one({"_id": user_id}, {"_id": user_id, **data}, upsert=True)
    except Exception as e:
        print(f"⚠️ Failed to save birthday: {e}")


def delete_birthday(user_id: str):
    col = get_birthday_col()
    if col is None:
        return
    try:
        col.delete_one({"_id": user_id})
    except Exception as e:
        print(f"⚠️ Failed to delete birthday: {e}")


def get_todays_birthdays(birthdays: dict) -> list[dict]:
    now = datetime.now(TIMEZONE)
    today = (now.month, now.day)
    return [
        {"name": data.get("name", key), **data}
        for key, data in birthdays.items()
        if (data["month"], data["day"]) == today
    ]


def load_filter_words() -> list[str]:
    col = get_filter_col()
    if col is None:
        return []
    try:
        doc = col.find_one({"_id": "filter_list"})
        return doc["words"] if doc and "words" in doc else []
    except Exception as e:
        print(f"⚠️ Failed to load filter words: {e}")
        return []


def save_filter_words(words: list[str]):
    col = get_filter_col()
    if col is None:
        return
    try:
        col.replace_one(
            {"_id": "filter_list"},
            {"_id": "filter_list", "words": words},
            upsert=True,
        )
    except Exception as e:
        print(f"⚠️ Failed to save filter words: {e}")


def load_warns(user_id: str) -> list:
    col = get_warn_col()
    if col is None:
        return []
    try:
        doc = col.find_one({"_id": user_id})
        return doc["warns"] if doc and "warns" in doc else []
    except Exception as e:
        print(f"⚠️ Failed to load warns: {e}")
        return []


def add_warn(user_id: str, reason: str, mod_name: str) -> int:
    col = get_warn_col()
    if col is None:
        return 0
    try:
        entry = {
            "reason": reason,
            "mod":    mod_name,
            "time":   datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        }
        col.update_one({"_id": user_id}, {"$push": {"warns": entry}}, upsert=True)
        doc = col.find_one({"_id": user_id})
        return len(doc["warns"]) if doc else 1
    except Exception as e:
        print(f"⚠️ Failed to add warn: {e}")
        return 0


def clear_warns(user_id: str):
    col = get_warn_col()
    if col is None:
        return
    try:
        col.delete_one({"_id": user_id})
    except Exception as e:
        print(f"⚠️ Failed to clear warns: {e}")


def load_user_perms(user_id: int) -> set:
    col = get_perm_col()
    if col is None:
        return set()
    try:
        doc = col.find_one({"_id": str(user_id)})
        return set(doc["perms"]) if doc and "perms" in doc else set()
    except Exception as e:
        print(f"⚠️ Failed to load permissions: {e}")
        return set()


def grant_perm(user_id: int, perm: str) -> bool:
    col = get_perm_col()
    if col is None:
        return False
    try:
        col.update_one({"_id": str(user_id)}, {"$addToSet": {"perms": perm}}, upsert=True)
        return True
    except Exception as e:
        print(f"⚠️ Failed to grant perm: {e}")
        return False


def revoke_perm(user_id: int, perm: str) -> bool:
    col = get_perm_col()
    if col is None:
        return False
    try:
        col.update_one({"_id": str(user_id)}, {"$pull": {"perms": perm}})
        return True
    except Exception as e:
        print(f"⚠️ Failed to revoke perm: {e}")
        return False


_settings_col = None


def get_settings_col():
    global _settings_col
    if _settings_col is None:
        c = _get_client()
        if c:
            _settings_col = c["torie"]["settings"]
    return _settings_col


def load_settings() -> dict:
    col = get_settings_col()
    if col is None:
        return {}
    try:
        doc = col.find_one({"_id": "spontaneous"})
        return dict(doc.get("data", {})) if doc and "data" in doc else {}
    except Exception as e:
        print(f"⚠️ Failed to load settings: {e}")
        return {}


def save_settings(data: dict):
    col = get_settings_col()
    if col is None:
        return
    try:
        col.replace_one({"_id": "spontaneous"}, {"_id": "spontaneous", "data": data}, upsert=True)
    except Exception as e:
        print(f"⚠️ Failed to save settings: {e}")
