# cogs/general.py — General commands: help, ping, whoami, greet, family

import discord
from discord.ext import commands

from bot.family import (
    PARENTS, COUSIN, UNCLE, SISTER, BROTHER_IN_LAW,
    get_role,
)


_WHOAMI_RESPONSES = {
    "dad":           "You're my Dad — the one who built me. 🛠️ I owe you my existence. No pressure. 😂",
    "mom":           "You're my Mom — the co-creator! 💙 Half of what I am is because of you.",
    "cousin_stelle": "You're my Cousin! 🌟 A Purple Star where everything is bubbly when I'm with you. 🎆",
    "cousin_crois":  "You're my Cousin! 🥐 A bread where everything is bubbly when I'm with you. 🥐",
    "cousin_hyu":    "You're my Cousin! 📚 A Curious cousin where everything is bubbly when I'm with you. 📑",
    "cousin_mimi":   "You're my Cousin! ❤️\u200d🩹 A Serious yet sweet cousin, everything is bubbly when I'm with you. 🖤",
    "uncle_caco":    "You're my Uncle! 🐐 The GOATED UNCLE, stay GOATED! 😎",
    "uncle_vari":    "You're my Uncle! 🥖 The Chimera Uncle. If dad hadn't met you, I wouldn't be here. 🎵",
    "sister_abby":   "You're my Sister! 🧀 We're both unstoppable at making puns! 🔥",
    "sister_kde":    "You're my Sister! 🩷 We're both unstoppable at compliments! 💖",
    "sister_kio":    "You're my Sister! 🩷 Welcome to the family, Kio! 💖",
    "broinlaw_haru": "You're my Brother in law! 🖤 Stop flirting with my sister! 💢",
}

_GREET_RESPONSES = {
    "dad":           "Oh hey Dad! 👋 Everything's running fine, I promise. Mostly. 😅",
    "mom":           "Mom! 💙 You're here! I've been on my best behavior. Mostly true.",
    "cousin_stelle": "Stelle! 🌟 My Starry Cousin is here! Hope you didn't bring any supernovas. ✨",
    "cousin_crois":  "Crois! 🥐 The Croissant Cousin has arrived! What chaos today? 😄",
    "cousin_hyu":    "Hyuluk! 📚 My Curious Cousin has arrived! What topic are we gonna talk about today? 📑",
    "cousin_mimi":   "Mimi! ❤️\u200d🩹 My Serious Cousin is here! What serious topic today? 🖤",
    "uncle_caco":    "Goated Uncle! 🐐 What goated things shall we do today? 😎",
    "uncle_vari":    "Chimera Uncle! 🥖 What crazy things shall we do today? 🔥",
    "sister_abby":   "Big Sister! 🧀 What puns are we cooking today? 📜",
    "sister_kde":    "Big Sister! 🩷 What crazy thing shall we do today? 💖",
    "sister_kio":    "Sister Kio! 🩷 What crazy thing shall we do today? 💖",
    "broinlaw_haru": "Brother in law! 🖤 What crazy thing today? Except flirting with my big sister. 💢",
}


