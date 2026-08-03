# cogs/settings.py — Spontaneous chat behavior settings (t!settings / /settings)

import discord
from discord.ext import commands

from bot.config import SPONTANEOUS_DEFAULTS
from bot.db import save_settings
from bot.family import get_parent_role

_BOOL_WORDS = {"true": True, "false": False, "on": True, "off": False, "yes": True, "no": False}

_SCALAR_KEYS = [k for k in SPONTANEOUS_DEFAULTS if k != "channels"]

_INT_CLAMPS = {
    "join_threshold":   lambda v: max(2, v),
    "join_window":      lambda v: max(5, v),
    "join_cooldown":    lambda v: max(0, v),
    "join_min_authors": lambda v: max(1, v),
    "greet_cooldown":       lambda v: max(0, v),
    "greet_user_cooldown":  lambda v: max(0, v),
}

_BOOL_KEYS = {"enabled", "join_enabled", "greet_enabled"}

_VALID_KEYS = sorted(set(_SCALAR_KEYS))


def _parse_value(raw: str):
    low = raw.lower()
    if low in _BOOL_WORDS:
        return _BOOL_WORDS[low]
    if low.isdigit():
        return int(low)
    return None


def _settings_embed(bot) -> discord.Embed:
    s = bot.settings
    lines = [
        f"**Master switch:** `{'ON' if s.get('enabled') else 'OFF'}`",
        f"**Lively-chat join:** `{'ON' if s.get('join_enabled') else 'OFF'}` — joins after "
        f"`{s.get('join_threshold')}` messages in `{s.get('join_window')}s` "
        f"(cooldown `{s.get('join_cooldown')}s`, ≥`{s.get('join_min_authors')}` distinct authors)",
        f"**Greeting replies:** `{'ON' if s.get('greet_enabled') else 'OFF'}` — channel cooldown "
        f"`{s.get('greet_cooldown')}s`, per-user cooldown `{s.get('greet_user_cooldown')}s`",
        "**Channels:** " + (", ".join(f"<#{cid}>" for cid in s.get("channels", [])) or "*none*"),
    ]
    embed = discord.Embed(
        title="⚙️ Spontaneous Chat Settings",
        description="\n".join(lines),
        color=discord.Color.blurple(),
    )
    embed.set_footer(text="Parents: t!settings set <key> <value> • t!settings channels add/remove • t!settings on/off/reset")
    return embed


