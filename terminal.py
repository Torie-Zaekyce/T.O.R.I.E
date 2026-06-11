import asyncio
import os
import sys
import re
import tempfile
from datetime import datetime

import discord
from dotenv import load_dotenv

try:
    import edge_tts
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False

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
        self._voice_client: discord.VoiceClient | None = None
        self._tts_voice: str = "en-US-AriaNeural"

    async def on_ready(self):
        print()
        print(_c("=" * 52, _CYAN, _BOLD))
        print(_c(f"  T.O.R.I.E. Terminal Messenger", _CYAN, _BOLD))
        print(_c(f"  Logged in as {self.user}", _GREEN))
        print(_c(f"  Guilds : {len(self.guilds)}", _GREY))
        print(_c("=" * 52, _CYAN, _BOLD))
        print()
        print(_c("Commands: /watch  /unwatch  /send  /dm  /join  /leave  /vc  /tts  /voice  /voices  /channels  /guilds  /quit", _YELLOW))
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

        elif cmd == "/join":
            await self._cmd_join(parts)

        elif cmd == "/leave":
            await self._cmd_leave()

        elif cmd == "/vc":
            self._cmd_vc()

        elif cmd == "/tts":
            await self._cmd_tts(parts)

        elif cmd == "/voice":
            await self._cmd_set_voice(parts)

        elif cmd == "/voices":
            await self._cmd_voices()

        elif cmd == "/channels":
            self._cmd_channels()

        elif cmd == "/guilds":
            self._cmd_guilds()

        elif cmd in ("/quit", "/exit", "/q"):
            await self._quit()
            return

        else:
            if self.watched_channel:
                try:
                    await self.watched_channel.send(line)
                except discord.Forbidden:
                    print(_c("  ❌ No permission to send in that channel.", _RED))
            else:
                print(_c(f"  ❓ Unknown command: {cmd}  (use /watch first to send bare text)", _YELLOW))

        print(_c(">>> ", _YELLOW), end="", flush=True)

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

    def _cmd_guilds(self):
        print(_c("\n  Guilds the bot is in:", _CYAN))
        for guild in self.guilds:
            print(f"    {_c(guild.name, _BOLD)}  (id: {guild.id}, members: {guild.member_count})")

    async def _cmd_join(self, parts: list):
        if len(parts) < 2:
            print(_c("  Usage: /join <voice channel name or id>", _YELLOW))
            return

        target  = parts[1].strip()
        channel = self._resolve_voice_channel(target)

        if not channel:
            print(_c(f"  ❌ Voice channel not found: {target}  (use /vc to list them)", _RED))
            return

        if self._voice_client and self._voice_client.is_connected():
            if self._voice_client.guild.id == channel.guild.id:
                await self._voice_client.move_to(channel)
                print(_c(f"  🔀 Moved to 🔊 {channel.name} in {channel.guild.name}", _GREEN))
                return
            else:
                await self._voice_client.disconnect()
                self._voice_client = None

        try:
            self._voice_client = await channel.connect()
            members_in_vc = [m.display_name for m in channel.members if not m.bot]
            print(_c(f"  ✅ Joined 🔊 {channel.name} in {channel.guild.name}", _GREEN))
            if members_in_vc:
                print(_c(f"     Members: {', '.join(members_in_vc)}", _GREY))
            else:
                print(_c(f"     Channel is empty.", _GREY))
        except discord.ClientException as e:
            print(_c(f"  ❌ Already connected or connection error: {e}", _RED))
        except discord.Forbidden:
            print(_c("  ❌ No permission to join that voice channel.", _RED))
        except Exception as e:
            print(_c(f"  ❌ Error joining voice: {e}", _RED))

    async def _cmd_leave(self):
        if not self._voice_client or not self._voice_client.is_connected():
            print(_c("  ⚠️  Not connected to any voice channel.", _YELLOW))
            return
        name = self._voice_client.channel.name
        await self._voice_client.disconnect()
        self._voice_client = None
        print(_c(f"  ✅ Left 🔊 {name}", _GREEN))

    def _cmd_vc(self):
        for guild in self.guilds:
            print(_c(f"\n  [{guild.name}]", _MAGENTA, _BOLD))
            for ch in guild.voice_channels:
                perms   = ch.permissions_for(guild.me)
                members = [m.display_name for m in ch.members if not m.bot]
                joined  = _c(" ◄ joined", _GREEN) if (
                    self._voice_client and
                    self._voice_client.is_connected() and
                    self._voice_client.channel.id == ch.id
                ) else ""
                can_join = _c("connect", _BLUE) if perms.connect else _c("no access", _GREY)
                occupants = _c(f"  [{', '.join(members)}]", _CYAN) if members else _c("  [empty]", _GREY)
                print(f"    🔊 {ch.name:<30} {ch.id}  [{can_join}]{occupants}{joined}")

    async def _cmd_tts(self, parts: list):
        if not _TTS_AVAILABLE:
            print(_c("  ❌ edge-tts is not installed. Run: pip install edge-tts", _RED))
            return

        if len(parts) < 2:
            print(_c("  Usage: /tts <text to speak>", _YELLOW))
            return

        if not self._voice_client or not self._voice_client.is_connected():
            print(_c("  ⚠️  Not in a voice channel. Use /join first.", _YELLOW))
            return

        text = parts[1] if len(parts) == 2 else " ".join(parts[1:])

        if self._voice_client.is_playing():
            self._voice_client.stop()

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()

        try:
            print(_c(f"  🗣️  Generating TTS  [{self._tts_voice}] …", _GREY), end="", flush=True)
            communicate = edge_tts.Communicate(text, self._tts_voice)
            await communicate.save(tmp.name)
            print(_c(" done", _GREEN))

            source = discord.FFmpegPCMAudio(tmp.name)

            def after_play(error):
                if error:
                    print(_c(f"\n  ⚠️  TTS playback error: {error}", _YELLOW))
                try:
                    os.unlink(tmp.name)
                except OSError:
                    pass
                print(_c(">>> ", _YELLOW), end="", flush=True)

            self._voice_client.play(source, after=after_play)

        except Exception as e:
            print(_c(f"\n  ❌ TTS error: {e}", _RED))
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    async def _cmd_set_voice(self, parts: list):
        if not _TTS_AVAILABLE:
            print(_c("  ❌ edge-tts is not installed. Run: pip install edge-tts", _RED))
            return

        if len(parts) < 2:
            print(_c(f"  Current voice: {_c(self._tts_voice, _CYAN)}", _RESET))
            print(_c("  Usage: /voice <voice name>  — use /voices to list options", _YELLOW))
            return

        name = parts[1].strip()
        try:
            voices = await edge_tts.list_voices()
            match  = next((v for v in voices if v["ShortName"].lower() == name.lower()), None)
            if not match:
                print(_c(f"  ❌ Voice not found: {name}  (use /voices to see the list)", _RED))
                return
            self._tts_voice = match["ShortName"]
            print(_c(f"  ✅ TTS voice set to {_c(self._tts_voice, _CYAN)}", _GREEN))
        except Exception as e:
            print(_c(f"  ❌ Error fetching voices: {e}", _RED))

    async def _cmd_voices(self):
        if not _TTS_AVAILABLE:
            print(_c("  ❌ edge-tts is not installed. Run: pip install edge-tts", _RED))
            return

        try:
            voices = await edge_tts.list_voices()
        except Exception as e:
            print(_c(f"  ❌ Could not fetch voice list: {e}", _RED))
            return

        # Group by locale for readability
        grouped: dict[str, list] = {}
        for v in voices:
            locale = v["Locale"]
            grouped.setdefault(locale, []).append(v["ShortName"])

        # Highlight English locales first, rest alphabetically
        en_locales  = sorted(k for k in grouped if k.startswith("en-"))
        other       = sorted(k for k in grouped if not k.startswith("en-"))
        ordered     = en_locales + other

        print(_c(f"\n  {len(voices)} voices available  (current: {self._tts_voice})", _CYAN))
        for locale in ordered:
            names = grouped[locale]
            label = _c(f"  {locale:<12}", _MAGENTA)
            for n in names:
                active = _c(" ◄", _GREEN) if n == self._tts_voice else ""
                print(f"{label} {n}{active}")
        print()

    def _resolve_voice_channel(self, target: str) -> discord.VoiceChannel | None:
        if target.isdigit():
            ch = self.get_channel(int(target))
            return ch if isinstance(ch, discord.VoiceChannel) else None
        target_lower = target.lower()
        for guild in self.guilds:
            for ch in guild.voice_channels:
                if ch.name.lower() == target_lower:
                    return ch
        return None

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

    async def _quit(self):
        print(_c("\n  👋 Disconnecting...", _YELLOW))
        if self._voice_client and self._voice_client.is_connected():
            await self._voice_client.disconnect()
        if self._input_task:
            self._input_task.cancel()
        await self.close()


if __name__ == "__main__":
    client = TerminalClient()
    try:
        client.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        pass