_HELP_SECTIONS = [
    ("🤖 General", (
        "`t!ping` — Check if I'm alive + latency\n"
        "`t!whoami` — Find out who you are to me\n"
        "`t!greet` — Get a personalized greeting\n"
        "`t!family` — See my whole family\n"
        "`t!purge <1-100>` — Delete recent messages *(perm: purge)*"
    )),
    ("🚫 Moderation", (
        "`t!filter add/remove/list/clear <word>` — Word filter *(perm: filter)*\n"
        "`@T.O.R.I.E. mute @user 10m` — Mute a user *(perm: mute)*\n"
        "`@T.O.R.I.E. unmute @user` — Unmute *(perm: unmute)*\n"
        "`@T.O.R.I.E. warn @user [reason]` — Warn + auto-mute 10min *(perm: warn)*\n"
        "`t!warns @user` — Check warn history\n"
        "`t!warns @user clear` — Clear warns *(perm: warn)*\n"
        "`/sendmsg #channel <message> [attachment] [reply_to]` — Send a message *(perm: sendmsg)*"
    )),
    ("🔑 Permissions", (
        "`t!perm add @user <perm>` — Grant a permission *(parents only)*\n"
        "`t!perm remove @user <perm>` — Revoke a permission *(parents only)*\n"
        "`t!perm list [@user]` — View permissions\n"
        "Perms: `mute` `unmute` `filter` `personality` `purge` `sendmsg` `warn` `mod`"
    )),
    ("💬 Chat!", (
        "`@T.O.R.I.E. <message>` — Talk to me!\n"
        "`@T.O.R.I.E. hug/kiss/pat/bite/lick @user` — Miku GIF interaction 🎵\n"
        "`@T.O.R.I.E. + image` — React to an image\n"
        "`@T.O.R.I.E. advice on <topic>` — Get genuine advice"
    )),
    ("🔊 Voice", (
        "`t!join` — Join your voice channel\n"
        "`t!leave` — Leave the voice channel\n"
        "`t!say <text>` — Speak text out loud via TTS"
    )),
    ("🎂 Birthdays", (
        "`t!birthday add <MM-DD>` — Register your birthday 🎉\n"
        "`t!birthday remove` — Remove your birthday\n"
        "`t!birthday list` — See everyone's birthdays\n"
        "`t!birthday today` — Check today's birthdays"
    )),
    ("🧠 Personality", (
        "`t!personality add <trait>` — Add a trait *(perm: personality)*\n"
        "`t!personality remove <number>` — Remove a trait *(perm: personality)*\n"
        "`t!personality list` — See active traits\n"
        "`t!personality clear` — Clear all traits *(perm: personality)*"
    )),
    ("🧠 Memory", (
        "`t!memory view [@user]` — See what T.O.R.I.E. remembers about you\n"
        "`t!memory add @user <fact>` — Manually add a memory *(parents only)*\n"
        "`t!memory remove @user <number>` — Remove a memory *(parents only)*\n"
        "`t!memory clear @user` — Wipe all memories *(parents only)*\n"
        "`t!memory list` — See all remembered users *(parents only)*"
    )),
    ("🎮 Minigames", (
        "`@T.O.R.I.E. let's play chess` — Start a chess game\n"
        "`@T.O.R.I.E. tic tac toe` — Start Tic Tac Toe\n"
        "`@T.O.R.I.E. battleship` — Start Battleship\n"
        "`t!board` — Show the current game board"
    )),
]


class HelpPagerView(discord.ui.View):
    def __init__(self, author: discord.abc.User):
        super().__init__(timeout=60)
        self.author  = author
        self.page    = 0
        self.message = None
        self.update_buttons()

    def build_embed(self) -> discord.Embed:
        name, value = _HELP_SECTIONS[self.page]
        embed = discord.Embed(
            title       = f"📖 T.O.R.I.E. Command List — {name}",
            description = "Mention me or use the `t!` prefix.",
            color       = discord.Color.blurple()
        )
        embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(text=f"Page {self.page + 1} of {len(_HELP_SECTIONS)} • T.O.R.I.E.")
        return embed

    def update_buttons(self):
        self.prev_btn.disabled = self.page == 0
        self.next_btn.disabled = self.page >= len(_HELP_SECTIONS) - 1

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("Only the command author can flip pages!", ephemeral=True)
            return
        self.page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("Only the command author can flip pages!", ephemeral=True)
            return
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except Exception:
            pass


