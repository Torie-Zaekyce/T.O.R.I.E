# T.O.R.I.E.
### Thoughtful Online Response Intelligence Entity

> A personal Discord bot built with love, dad jokes, and a concerning amount of sarcasm.

T.O.R.I.E. is a feature-rich Discord bot designed for a private server. She chats with AI, manages birthdays, moderates members, sends Klipy GIFs, remembers facts about people, plays minigames, and knows exactly who her family is — and acts accordingly.

---

## Features

### 🤖 AI Chat
T.O.R.I.E. responds when mentioned. She has a distinct personality — sarcastic, warm, occasionally wise — powered by Groq's LLaMA models. She reacts to images, stickers, and knows how to switch to a softer tone when someone needs it. She also gives genuine advice when asked.

### 🎂 Birthdays
Users register their own birthdays. T.O.R.I.E. announces them at midnight PHT in a dedicated birthday channel with a role ping.

### 🎞️ GIF Interactions
Mention T.O.R.I.E. and say `hug`, `kiss`, `pat`, `bite`, `lick`, `punch`, or `kick` at a user — she searches Klipy for an anime GIF and sends it as an embed. Also works via `t!hug @user` or `tor hug @user` (no prefix needed).

### 🚫 Moderation
- Word filter with leet-speak normalization and false-positive protection
- Mute / unmute with custom durations and auto-expiry
- Warn system — warns are stored in MongoDB and trigger an automatic 10-minute mute
- Purge messages in bulk
- All moderation permissions are configurable per-user via `t!perm`

### 🔑 Permission System
No hardcoded moderators (except parents who always have `mod`). Grant any user specific permissions like `mute`, `warn`, `filter`, `purge`, `sendmsg`, or `mod` (all-access). Permissions are stored in MongoDB and survive restarts.

### 📅 Scheduled Announcements
Automatic messages at 7AM, 12PM, 7PM, 7:30PM, and midnight PHT — morning greetings, lunch reminders, dinner reminders, evening check-ins, and midnight chaos.

### 🧠 Memory
T.O.R.I.E. quietly remembers facts about people from conversation — likes, dislikes, running jokes — and brings them up naturally later. Parents can view, add, remove, or wipe anyone's stored memory with `t!memory`.

### 🎮 Minigames
Start a quick game by mentioning her — chess (with a basic AI opponent), tic-tac-toe, or battleship. Game state is stored in MongoDB so sessions survive restarts. Check the current board anytime with `t!board`.

### 📨 Anonymous Messaging
`/sendmsg #channel message` — T.O.R.I.E. sends the message from her account. Only you see the confirmation. Useful for announcements without revealing who sent them.

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Discord | discord.py 2.x |
| AI | Groq API (LLaMA 3.3 70B + LLaMA 3.1 8B fallback) |
| Vision | Groq Vision (Llama 4 Scout) |
| Database | MongoDB Atlas (M0 free tier) |
| GIFs | Klipy GIF API |
| Hosting | Railway |

---

## Project Structure

```
T.O.R.I.E./
│
├── main.py                  ← entry point, Discord events, AI chat, response logic
│
├── bot/
│   ├── __init__.py
│   ├── cog_loader.py         ← loads all cogs on startup
│   ├── family.py             ← family role data + lookup helpers
│   ├── perms.py               ← permission checks + family default perms
│   ├── db.py                 ← MongoDB singleton + all collection CRUD
│   ├── word_filter.py         ← word filter normalization, cache, detection
│   ├── config.py              ← centralized constants, API keys, channel IDs
│   ├── utils.py                ← helper functions (parse_duration, sanitize_input, fetch_reply_chain)
│   ├── moderation.py            ← moderation handlers (warn, mute, unmute, auto-unmute)
│   ├── personality.py            ← AI personality, system prompt, custom traits
│   ├── user_memory.py             ← MongoDB user memory and fact extraction
│   ├── greetings.py                ← scheduled message pools
│   └── minigames.py                 ← chess / tic-tac-toe / battleship session logic
│
├── cogs/
│   ├── __init__.py
│   ├── general.py             ← t!help, t!ping, t!whoami, t!greet, t!family
│   ├── moderation.py            ← t!filter, t!warns, t!purge, /sendmsg
│   ├── birthday.py               ← t!birthday (add / remove / list / today)
│   ├── personality.py             ← t!personality (add / remove / list / clear)
│   ├── permissions.py              ← t!perm (add / remove / list)
│   ├── memory.py                    ← t!memory (view / add / remove / clear / delete / list)
│   └── interactions.py               ← GIF interactions, t!tor, t!board
│
├── .env                      ← local secrets (never commit)
├── .env.example              ← key template
├── .gitignore
├── requirements.txt
├── Procfile
└── README.md
```

