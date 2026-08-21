import json
import re
from datetime import datetime, timezone

from bot.config import reasoning_kwargs
from bot.db import get_memory_col

MAX_FACTS = 20
_CODE_BLOCK_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.DOTALL)


def _col():
    return get_memory_col()


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


def touch_user(user_id: str, display_name: str) -> None:
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
    if not new_facts:
        return
    col = _col()
    if col is None:
        return
    try:
        touch_user(user_id, display_name)
        doc = col.find_one({"_id": user_id}, {"facts": 1}) or {}
        existing = doc.get("facts", [])
        existing_lower = {f.lower() for f in existing}
        unique_new = [f for f in new_facts if f.lower() not in existing_lower]
        if not unique_new:
            return
        merged = existing + unique_new
        if len(merged) > MAX_FACTS:
            merged = merged[-MAX_FACTS:]
        col.update_one({"_id": user_id}, {"$set": {"facts": merged}})
    except Exception as e:
        print(f"⚠️ [user_memory] add_facts error: {e}")


def add_single_fact(user_id: str, display_name: str, fact: str) -> bool:
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
    col = _col()
    if col is None:
        return False
    try:
        result = col.delete_one({"_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"⚠️ [user_memory] delete error: {e}")
        return False


def build_memory_note(user_id: str) -> str | None:
    doc = get_user_memory(user_id)
    if not doc or not doc.get("facts"):
        return None
    facts_text = " ".join(f"{f}." for f in doc["facts"])
    return f"Known facts about this user: {facts_text}"


def extract_and_save_facts(user_id: str, display_name: str, user_message: str, groq_client, model: str) -> None:
    if not user_message or len(user_message.strip()) < 8:
        return
    try:
        prompt = (
            "Extract short, durable facts about the user from their message. "
            "Only extract things that are genuinely personal and worth remembering long-term "
            "(e.g. hobbies, job, personality traits, preferences, relationships, feelings they've expressed). "
            "Do NOT extract greetings, questions directed at the bot, or one-off throwaway comments. "
            "Return ONLY a JSON array of strings, max 3 items. "
            "If nothing worth remembering exists, return an empty array []. "
            "Example output: [\"Likes playing Genshin Impact\", \"Studies computer science\"]"
        )
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=120,
            temperature=0.2,
        )
        kwargs.update(reasoning_kwargs(model))
        response = groq_client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content.strip()
        raw = _CODE_BLOCK_RE.sub("", raw).strip()
        facts = json.loads(raw)
        if isinstance(facts, list) and facts:
            clean = [str(f).strip() for f in facts if isinstance(f, str) and f.strip()]
            if clean:
                add_facts(user_id, display_name, clean)
                print(f"🧠 [user_memory] Saved {len(clean)} fact(s) for {display_name}: {clean}")
    except Exception as e:
        print(f"⚠️ [user_memory] extract_and_save_facts error: {e}")
