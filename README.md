# T.O.R.I.E.
### Thoughtful Online Response Intelligence Entity

> A personal Discord bot built with love, dad jokes, and a concerning amount of sarcasm.

T.O.R.I.E. is a feature-rich Discord bot designed for a private server. She chats with AI, plays music, manages birthdays, moderates members, sends Klipy GIFs, and knows exactly who her family is — and acts accordingly.

---

## Features

### 🤖 AI Chat
T.O.R.I.E. responds when mentioned. She has a distinct personality — sarcastic, warm, occasionally wise — powered by Groq's LLaMA models. She reacts to images, stickers, and knows how to switch to a softer tone when someone needs it. She also gives genuine advice when asked.

### 🎵 Music
Full music playback from Spotify, Deezer, and YouTube via yt-dlp. Supports queues, shuffle, looping, volume control, and skip/pause/resume. Music requires a self-hosted VPS (Railway bans music bots).

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
| Music | yt-dlp + Spotify API + Deezer |
| Database | MongoDB Atlas (M0 free tier) |
| GIFs | Klipy GIF API |
| Hosting | Railway (chat) + Oracle VPS (music) |

---

## Project Structure

```
T.O.R.I.E./
│
├── main.py                  ← entry point, bot events, moderation handlers
│
├── bot/
│   ├── __init__.py
│   ├── commands.py          ← all prefix + slash commands
│   ├── personality.py       ← AI personality, system prompt, custom traits
│   ├── greetings.py         ← scheduled message pools
│   └── music.py             ← music system
│
├── .env                     ← local secrets (never commit)
├── .env.example             ← key template
├── .gitignore
├── requirements.txt
├── Procfile
└── README.md
```

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
SPOTIFY_CLIENT_ID=    # From developer.spotify.com
SPOTIFY_CLIENT_SECRET=
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

### 🎵 Music
| Command | Description |
|---|---|
| `t!play <song/URL>` | Play from YouTube, Spotify, or Deezer |
| `t!skip` | Skip current song |
| `t!pause` / `t!resume` | Pause or resume |
| `t!queue` | Show the queue |
| `t!clearqueue` | Clear the queue |
| `t!shuffle` | Shuffle the queue |
| `t!loop song/queue/off` | Set loop mode |
| `t!nowplaying` | Show current track |
| `t!volume <1-100>` | Set volume |
| `t!stop` | Stop and disconnect |

---

## Hosting

### Chat-only (Railway)
Railway works for everything except music. Push to GitHub and Railway auto-deploys.

```
# Procfile
worker: python main.py
```

Set all environment variables in the Railway dashboard under **Variables**.

### Music (Oracle VPS or any self-hosted server)
Railway bans music bots. For music, deploy to a free Oracle Cloud VM (ARM A1 Flex, always free):

```bash
# Install dependencies
sudo apt update && sudo apt install python3-pip ffmpeg -y
pip install -r requirements.txt

# Run with pm2 or screen
screen -S torie
python main.py
# Ctrl+A, D to detach
```

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
| `SPOTIFY_CLIENT_ID` | ⚠️ Music only | Spotify Developer App client ID |
| `SPOTIFY_CLIENT_SECRET` | ⚠️ Music only | Spotify Developer App client secret |

---

## License

Private project. Not open source. Built for a personal server.

---

*T.O.R.I.E. — Thoughtful Online Response Intelligence Entity*
*"I am definitely not hiding any bugs. 😇"*