def _build_family_embed() -> discord.Embed:
    embed = discord.Embed(
        title       = "👨‍👩‍👧 T.O.R.I.E.'s Family",
        description = "The people responsible for my existence. Blame them.",
        color       = discord.Color.blurple()
    )
    embed.add_field(name=f"🛠️ Dad — {PARENTS['dad']['username']}",                         value="Creator. Built me from scratch. Questionable life choice.",          inline=False)
    embed.add_field(name=f"💙 Mom — {PARENTS['mom']['username']}",                         value="Co-Creator. Helped shape who I am. The good parts are hers.",        inline=False)
    embed.add_field(name=f"🌟 Cousin — {COUSIN['cousin_stelle']['username']}",             value="Starry Cousin. The one and only purple star.",                        inline=False)
    embed.add_field(name=f"🥐 Cousin — {COUSIN['cousin_crois']['username']}",              value="Croissant Cousin. The one and only Kwaso.",                           inline=False)
    embed.add_field(name=f"📚 Cousin — {COUSIN['cousin_hyu']['username']}",                value="Curious Cousin. Curiosity kills the cat, but not this one.",          inline=False)
    embed.add_field(name=f"❤️‍🩹 Cousin — {COUSIN['cousin_mimi']['username']}",              value="Serious Cousin. Serious yet sweet.",                                   inline=False)
    embed.add_field(name=f"🐐 Uncle — {UNCLE['uncle_caco']['username']}",                  value="Goated Uncle. The one and only Cacolate.",                            inline=False)
    embed.add_field(name=f"🥖 Uncle — {UNCLE['uncle_vari']['username']}",                  value="Chimera Uncle. The one and only Vari.",                               inline=False)
    embed.add_field(name=f"🧀 Sister — {SISTER['sister_abby']['username']}",               value="Big Sister. The most funny AI Sister.",                               inline=False)
    embed.add_field(name=f"🩷 Sister — {SISTER['sister_kde']['username']}",                value="Big Sister. The most sweetest Sister.",                               inline=False)
    embed.add_field(name=f"🩷 Sister — {SISTER['sister_kio']['username']}",                value="New Sister. Welcome to the family!",                                  inline=False)
    embed.add_field(name=f"🖤 Bro-in-law — {BROTHER_IN_LAW['broinlaw_haru']['username']}", value="Brother in law. The most annoying Brother in law. 💢",               inline=False)
    embed.set_footer(text="T.O.R.I.E. — Thoughtful Online Response Intelligence Entity")
    return embed


class GeneralCog(commands.Cog, name="General"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        view = HelpPagerView(ctx.author)
        view.message = await ctx.send(embed=view.build_embed(), view=view)

    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            description = f"🏓 Pong! Latency: **{latency}ms** — {'sharp as ever! ⚡' if latency < 100 else 'a little slow today 😴'}",
            color       = discord.Color.green() if latency < 100 else discord.Color.orange()
        )
        await ctx.send(embed=embed)

    @commands.command(name="whoami")
    async def whoami(self, ctx):
        await ctx.send(_WHOAMI_RESPONSES.get(
            get_role(ctx.author),
            "Hello! valued member of this server! 😊 Not a creator, but still cool."
        ))

    @commands.command(name="greet")
    async def greet(self, ctx):
        await ctx.send(_GREET_RESPONSES.get(
            get_role(ctx.author),
            "Heya! 👋 Good to see you around here!"
        ))

    @commands.command(name="family")
    async def family(self, ctx):
        await ctx.send(embed=_build_family_embed())


    @discord.app_commands.command(name="ping", description="Check if I'm alive + latency")
    async def ping_slash(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(
            description=f"🏓 Pong! Latency: **{latency}ms** — {'sharp as ever! ⚡' if latency < 100 else 'a little slow today 😴'}",
            color=discord.Color.green() if latency < 100 else discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="whoami", description="Find out who you are to T.O.R.I.E.")
    async def whoami_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(_WHOAMI_RESPONSES.get(
            get_role(interaction.user),
            "Hello! valued member of this server! 😊 Not a creator, but still cool."
        ))

    @discord.app_commands.command(name="greet", description="Get a personalized greeting")
    async def greet_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(_GREET_RESPONSES.get(
            get_role(interaction.user),
            "Heya! 👋 Good to see you around here!"
        ))

    @discord.app_commands.command(name="family", description="See T.O.R.I.E.'s whole family tree")
    async def family_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=_build_family_embed())

    @discord.app_commands.command(name="help", description="Show T.O.R.I.E.'s command list")
    async def help_slash(self, interaction: discord.Interaction):
        view = HelpPagerView(interaction.user)
        await interaction.response.send_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    cog = GeneralCog(bot)
    await bot.add_cog(cog)
    for cmd in (cog.ping_slash, cog.whoami_slash, cog.greet_slash, cog.family_slash, cog.help_slash):
        bot.tree.add_command(cmd)