### Architecture Notes

**Cog-based design:** Commands are split into single-responsibility cogs under `cogs/`, loaded dynamically at startup via `bot/cog_loader.py`. Shared logic (family data, permissions, database access, word filtering) lives in `bot/` so every cog pulls from the same source of truth instead of duplicating it.

- **bot/family.py** — Family role dictionaries and `get_role()` lookup helpers
- **bot/perms.py** — `has_permission()` checks, valid permission list, family default perm table
- **bot/db.py** — Single MongoDB client + every collection's CRUD functions (birthdays, warns, perms, filter words)
- **bot/word_filter.py** — Leet-speak normalization, filtered word cache, detection logic
- **bot/config.py** — All constants, channel IDs, model names, and regex patterns compiled at import time for performance
- **bot/utils.py** — Reusable functions for text processing, duration parsing, and Discord context handling
- **bot/moderation.py** — Self-contained moderation logic with embed creation and role management
- **bot/personality.py** — AI personality system with advice detection and custom traits
- **bot/user_memory.py** — MongoDB integration for persistent user facts and memory extraction
- **bot/minigames.py** — Game session state and board rendering for chess, tic-tac-toe, and battleship
- **cogs/** — All user-facing commands (prefix, slash, interactions), one cog per concern

**Performance Optimizations:**
- Regex patterns compiled at module load time (not on every function call)
- Efficient advice detection using precompiled regex instead of substring iteration
- Normalized word filter with leet-speak protection

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/Torie-Zaekyce/T.O.R.I.E.git
cd T.O.R.I.E.
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your keys:

```env
DISCORD_TOKEN=        # Bot token from discord.com/developers
GROQ_API_KEY=         # From console.groq.com
MONGODB_URI=          # From MongoDB Atlas → Connect → Drivers
KLIPY_API_KEY=        # From klipy.com/developers (free)
```

### 4. MongoDB Atlas setup

Create a free M0 cluster at [cloud.mongodb.com](https://cloud.mongodb.com).

T.O.R.I.E. will auto-create these collections inside a `torie` database:

| Collection | Stores |
|---|---|
| `birthdays` | User birthday registrations |
| `filtered_words` | Custom word filter list |
| `warns` | User warning history |
| `permissions` | Custom permission grants |
| `user_memory` | User facts and interaction history |
| `game_sessions` | Active/recent minigame board state |

### 5. Run locally
```bash
python main.py
```

---

## Commands

### 🤖 General
| Command | Description |
|---|---|
| `t!ping` | Check latency |
| `t!whoami` | Find out who you are to T.O.R.I.E. |
| `t!greet` | Get a personalized greeting |
| `t!family` | See T.O.R.I.E.'s whole family tree |
| `t!purge <1-100>` | Bulk delete messages *(perm: purge)* |

### 💬 Chat
| Trigger | Description |
|---|---|
| `@T.O.R.I.E. <message>` | Chat with her |
| `@T.O.R.I.E. + image` | She reacts to your image |
| `@T.O.R.I.E. + sticker` | She reacts to your sticker |
| `@T.O.R.I.E. advice on <topic>` | Genuine advice mode |
| `@T.O.R.I.E. hug/kiss/pat @user` | GIF interaction via mention |
| `t!hug/kiss/pat/bite/lick/punch/kick @user` | GIF interaction via command |
| `tor hug @user` | Prefix-free shortcut |
| `@T.O.R.I.E. let's play chess / tic tac toe / battleship` | Start a minigame |
| `t!board` | Show the current game board |

### 🚫 Moderation
| Command | Description | Permission |
|---|---|---|
| `@T.O.R.I.E. warn @user [reason]` | Warn + auto-mute 10min | `warn` |
| `@T.O.R.I.E. mute @user [duration]` | Mute a user | `mute` |
| `@T.O.R.I.E. unmute @user` | Unmute a user | `unmute` |
| `t!warns @user` | View warn history | anyone |
| `t!warns @user clear` | Clear warns | `warn` |
| `t!filter add/remove/list/clear` | Manage word filter | `filter` |
| `/sendmsg #channel <message>` | Send anonymous message | `sendmsg` |

**Mute duration examples:** `10m`, `1h`, `2d`, `1w` — defaults to 10 minutes if not specified.

### 🔑 Permissions
| Command | Description |
|---|---|
| `t!perm add @user <perm>` | Grant a permission *(parents only)* |
| `t!perm remove @user <perm>` | Revoke a permission *(parents only)* |
| `t!perm list [@user]` | View someone's permissions |

**Available perms:** `mute` `unmute` `filter` `personality` `purge` `sendmsg` `warn` `mod`

`mod` grants all permissions at once.

Family members have default permissions without needing a grant — parents have `mod`, everyone else has `mute unmute warn purge sendmsg`.

### 🎂 Birthdays
| Command | Description |
|---|---|
| `t!birthday add <MM-DD>` | Register your birthday |
| `t!birthday remove` | Remove your birthday |
| `t!birthday list` | Browse all birthdays |
| `t!birthday today` | Check today's birthdays |

### 🧠 Personality
| Command | Description | Permission |
|---|---|---|
| `t!personality add <trait>` | Add a custom trait | `personality` |
| `t!personality remove <number>` | Remove a trait | `personality` |
| `t!personality list` | View active traits | anyone |
| `t!personality clear` | Clear all traits | `personality` |

### 🧠 Memory
| Command | Description | Permission |
|---|---|---|
| `t!memory view [@user]` | View memories for yourself or a user | anyone (own); parents for others |
| `t!memory add @user <fact>` | Manually add a fact | parents only |
| `t!memory remove @user <number>` | Remove a fact by number | parents only |
| `t!memory clear @user` | Wipe all facts for a user | parents only |
| `t!memory delete @user` | Fully remove a user from memory | parents only |
| `t!memory list` | List all users T.O.R.I.E. remembers | parents only |

---

## Hosting

Deployed on [Railway](https://railway.app) — push to `main`, Railway builds and runs `python main.py` via the `Procfile`. No special configuration needed beyond setting the environment variables in the Railway dashboard.

---

## Family

T.O.R.I.E. knows her family and treats them differently — special greetings, warmer AI context, and default moderation permissions.

| Role | Username |
|---|---|
| 🛠️ Dad (Creator) | TorieRingo |
| 💙 Mom (Co-Creator) | Nico |
| 🌟 Starry Cousin | Stelle |
| 🥐 Bread Cousin | Crois |
| 📚 Curious Cousin | Hyuluk |
| ❤️ Serious Cousin | Mimi |
| 🐐 Goated Uncle | Cacolate |
| 🥖 Chimera Uncle | Vari |
| 🧀 AI Sister | Abby |
| 🩷 Sister | Kde |
| 🩷 Sister | Kio |
| 🖤 Brother-in-Law | Haru |

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Bot token from Discord Developer Portal |
| `GROQ_API_KEY` | ✅ | Groq API key for AI responses |
| `MONGODB_URI` | ✅ | MongoDB Atlas connection string |
| `KLIPY_API_KEY` | ✅ | Klipy GIF API key (free at klipy.com/developers) |

---

## License

Private project. Not open source. Built for a personal server.

---

*T.O.R.I.E. — Thoughtful Online Response Intelligence Entity*
*"I am definitely not hiding any bugs. 😇"*