import os
import pymongo
from datetime import datetime, timezone
 
MAX_FACTS = 20
 
_MONGO_UNAVAILABLE = object()
_mongo_client      = None
_memory_col        = None
 
 
def _get_client():
    global _mongo_client
    if _mongo_client is _MONGO_UNAVAILABLE:
        return None
    if _mongo_client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            print("⚠️ [user_memory] MONGODB_URI not set — memories won't persist!")
            _mongo_client = _MONGO_UNAVAILABLE
            return None
        try:
            import certifi
            _mongo_client = pymongo.MongoClient(
                uri,
                serverSelectionTimeoutMS=5000,
                tlsCAFile=certifi.where(),
            )
            _mongo_client.admin.command("ping")
            print("✅ [user_memory] MongoDB connected!")
        except Exception as e:
            print(f"⚠️ [user_memory] MongoDB connection failed: {e}")
            _mongo_client = _MONGO_UNAVAILABLE
            return None
    return _mongo_client
 
 
def _col():
    global _memory_col
    if _memory_col is None:
        client = _get_client()
        if client:
            _memory_col = client["torie"]["user_memory"]
            _memory_col.create_index("_id", unique=True)
    return _memory_col
 
 
# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
 
def get_user_memory(user_id: str) -> dict | None:
    col = _col()
    if col is None:
        return None
    try:
        return col.find_one({"_id": user_id})
    except Exception as e:
        print(f"⚠️ [user_memory] get error: {e}")
        return None
 
 
def all_memories() -> list[dict]:
    col = _col()
    if col is None:
        return []
    try:
        return list(col.find({}, {"_id": 1, "display_name": 1, "interaction_count": 1, "last_seen": 1}))
    except Exception as e:
        print(f"⚠️ [user_memory] list error: {e}")
        return []
 
 
# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------
 
def touch_user(user_id: str, display_name: str) -> None:
    """Create the document on first sight or just bump last_seen + interaction_count."""
    col = _col()
    if col is None:
        return
    now = datetime.now(timezone.utc)
    try:
        col.update_one(
            {"_id": user_id},
            {
                "$set":  {"display_name": display_name, "last_seen": now},
                "$inc":  {"interaction_count": 1},
                "$setOnInsert": {"first_seen": now, "facts": []},
            },
            upsert=True,
        )
    except Exception as e:
        print(f"⚠️ [user_memory] touch error: {e}")
 
 
def add_facts(user_id: str, display_name: str, new_facts: list[str]) -> None:
    """Append new facts, trim to MAX_FACTS (oldest removed first)."""
    if not new_facts:
        return
    col = _col()
    if col is None:
        return
    try:
        touch_user(user_id, display_name)
        doc = col.find_one({"_id": user_id}, {"facts": 1}) or {}
        existing = doc.get("facts", [])
 
        # Deduplicate — skip facts already captured (case-insensitive)
        existing_lower = {f.lower() for f in existing}
        unique_new     = [f for f in new_facts if f.lower() not in existing_lower]
        if not unique_new:
            return
 
        merged = existing + unique_new
        if len(merged) > MAX_FACTS:
            merged = merged[-MAX_FACTS:]
 
        col.update_one({"_id": user_id}, {"$set": {"facts": merged}})
    except Exception as e:
        print(f"⚠️ [user_memory] add_facts error: {e}")
 
 
def add_single_fact(user_id: str, display_name: str, fact: str) -> bool:
    """Manually add one fact. Returns False if already present."""
    col = _col()
    if col is None:
        return False
    try:
        touch_user(user_id, display_name)
        doc = col.find_one({"_id": user_id}, {"facts": 1}) or {}
        existing = doc.get("facts", [])
        if fact.lower() in {f.lower() for f in existing}:
            return False
        merged = (existing + [fact])[-MAX_FACTS:]
        col.update_one({"_id": user_id}, {"$set": {"facts": merged}})
        return True
    except Exception as e:
        print(f"⚠️ [user_memory] add_single error: {e}")
        return False
 
 
def remove_fact_by_index(user_id: str, index: int) -> str | None:
    """Remove a fact by 1-based index. Returns the removed fact or None."""
    col = _col()
    if col is None:
        return None
    try:
        doc = col.find_one({"_id": user_id}, {"facts": 1})
        if not doc:
            return None
        facts = doc.get("facts", [])
        if index < 1 or index > len(facts):
            return None
        removed = facts.pop(index - 1)
        col.update_one({"_id": user_id}, {"$set": {"facts": facts}})
        return removed
    except Exception as e:
        print(f"⚠️ [user_memory] remove error: {e}")
        return None
 
 
def clear_facts(user_id: str) -> bool:
    """Wipe all facts for a user but keep their profile doc."""
    col = _col()
    if col is None:
        return False
    try:
        result = col.update_one({"_id": user_id}, {"$set": {"facts": []}})
        return result.matched_count > 0
    except Exception as e:
        print(f"⚠️ [user_memory] clear error: {e}")
        return False
 
 
def delete_user(user_id: str) -> bool:
    """Fully remove a user's memory document."""
    col = _col()
    if col is None:
        return False
    try:
        result = col.delete_one({"_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"⚠️ [user_memory] delete error: {e}")
        return False
 
 
# ---------------------------------------------------------------------------
# Context helper
# ---------------------------------------------------------------------------
 
def build_memory_note(user_id: str) -> str | None:
    """
    Returns a compact string to inject into the AI prompt, or None if no facts.
    Example: "Known facts about this user: Likes lo-fi music. Lives in the Philippines."
    """
    doc = get_user_memory(user_id)
    if not doc or not doc.get("facts"):
        return None
    facts_text = " ".join(f"{f}." for f in doc["facts"])
    return f"Known facts about this user: {facts_text}"