class SettingsCog(commands.Cog, name="Settings"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _persist(self) -> None:
        save_settings(self.bot.settings)

    @commands.group(name="settings", aliases=["config"], invoke_without_command=True)
    async def settings_group(self, ctx):
        await ctx.send(embed=_settings_embed(self.bot))

    @settings_group.command(name="set")
    async def settings_set(self, ctx, key: str, *, value: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can change settings.", color=discord.Color.red()))
            return
        key = key.lower()
        if key not in _VALID_KEYS:
            await ctx.send(embed=discord.Embed(
                description=f"⚠️ Unknown key. Valid keys: `{'` `'.join(_VALID_KEYS)}`",
                color=discord.Color.orange(),
            ))
            return
        parsed = _parse_value(value)
        if parsed is None:
            await ctx.send(embed=discord.Embed(description="⚠️ Value must be `true`/`false` or a whole number.", color=discord.Color.orange()))
            return
        if key in _BOOL_KEYS:
            parsed = bool(parsed)
        elif key in _INT_CLAMPS:
            parsed = _INT_CLAMPS[key](parsed)
        self.bot.settings[key] = parsed
        self._persist()
        await ctx.send(embed=discord.Embed(description=f"✅ `{key}` set to `{parsed}`.", color=discord.Color.green()))

    @settings_group.command(name="on")
    async def settings_on(self, ctx):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can change settings.", color=discord.Color.red()))
            return
        self.bot.settings["enabled"] = True
        self._persist()
        await ctx.send(embed=discord.Embed(description="✅ Spontaneous replies **enabled**.", color=discord.Color.green()))

    @settings_group.command(name="off")
    async def settings_off(self, ctx):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can change settings.", color=discord.Color.red()))
            return
        self.bot.settings["enabled"] = False
        self._persist()
        await ctx.send(embed=discord.Embed(description="✅ Spontaneous replies **disabled**.", color=discord.Color.red()))

    @settings_group.command(name="reset")
    async def settings_reset(self, ctx):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can change settings.", color=discord.Color.red()))
            return
        self.bot.settings = dict(SPONTANEOUS_DEFAULTS)
        self._persist()
        await ctx.send(embed=discord.Embed(description="✅ Settings reset to defaults.", color=discord.Color.green()))

    @settings_group.group(name="channels", invoke_without_command=True)
    async def settings_channels(self, ctx):
        await ctx.send(embed=_settings_embed(self.bot))

    @settings_channels.command(name="add")
    async def settings_channels_add(self, ctx, channel: discord.TextChannel):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can change settings.", color=discord.Color.red()))
            return
        channels = self.bot.settings.setdefault("channels", [])
        if channel.id in channels:
            await ctx.send(embed=discord.Embed(description=f"⚠️ {channel.mention} is already enabled.", color=discord.Color.orange()))
            return
        channels.append(channel.id)
        self._persist()
        await ctx.send(embed=discord.Embed(description=f"✅ {channel.mention} added to spontaneous replies.", color=discord.Color.green()))

    @settings_channels.command(name="remove")
    async def settings_channels_remove(self, ctx, channel: discord.TextChannel):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can change settings.", color=discord.Color.red()))
            return
        channels = self.bot.settings.setdefault("channels", [])
        if channel.id not in channels:
            await ctx.send(embed=discord.Embed(description=f"⚠️ {channel.mention} isn't enabled.", color=discord.Color.orange()))
            return
        channels.remove(channel.id)
        self._persist()
        await ctx.send(embed=discord.Embed(description=f"✅ {channel.mention} removed from spontaneous replies.", color=discord.Color.green()))

    @settings_channels.command(name="clear")
    async def settings_channels_clear(self, ctx):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can change settings.", color=discord.Color.red()))
            return
        self.bot.settings["channels"] = []
        self._persist()
        await ctx.send(embed=discord.Embed(description="✅ Cleared all channels (spontaneous replies now off everywhere).", color=discord.Color.green()))


    settings_slash = discord.app_commands.Group(name="settings", description="Tweak T.O.R.I.E.'s spontaneous chat behavior")
    channels_slash = discord.app_commands.Group(name="channels", description="Manage channels where T.O.R.I.E. replies on her own", parent=settings_slash)

    @settings_slash.command(name="view", description="Show current spontaneous-chat settings")
    async def settings_view_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=_settings_embed(self.bot))

    @settings_slash.command(name="set", description="Set a spontaneous-behavior setting (parents only)")
    @discord.app_commands.describe(key="Which setting to change", value="true/false or a number")
    @discord.app_commands.choices(key=[
        discord.app_commands.Choice(name=k, value=k) for k in _VALID_KEYS
    ])
    async def settings_set_slash(self, interaction: discord.Interaction, key: str, value: str):
        if not get_parent_role(interaction.user):
            await interaction.response.send_message("⛔ Only parents can change settings.", ephemeral=True)
            return
        parsed = _parse_value(value)
        if parsed is None:
            await interaction.response.send_message("⚠️ Value must be `true`/`false` or a whole number.", ephemeral=True)
            return
        if key in _BOOL_KEYS:
            parsed = bool(parsed)
        elif key in _INT_CLAMPS:
            parsed = _INT_CLAMPS[key](parsed)
        self.bot.settings[key] = parsed
        self._persist()
        await interaction.response.send_message(f"✅ `{key}` set to `{parsed}`.")

    @settings_slash.command(name="on", description="Enable spontaneous replies (parents only)")
    async def settings_on_slash(self, interaction: discord.Interaction):
        if not get_parent_role(interaction.user):
            await interaction.response.send_message("⛔ Only parents can change settings.", ephemeral=True)
            return
        self.bot.settings["enabled"] = True
        self._persist()
        await interaction.response.send_message("✅ Spontaneous replies **enabled**.")

    @settings_slash.command(name="off", description="Disable spontaneous replies (parents only)")
    async def settings_off_slash(self, interaction: discord.Interaction):
        if not get_parent_role(interaction.user):
            await interaction.response.send_message("⛔ Only parents can change settings.", ephemeral=True)
            return
        self.bot.settings["enabled"] = False
        self._persist()
        await interaction.response.send_message("✅ Spontaneous replies **disabled**.")

    @settings_slash.command(name="reset", description="Reset settings to defaults (parents only)")
    async def settings_reset_slash(self, interaction: discord.Interaction):
        if not get_parent_role(interaction.user):
            await interaction.response.send_message("⛔ Only parents can change settings.", ephemeral=True)
            return
        self.bot.settings = dict(SPONTANEOUS_DEFAULTS)
        self._persist()
        await interaction.response.send_message("✅ Settings reset to defaults.")

    @channels_slash.command(name="add", description="Allow spontaneous replies in a channel (parents only)")
    @discord.app_commands.describe(channel="The text channel to enable")
    async def channels_add_slash(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not get_parent_role(interaction.user):
            await interaction.response.send_message("⛔ Only parents can change settings.", ephemeral=True)
            return
        channels = self.bot.settings.setdefault("channels", [])
        if channel.id in channels:
            await interaction.response.send_message(f"⚠️ {channel.mention} is already enabled.")
            return
        channels.append(channel.id)
        self._persist()
        await interaction.response.send_message(f"✅ {channel.mention} added to spontaneous replies.")

    @channels_slash.command(name="remove", description="Stop spontaneous replies in a channel (parents only)")
    @discord.app_commands.describe(channel="The text channel to disable")
    async def channels_remove_slash(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not get_parent_role(interaction.user):
            await interaction.response.send_message("⛔ Only parents can change settings.", ephemeral=True)
            return
        channels = self.bot.settings.setdefault("channels", [])
        if channel.id not in channels:
            await interaction.response.send_message(f"⚠️ {channel.mention} isn't enabled.")
            return
        channels.remove(channel.id)
        self._persist()
        await interaction.response.send_message(f"✅ {channel.mention} removed from spontaneous replies.")

    @channels_slash.command(name="clear", description="Disable spontaneous replies everywhere (parents only)")
    async def channels_clear_slash(self, interaction: discord.Interaction):
        if not get_parent_role(interaction.user):
            await interaction.response.send_message("⛔ Only parents can change settings.", ephemeral=True)
            return
        self.bot.settings["channels"] = []
        self._persist()
        await interaction.response.send_message("✅ Cleared all channels (spontaneous replies now off everywhere).")


async def setup(bot: commands.Bot):
    cog = SettingsCog(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.settings_slash)
