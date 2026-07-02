# cogs/moderation.py — Moderation: filter, warns, purge, /sendmsg

import asyncio
import io
import re

import aiohttp
import discord
from discord.ext import commands
from bot.config import (
    MUTED_ROLE_ID,
    MUTED_CHANNEL_ID,
)

from bot.db import load_warns, add_warn, clear_warns
from bot.perms import has_permission, VALID_PERMS
from bot.family import get_parent_role
from bot.word_filter import (
    FILTERED_WORDS,
    add_word, remove_word, clear_all_words,
)

_MSG_LINK_RE          = re.compile(r"https?://(?:ptb\.|canary\.)?discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)")
_MENTION_AVOIDANCE_RE = re.compile(r"@everyone|@here")
_MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024


class ModerationCog(commands.Cog, name="Moderation"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -----------------------------------------------------------------------
    # t!filter
    # -----------------------------------------------------------------------

    @commands.group(name="filter", invoke_without_command=True)
    async def filter_group(self, ctx):
        await ctx.send(embed=discord.Embed(
            description="Usage: `t!filter add <word>` | `t!filter remove <word>` | `t!filter list` | `t!filter clear`",
            color=discord.Color.red()
        ))

    @filter_group.command(name="add")
    async def filter_add(self, ctx, *, word: str):
        if not has_permission(ctx.author, "filter"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to manage the filter.", color=discord.Color.red()))
            return
        word = word.lower().strip()
        if add_word(word):
            await ctx.send(embed=discord.Embed(description=f"✅ Added `{word}` to the filter list. 👀", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description=f"⚠️ `{word}` is already in the filter list.", color=discord.Color.orange()))

    @filter_group.command(name="remove")
    async def filter_remove(self, ctx, *, word: str):
        if not has_permission(ctx.author, "filter"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to manage the filter.", color=discord.Color.red()))
            return
        if remove_word(word.lower().strip()):
            await ctx.send(embed=discord.Embed(description=f"✅ Removed `{word.strip()}` from the filter list.", color=discord.Color.green()))
        else:
            await ctx.send(embed=discord.Embed(description=f"⚠️ `{word.strip()}` isn't in the filter list.", color=discord.Color.orange()))

    @filter_group.command(name="list")
    async def filter_list(self, ctx):
        if not has_permission(ctx.author, "filter"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to view the filter list.", color=discord.Color.red()))
            return
        if not FILTERED_WORDS:
            await ctx.send(embed=discord.Embed(description="📋 The filter list is empty.", color=discord.Color.greyple()))
            return
        embed = discord.Embed(
            title       = "🚫 Filtered Words",
            description = "\n".join(f"• `{w}`" for w in FILTERED_WORDS),
            color       = discord.Color.red()
        )
        embed.set_footer(text=f"{len(FILTERED_WORDS)} word(s) currently filtered")
        await ctx.send(embed=embed)

    @filter_group.command(name="clear")
    async def filter_clear(self, ctx):
        if not has_permission(ctx.author, "filter"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to clear the filter.", color=discord.Color.red()))
            return
        count = clear_all_words()
        await ctx.send(embed=discord.Embed(description=f"✅ Cleared all {count} filtered word(s). 🧹", color=discord.Color.green()))

    # -----------------------------------------------------------------------
    # t!warns
    # -----------------------------------------------------------------------

    @commands.command(name="warns")
    async def warns_cmd(self, ctx, member: discord.Member = None, action: str = None):
        if not member:
            await ctx.send(embed=discord.Embed(
                description="Usage: `t!warns @user` — view warns | `t!warns @user clear` — clear warns",
                color=discord.Color.orange()
            ))
            return
        if action and action.lower() == "clear":
            if not has_permission(ctx.author, "warn"):
                await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to clear warnings.", color=discord.Color.red()))
                return
            clear_warns(str(member.id))
            await ctx.send(embed=discord.Embed(description=f"✅ Cleared all warnings for {member.mention}.", color=discord.Color.green()))
            return
        warns = load_warns(str(member.id))
        if not warns:
            await ctx.send(embed=discord.Embed(description=f"✅ {member.mention} has no warnings. Clean record! 🌟", color=discord.Color.green()))
            return
        lines = [
            f"`{i}.` **{w.get('reason', 'No reason')}** — by {w.get('mod', '?')} at {w.get('time', '?')}"
            for i, w in enumerate(warns, 1)
        ]
        embed = discord.Embed(
            title       = f"⚠️ Warnings — {member.display_name}",
            description = "\n".join(lines),
            color       = discord.Color.orange()
        )
        embed.set_footer(text=f"{len(warns)} warning(s) total")
        await ctx.send(embed=embed)

    # -----------------------------------------------------------------------
    # t!purge
    # -----------------------------------------------------------------------

    # ── Slash: filter group ──────────────────────────────────────────────────

    filter_group_slash = discord.app_commands.Group(name="filter", description="Manage the word filter")

    @filter_group_slash.command(name="add", description="Add a word to the filter")
    @discord.app_commands.describe(word="The word to filter")
    async def filter_add_slash(self, interaction: discord.Interaction, word: str):
        if not has_permission(interaction.user, "filter"):
            await interaction.response.send_message("⛔ You don't have permission to manage the filter.", ephemeral=True)
            return
        word = word.lower().strip()
        if add_word(word):
            await interaction.response.send_message(f"✅ Added `{word}` to the filter list. 👀")
        else:
            await interaction.response.send_message(f"⚠️ `{word}` is already in the filter list.")

    @filter_group_slash.command(name="remove", description="Remove a word from the filter")
    @discord.app_commands.describe(word="The word to remove")
    async def filter_remove_slash(self, interaction: discord.Interaction, word: str):
        if not has_permission(interaction.user, "filter"):
            await interaction.response.send_message("⛔ You don't have permission to manage the filter.", ephemeral=True)
            return
        if remove_word(word.lower().strip()):
            await interaction.response.send_message(f"✅ Removed `{word.strip()}` from the filter list.")
        else:
            await interaction.response.send_message(f"⚠️ `{word.strip()}` isn't in the filter list.")

    @filter_group_slash.command(name="list", description="List all filtered words")
    async def filter_list_slash(self, interaction: discord.Interaction):
        if not has_permission(interaction.user, "filter"):
            await interaction.response.send_message("⛔ You don't have permission to view the filter list.", ephemeral=True)
            return
        if not FILTERED_WORDS:
            await interaction.response.send_message("📋 The filter list is empty.")
            return
        embed = discord.Embed(
            title="🚫 Filtered Words",
            description="\n".join(f"• `{w}`" for w in FILTERED_WORDS),
            color=discord.Color.red()
        )
        embed.set_footer(text=f"{len(FILTERED_WORDS)} word(s) currently filtered")
        await interaction.response.send_message(embed=embed)

    @filter_group_slash.command(name="clear", description="Clear all filtered words")
    async def filter_clear_slash(self, interaction: discord.Interaction):
        if not has_permission(interaction.user, "filter"):
            await interaction.response.send_message("⛔ You don't have permission to clear the filter.", ephemeral=True)
            return
        count = clear_all_words()
        await interaction.response.send_message(f"✅ Cleared all {count} filtered word(s). 🧹")

    # ── Slash: warns ─────────────────────────────────────────────────────────

    @discord.app_commands.command(name="warns", description="View or clear a user's warnings")
    @discord.app_commands.describe(member="The user to check", action="Optionally clear all warnings")
    @discord.app_commands.choices(action=[
        discord.app_commands.Choice(name="clear", value="clear"),
    ])
    async def warns_slash(self, interaction: discord.Interaction, member: discord.Member, action: str | None = None):
        if not member:
            await interaction.response.send_message("⚠️ Please specify a user.", ephemeral=True)
            return
        if action and action.lower() == "clear":
            if not has_permission(interaction.user, "warn"):
                await interaction.response.send_message("⛔ You don't have permission to clear warnings.", ephemeral=True)
                return
            clear_warns(str(member.id))
            await interaction.response.send_message(f"✅ Cleared all warnings for {member.mention}.")
            return
        warns = load_warns(str(member.id))
        if not warns:
            await interaction.response.send_message(f"✅ {member.mention} has no warnings. Clean record! 🌟")
            return
        lines = [
            f"`{i}.` **{w.get('reason', 'No reason')}** — by {w.get('mod', '?')} at {w.get('time', '?')}"
            for i, w in enumerate(warns, 1)
        ]
        embed = discord.Embed(
            title=f"⚠️ Warnings — {member.display_name}",
            description="\n".join(lines),
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"{len(warns)} warning(s) total")
        await interaction.response.send_message(embed=embed)

    # ── Slash: purge ─────────────────────────────────────────────────────────

    @discord.app_commands.command(name="purge", description="Bulk delete messages (1-100)")
    @discord.app_commands.describe(amount="Number of messages to delete (1-100)")
    async def purge_slash(self, interaction: discord.Interaction, amount: int):
        if not has_permission(interaction.user, "purge"):
            await interaction.response.send_message("⛔ You don't have permission to purge messages.", ephemeral=True)
            return
        if not (1 <= amount <= 100):
            await interaction.response.send_message("⚠️ Please provide a number between 1 and 100.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(f"🗑️ Deleted **{len(deleted)}** message(s).")
        except discord.Forbidden:
            await interaction.followup.send("⛔ I don't have permission to delete messages here.")

    # ── Slash: warn / mute / unmute ──────────────────────────────────────────

    @discord.app_commands.command(name="warn", description="Warn a user with auto-mute for 10 minutes")
    @discord.app_commands.describe(member="The user to warn", reason="Reason for the warning")
    async def warn_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if not has_permission(interaction.user, "warn"):
            await interaction.response.send_message("⛔ You don't have permission to warn users.", ephemeral=True)
            return
        await interaction.response.defer()
        warn_count = add_warn(str(member.id), reason, interaction.user.display_name)
        await interaction.followup.send(
            embed=discord.Embed(
                title="⚠️ User Warned",
                description=f"{member.mention} has been warned!\n**Reason:** {reason}\n**Total warnings:** {warn_count}\nAuto-muted for **10 minutes**.",
                color=discord.Color.orange()
            )
        )
        muted_role = interaction.guild.get_role(MUTED_ROLE_ID)
        muted_ch = self.bot.get_channel(MUTED_CHANNEL_ID)
        if muted_role:
            try:
                await member.add_roles(muted_role, reason=f"Warned by {interaction.user} — auto-mute")
                if muted_ch:
                    warn_embed = discord.Embed(
                        title="⚠️ You have been warned and muted",
                        description=f"Hey {member.mention}, you've been warned!\n**Reason:** {reason}\n**Total warnings:** {warn_count}\nYou are automatically muted for **10 minutes**.",
                        color=discord.Color.orange()
                    )
                    warn_embed.set_footer(text=f"Warned by {interaction.user.display_name}")
                    warn_msg = await muted_ch.send(embed=warn_embed)
                    await warn_msg.delete(delay=180)
                from bot.moderation import auto_unmute
                task = asyncio.create_task(auto_unmute(member, muted_role, 600, muted_ch, self.bot))
            except discord.Forbidden:
                pass

    @discord.app_commands.command(name="mute", description="Mute a user for a specified duration")
    @discord.app_commands.describe(member="The user to mute", duration="Duration like 10m, 1h, 2d (default 10m)")
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, duration: str | None = None):
        if not has_permission(interaction.user, "mute"):
            await interaction.response.send_message("⛔ You don't have permission to mute users.", ephemeral=True)
            return
        from bot.utils import parse_duration, fmt_duration
        dur = parse_duration(duration) if duration else None
        from datetime import timedelta as _td
        dur = dur or _td(minutes=10)
        default = not bool(duration)
        if dur > _td(days=28):
            await interaction.response.send_message("⚠️ Maximum mute duration is 28 days.", ephemeral=True)
            return
        await interaction.response.defer()
        duration_str = fmt_duration(dur)
        muted_role = interaction.guild.get_role(MUTED_ROLE_ID)
        if not muted_role:
            await interaction.followup.send("⛔ Muted role not found. Contact an admin.")
            return
        try:
            if member.id in self.bot._mute_tasks:
                self.bot._mute_tasks[member.id].cancel()
            await member.add_roles(muted_role, reason=f"Muted by {interaction.user} via T.O.R.I.E.")
            desc = f"🔇 Muted {member.mention} for **{duration_str}**."
            if default:
                desc += " *(no duration specified — defaulted to 10 minutes)*"
            await interaction.followup.send(embed=discord.Embed(description=desc, color=discord.Color.red()))
            muted_ch = self.bot.get_channel(MUTED_CHANNEL_ID)
            if muted_ch:
                mute_embed = discord.Embed(
                    title="🔇 You have been muted",
                    description=f"Hey {member.mention}, you've been muted for **{duration_str}**.\nYou can only see this channel while muted.\nYour mute will be lifted automatically.",
                    color=discord.Color.red()
                )
                mute_embed.set_footer(text=f"Muted by {interaction.user.display_name}")
                mute_msg = await muted_ch.send(embed=mute_embed)
                await mute_msg.delete(delay=180)
            from bot.moderation import auto_unmute
            task = asyncio.create_task(auto_unmute(member, muted_role, int(dur.total_seconds()), muted_ch, self.bot))
            self.bot._mute_tasks[member.id] = task
        except discord.Forbidden:
            await interaction.followup.send("⛔ I don't have permission to mute that user.")

    @discord.app_commands.command(name="unmute", description="Unmute a user early")
    @discord.app_commands.describe(member="The user to unmute")
    async def unmute_slash(self, interaction: discord.Interaction, member: discord.Member):
        if not has_permission(interaction.user, "unmute"):
            await interaction.response.send_message("⛔ You don't have permission to unmute users.", ephemeral=True)
            return
        await interaction.response.defer()
        try:
            if member.id in self.bot._mute_tasks:
                self.bot._mute_tasks[member.id].cancel()
                self.bot._mute_tasks.pop(member.id, None)
            muted_role = interaction.guild.get_role(MUTED_ROLE_ID)
            if muted_role and muted_role in member.roles:
                await member.remove_roles(muted_role, reason=f"Unmuted by {interaction.user} via T.O.R.I.E.")
            await interaction.followup.send(embed=discord.Embed(description=f"🔊 Unmuted {member.mention}. Welcome back!", color=discord.Color.green()))
            muted_ch = self.bot.get_channel(MUTED_CHANNEL_ID)
            if muted_ch:
                done_msg = await muted_ch.send(embed=discord.Embed(description=f"🔊 {member.mention} has been unmuted early. Welcome back!", color=discord.Color.green()))
                await done_msg.delete(delay=180)
        except discord.Forbidden:
            await interaction.followup.send("⛔ I don't have permission to unmute that user.")

    @commands.command(name="purge")
    async def purge(self, ctx, amount: int = None):
        if not has_permission(ctx.author, "purge"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to purge messages.", color=discord.Color.red()))
            return
        if amount is None or not (1 <= amount <= 100):
            await ctx.send(embed=discord.Embed(description="⚠️ Please provide a number between 1 and 100. Example: `t!purge 50`", color=discord.Color.orange()))
            return
        try:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=amount)
            confirm = await ctx.send(f"🗑️ Deleted **{len(deleted)}** message(s).")
            await confirm.delete(delay=3)
        except discord.Forbidden:
            await ctx.send(embed=discord.Embed(description="⛔ I don't have permission to delete messages here.", color=discord.Color.red()))
        except Exception as e:
            print(f"❌ Purge error: {e}")

    # -----------------------------------------------------------------------
    # /sendmsg  (slash command)
    # -----------------------------------------------------------------------

    @discord.app_commands.command(name="sendmsg", description="Send a message and/or file to a channel as T.O.R.I.E.")
    @discord.app_commands.describe(
        channel    = "The channel to send to",
        message    = "The text message to send (optional if attachment provided)",
        attachment = "A file, image, or video to attach (optional if message provided)",
        reply_to   = "Paste a message link to reply to a specific message (optional)",
    )
    async def sendmsg(
        self,
        interaction: discord.Interaction,
        channel:     discord.TextChannel,
        message:     str | None                = None,
        attachment:  discord.Attachment | None = None,
        reply_to:    str | None                = None,
    ):
        if not has_permission(interaction.user, "sendmsg"):
            await interaction.response.send_message("⛔ You don't have permission to use this command.", ephemeral=True)
            return
        if not message and not attachment:
            await interaction.response.send_message("⚠️ You must provide a message, an attachment, or both.", ephemeral=True)
            return
        if message and len(message) > 2000:
            await interaction.response.send_message("⚠️ Message is too long (max 2000 characters).", ephemeral=True)
            return
        if message:
            message = _MENTION_AVOIDANCE_RE.sub(lambda m: "@\u200b" + m.group()[1:], message)

        reference: discord.MessageReference | None = None
        if reply_to:
            match = _MSG_LINK_RE.search(reply_to)
            if not match:
                await interaction.response.send_message(
                    "⚠️ Invalid message link. Right-click a message → **Copy Message Link** and paste it here.",
                    ephemeral=True
                )
                return
            link_guild_id, link_channel_id, link_message_id = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if link_guild_id != interaction.guild_id:
                await interaction.response.send_message("⚠️ That message link is from a different server.", ephemeral=True)
                return
            if link_channel_id != channel.id:
                await interaction.response.send_message(
                    f"⚠️ That message is in a different channel. The reply must be in {channel.mention}.", ephemeral=True
                )
                return
            try:
                target_msg = await channel.fetch_message(link_message_id)
                reference  = target_msg.to_reference(fail_if_not_exists=False)
            except discord.NotFound:
                await interaction.response.send_message("⚠️ Couldn't find that message. It may have been deleted.", ephemeral=True)
                return
            except discord.Forbidden:
                await interaction.response.send_message("⛔ I don't have permission to read messages in that channel.", ephemeral=True)
                return
            except Exception as e:
                print(f"❌ /sendmsg fetch_message error: {type(e).__name__}: {e}")
                await interaction.response.send_message("❌ Failed to fetch the reply target. Please try again.", ephemeral=True)
                return

        discord_file: discord.File | None = None
        if attachment:
            if attachment.size > _MAX_ATTACHMENT_BYTES:
                await interaction.response.send_message(
                    f"⚠️ Attachment too large ({attachment.size / 1024 / 1024:.1f} MB). Max is 8 MB.", ephemeral=True
                )
                return
            await interaction.response.defer(ephemeral=True)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status != 200:
                            await interaction.followup.send(f"❌ Failed to download attachment (HTTP {resp.status}).", ephemeral=True)
                            return
                        discord_file = discord.File(
                            fp       = io.BytesIO(await resp.read()),
                            filename = attachment.filename,
                            spoiler  = attachment.filename.startswith("SPOILER_"),
                        )
            except Exception as e:
                print(f"❌ /sendmsg attachment download error: {type(e).__name__}: {e}")
                await interaction.followup.send("❌ Failed to download the attachment.", ephemeral=True)
                return
        else:
            await interaction.response.defer(ephemeral=True)

        send_kwargs: dict = {}
        if message:      send_kwargs["content"]   = message
        if discord_file: send_kwargs["file"]      = discord_file
        if reference:    send_kwargs["reference"] = reference

        try:
            await channel.send(**send_kwargs)
            parts = []
            if message:      parts.append("message")
            if discord_file: parts.append(f"attachment (`{attachment.filename}`)")
            reply_note = " as a reply" if reference else ""
            await interaction.followup.send(
                f"✅ Sent {' and '.join(parts)}{reply_note} in {channel.mention}.", ephemeral=True
            )
            print(
                f"📨 /sendmsg by {interaction.user} → #{channel.name}"
                + (" [reply]" if reference else "")
                + (f" [file: {attachment.filename}]" if attachment else "")
            )
        except discord.Forbidden:
            await interaction.followup.send(f"⛔ No permission to send in {channel.mention}.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Discord rejected the message (HTTP {e.status}: {e.text}).", ephemeral=True)
            print(f"❌ /sendmsg HTTPException: {e.status} {e.text}")
        except Exception as e:
            await interaction.followup.send("❌ Something went wrong.", ephemeral=True)
            print(f"❌ /sendmsg error: {type(e).__name__}: {e}")


async def setup(bot: commands.Bot):
    cog = ModerationCog(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.sendmsg)
    bot.tree.add_command(cog.filter_group_slash)
    bot.tree.add_command(cog.warns_slash)
    bot.tree.add_command(cog.purge_slash)
    bot.tree.add_command(cog.warn_slash)
    bot.tree.add_command(cog.mute_slash)
    bot.tree.add_command(cog.unmute_slash)
