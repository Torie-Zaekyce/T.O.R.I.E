# T.O.R.I.E. — Agent Guide

## Entrypoints & structure

- **`main.py`** — bot entrypoint. Runs `commands.Bot(command_prefix="t!")`. Processes @mentions for AI chat, moderation, GIF interactions, and minigames via `on_message`.
- **`terminal.py`** — standalone terminal-based Discord client (NOT the bot). Only uses `discord` + `edge-tts`.
- **`bot/`** — shared logic (no commands). `bot/db.py` is the MongoDB singleton; `bot/config.py` has all constants (model names, channel IDs, regex, greetings).
- **`cogs/`** — command groups, one file per concern. Must be registered in `bot/cog_loader.py:8` `COGS` list to load.
- **No `cogs/__init__.py` exists** — namespace packages since Python 3.3; not needed.

## Run & test

```sh
python main.py                  # start bot
pip install -r requirements.txt # deps: discord.py[voice], groq, pymongo[srv], edge-tts
```

No test suite, no lint/typecheck config, no CI/CD. `.env` with `DISCORD_TOKEN`, `GROQ_API_KEY`, `MONGODB_URI`, `KLIPY_API_KEY` required at runtime.

## Key gotchas

- **MongoDB is optional at startup** — if `MONGODB_URI` is unset, the bot runs but data (birthdays, warns, perms, memory, filter words, game sessions) won't persist. All CRUD functions silently no-op.
- **Channel IDs are hardcoded** in `bot/config.py:44-48` — `GENERAL_CHANNEL`, `BIRTHDAY_CHANNEL`, `MUTED_ROLE_ID`, etc. Must match the target server or the bot silently fails (mute, announcements, birthday pings).
- **Family IDs are hardcoded** in `bot/family.py:3-24` — 12 Discord user IDs determine role-based perms. Parents (`TorieRingo`/`Nico`) get `mod`; cousins/uncles/sisters/brother-in-law get `mute unmute warn purge sendmsg`. Others have no default perms.
- **AI provider**: Groq only. Primary model `llama-3.3-70b-versatile`, fallback `llama-3.1-8b-instant`, vision `meta-llama/llama-4-scout-17b-16e-instruct` (all in `bot/config.py:12-14`).
- **Prompt injection defense**: 13 compiled regex patterns in `bot/config.py:20-33` checked via `bot/utils.py:sanitize_input()`. Messages matching any pattern are silently dropped.
- **Mute uses a Discord role** (`MUTED_ROLE_ID` in config). Auto-unmute via `asyncio.create_task` with `asyncio.sleep`. Cancellation tracked in `_mute_tasks` dict in `main.py:33`.
- **Memory extraction**: `bot/user_memory.py:197-231` makes a secondary LLM call (temperature 0.2, 120 tokens) to extract facts from user messages. JSON parsing from response, max 20 facts per user.
- **Personality modes**: Keyword-driven detection in `bot/personality.py:258-265` (priority: roast > hype > advice > game > default). Each mode has separate max_tokens budget (80-250).
- **Timezone**: All scheduled announcements use `Asia/Manila` (pytz). Greeting times hardcoded in `bot/config.py:37-42`.
- **Reply chain**: `bot/utils.py:fetch_reply_chain()` walks up to 6 parent messages for AI context (`MAX_CHAIN_DEPTH` in config).
- **Prefix commands**: `t!` prefix. Slash commands exist (`/sendmsg`) and must call `bot.tree.sync()` after any change.
