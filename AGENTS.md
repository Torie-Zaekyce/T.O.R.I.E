# T.O.R.I.E. — Agent Guide

## Entrypoints & structure

- **`main.py`** — bot entrypoint. `commands.Bot(command_prefix="t!")`. All chat, moderation, GIF, and minigame behavior runs through `on_message` (see flow order below).
- **`terminal.py`** — standalone terminal-based Discord client, NOT the bot. Only imports `discord` + `dotenv`; `edge_tts` is imported lazily.
- **`bot/`** — shared logic (no commands). `bot/db.py` = MongoDB singleton; `bot/config.py` = constants (model names, channel/role IDs, injection regex, greeting times); `bot/perms.py` = permission checks + family defaults.
- **`cogs/`** — command groups (general, moderation_commands, birthday, personality, permissions, memory, interactions, voice). Must be in the `COGS` list in `bot/cog_loader.py:8`. No `cogs/__init__.py` exists — namespace packages; don't add one.

## Run & test

```sh
python main.py                  # start bot (needs .env)
pip install -r requirements.txt # discord.py[voice], groq, pymongo[srv], pytz, certifi, aiohttp, python-dotenv, edge-tts
```

No test suite, no lint/typecheck config, no CI. `.env` requires `DISCORD_TOKEN`, `GROQ_API_KEY`, `MONGODB_URI`, `KLIPY_API_KEY` (`SPOTIFY_*` keys exist in `.env` but are unused in code).

## on_message flow (main.py:300) — order matters

1. `t!` prefix → `process_commands`, returns (prefix commands bypass the word filter).
2. Word filter runs on EVERY message — deletes + warns, before any mention check.
3. `tor <action> @user` → GIF interaction (prefix-free; still no mention needed).
4. Torie not @mentioned → return; everything below requires a mention.
5. Stickers / image attachments → dedicated vision/sticker replies.
6. Mentioned-target keywords: `warn`, `mute`/`unmute`, GIF actions.
7. `INJECTION_REGEX` checked before `sanitize_input` (rejects >800 chars / `MAX_MESSAGE_LENGTH`).

## Key gotchas

- **MongoDB is optional at startup** — no `MONGODB_URI` → bot runs but birthdays, warns, perms, memory, filter words don't persist; all CRUD silently no-ops.
- **Hardcoded IDs** in `bot/config.py:46-50` (`GENERAL_CHANNEL`, `BIRTHDAY_CHANNEL`, `BIRTHDAY_PING_ROLE`, `MUTED_ROLE_ID`, `MUTED_CHANNEL_ID`). If they don't match the server, mute/announcements/birthday pings silently fail.
- **Family identity** = 12 hardcoded user IDs in `bot/family.py:3-24`; **family default perms** live in `bot/perms.py:8-21` (parents `mod`, everyone else `mute unmute warn purge sendmsg`). `VALID_PERMS` in `bot/perms.py:6`.
- **Mute is currently broken** — auto-unmute tasks are stored on `bot._mute_tasks`, but nothing ever initializes that dict (a commit removed `bot._mute_tasks = {}`). Mention path passes an undefined `_mute_tasks` global (main.py:413,418 → NameError); slash path reads `self.bot._mute_tasks` (cogs/moderation_commands.py → AttributeError). Fix = initialize `bot._mute_tasks = {}`.
- **AI provider**: Groq only. Models in `bot/config.py:12-14`. `_call_groq` (main.py:83) retries primary → fallback on 429 with exponential backoff; `GROQ_FALLBACK` is also used for fact extraction.
- **Prompt injection defense**: 12 compiled patterns in `bot/config.py:22-35`, checked via `bot/utils.py:sanitize_input()` plus a second `INJECTION_REGEX.search` in on_message. Also: any injected message in the reply chain drops the whole chain (`fetch_reply_chain`), and bot replies pass through `sanitize_reply`.
- **Memory extraction**: `bot/user_memory.py:147` `extract_and_save_facts` — secondary LLM call (temp 0.2, 120 tokens), returns JSON array, capped at `MAX_FACTS=20`. Run off the hot path via `asyncio.to_thread`.
- **Personality modes**: `bot/personality.py:260` `detect_mode` — priority roast > hype > advice > game > default; each mode has its own max_tokens budget (80-250).
- **Minigame sessions are in-memory only** (`bot/minigames.py`) — keyed `(channel_id, user_id)`, expire after 30 min. NOT persisted to MongoDB (README's "sessions survive restarts" is stale). Board embeds parse `<<BOARD>>`/`<<TTT>>`/`<<BSHIP>>` markers out of the model reply.
- **Schedules**: `main.py:237` loop ticks every minute; sends greetings at 7AM/12PM/7PM/7:30PM/midnight + birthday ping at midnight, all `Asia/Manila` (pytz).
- **Prefix + slash**: every `t!` command has a `/` twin. New slash commands must be registered via `bot.tree.add_command()` in the cog's `setup()`; `bot.tree.sync()` runs once in `on_ready` (main.py:293).
- **Reply chain**: `bot/utils.py:65` `fetch_reply_chain` walks ≤6 parents (`MAX_CHAIN_DEPTH` in config) for AI context.
