import asyncio
import os
import sys
import re
from datetime import datetime

import discord
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    print("❌ DISCORD_TOKEN is missing from .env")
    sys.exit(1)

# ANSI colour helpers
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_GREY   = "\033[90m"
_BLUE   = "\033[94m"
_MAGENTA = "\033[95m"

def _c(text, *codes): return "".join(codes) + str(text) + _RESET
def _ts(): return _c(datetime.now().strftime("%H:%M:%S"), _GREY)


class TerminalClient(discord.Client):

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members         = True
        super().__init__(intents=intents)
        self.watched_channel: discord.TextChannel | None = None
        self._input_task: asyncio.Task | None = None

    # ------------------------------------------------------------------ events

    async def on_ready(self):
        print()
        print(_c("=" * 52, _CYAN, _BOLD))
        print(_c(f"  T.O.R.I.E. Terminal Messenger", _CYAN, _BOLD))
        print(_c(f"  Logged in as {self.user}", _GREEN))
        print(_c(f"  Guilds : {len(self.guilds)}", _GREY))
        print(_c("=" * 52, _CYAN, _BOLD))
        print()
        print(_c("Commands: /watch  /unwatch  /send  /dm  /channels  /guilds  /quit", _YELLOW))
        print()
        self._input_task = asyncio.create_task(self._input_loop())

    async def on_message(self, message: discord.Message):
        if self.watched_channel and message.channel.id == self.watched_channel.id:
            if message.author == self.user:
                prefix = _c(f"[{_ts()}] {_c('YOU', _GREEN, _BOLD)}", _RESET)
            else:
                prefix = _c(f"[{_ts()}] {_c(message.author.display_name, _CYAN, _BOLD)}", _RESET)

            content = message.content or ""

            attachments = ""
            if message.attachments:
                attachments = " " + _c(f"[{len(message.attachments)} attachment(s)]", _GREY)

            embeds = ""
            if message.embeds:
                embeds = " " + _c(f"[embed: {message.embeds[0].title or 'no title'}]", _GREY)

            print(f"\r{prefix}: {content}{attachments}{embeds}")
            print(_c(">>> ", _YELLOW), end="", flush=True)

    # ------------------------------------------------------------------ input loop

    async def _input_loop(self):
        loop = asyncio.get_running_loop()
        print(_c(">>> ", _YELLOW), end="", flush=True)

        while True:
            try:
                raw = await loop.run_in_executor(None, sys.stdin.readline)
            except (EOFError, KeyboardInterrupt):
                await self._quit()
                return

            line = raw.strip()
            if not line:
                print(_c(">>> ", _YELLOW), end="", flush=True)
                continue

            await self._handle_command(line)

    # ------------------------------------------------------------------ command dispatcher

    async def _handle_command(self, line: str):
        parts = line.split(None, 2)
        cmd   = parts[0].lower()

        if cmd in ("/watch", "/sw"):
            await self._cmd_watch(parts)

        elif cmd == "/unwatch":
            if self.watched_channel:
                print(_c(f"  ✅ Stopped watching #{self.watched_channel.name}", _GREEN))
                self.watched_channel = None
            else:
                print(_c("  ⚠️  Not watching any channel.", _YELLOW))

        elif cmd == "/send":
            await self._cmd_send(parts)

        elif cmd == "/dm":
            await self._cmd_dm(parts)

        elif cmd == "/channels":
            self._cmd_channels()

        elif cmd == "/guilds":
            self._cmd_guilds()

        elif cmd in ("/quit", "/exit", "/q"):
            await self._quit()
            return

        else:
            # Bare text with no slash — send to watched channel if one is set
            if self.watched_channel:
                try:
                    await self.watched_channel.send(line)
                except discord.Forbidden:
                    print(_c("  ❌ No permission to send in that channel.", _RED))
            else:
                print(_c(f"  ❓ Unknown command: {cmd}  (use /watch first to send bare text)", _YELLOW))

        print(_c(">>> ", _YELLOW), end="", flush=True)

    # ------------------------------------------------------------------ /watch

    async def _cmd_watch(self, parts: list):
        if len(parts) < 2:
            print(_c("  Usage: /watch <#channel-name or channel_id>", _YELLOW))
            return

        target = parts[1].lstrip("#").strip()
        channel = self._resolve_channel(target)

        if not channel:
            print(_c(f"  ❌ Channel not found: {target}", _RED))
            return

        self.watched_channel = channel
        print(_c(f"  👀 Now watching #{channel.name} in {channel.guild.name}", _GREEN))
        print(_c(f"     Messages will appear here. Type text directly to reply.", _GREY))

        # Show last 5 messages as context
        try:
            history = [m async for m in channel.history(limit=5)]
            history.reverse()
            print(_c(f"  — last {len(history)} message(s) —", _GREY))
            for m in history:
                who = _c(m.author.display_name, _CYAN)
                ts  = _c(m.created_at.strftime("%H:%M"), _GREY)
                print(f"  [{ts}] {who}: {m.content or _c('[no text content]', _GREY)}")
            print(_c("  — live —", _GREY))
        except discord.Forbidden:
            print(_c("  ⚠️  Can't read history (no permission).", _YELLOW))

    # ------------------------------------------------------------------ /send

    async def _cmd_send(self, parts: list):
        if len(parts) < 3:
            print(_c("  Usage: /send <#channel or id> <message>", _YELLOW))
            return

        target  = parts[1].lstrip("#").strip()
        text    = parts[2]
        channel = self._resolve_channel(target)

        if not channel:
            print(_c(f"  ❌ Channel not found: {target}", _RED))
            return

        try:
            await channel.send(text)
            print(_c(f"  ✅ Sent to #{channel.name}", _GREEN))
        except discord.Forbidden:
            print(_c("  ❌ No permission to send in that channel.", _RED))
        except Exception as e:
            print(_c(f"  ❌ Error: {e}", _RED))

    # ------------------------------------------------------------------ /dm

    async def _cmd_dm(self, parts: list):
        if len(parts) < 3:
            print(_c("  Usage: /dm <user_id or username> <message>", _YELLOW))
            return

        target = parts[1].strip()
        text   = parts[2]
        user   = await self._resolve_user(target)

        if not user:
            print(_c(f"  ❌ User not found: {target}", _RED))
            return

        try:
            await user.send(text)
            print(_c(f"  ✅ DM sent to {user.display_name} ({user.name})", _GREEN))
        except discord.Forbidden:
            print(_c(f"  ❌ Can't DM {user.display_name} — they may have DMs disabled.", _RED))
        except Exception as e:
            print(_c(f"  ❌ Error: {e}", _RED))

    # ------------------------------------------------------------------ /channels

    def _cmd_channels(self):
        for guild in self.guilds:
            print(_c(f"\n  [{guild.name}]", _MAGENTA, _BOLD))
            for ch in guild.text_channels:
                perms = ch.permissions_for(guild.me)
                flags = []
                if perms.read_messages:  flags.append(_c("read",  _GREEN))
                if perms.send_messages:  flags.append(_c("send",  _BLUE))
                if not flags:            flags.append(_c("no access", _GREY))
                print(f"    #{ch.name:<30} {ch.id}  [{', '.join(flags)}]")

    # ------------------------------------------------------------------ /guilds

    def _cmd_guilds(self):
        print(_c("\n  Guilds the bot is in:", _CYAN))
        for guild in self.guilds:
            print(f"    {_c(guild.name, _BOLD)}  (id: {guild.id}, members: {guild.member_count})")

    # ------------------------------------------------------------------ helpers

    def _resolve_channel(self, target: str) -> discord.TextChannel | None:
        # Try by ID first
        if target.isdigit():
            ch = self.get_channel(int(target))
            return ch if isinstance(ch, discord.TextChannel) else None
        # Try by name across all guilds
        target_lower = target.lower()
        for guild in self.guilds:
            for ch in guild.text_channels:
                if ch.name.lower() == target_lower:
                    return ch
        return None

    async def _resolve_user(self, target: str) -> discord.User | None:
        # By ID
        if target.isdigit():
            try:
                return await self.fetch_user(int(target))
            except discord.NotFound:
                return None
        # By username across all cached members
        target_lower = target.lower()
        for guild in self.guilds:
            async for member in guild.fetch_members(limit=None):
                if member.name.lower() == target_lower or member.display_name.lower() == target_lower:
                    return member
        return None

    # ------------------------------------------------------------------ quit

    async def _quit(self):
        print(_c("\n  👋 Disconnecting...", _YELLOW))
        if self._input_task:
            self._input_task.cancel()
        await self.close()


if __name__ == "__main__":
    client = TerminalClient()
    try:
        client.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        pass
