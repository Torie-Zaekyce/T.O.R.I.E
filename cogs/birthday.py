# cogs/birthday.py — Birthday registration and lookup

from datetime import datetime

import discord
from discord.ext import commands

from bot.db import load_birthdays, save_birthday, delete_birthday, get_todays_birthdays

# In-memory cache loaded at startup (mirrors the old module-level BIRTHDAYS dict)
BIRTHDAYS: dict = {}


class BirthdayCog(commands.Cog, name="Birthday"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        BIRTHDAYS.update(load_birthdays())

    # -----------------------------------------------------------------------
    # t!birthday
    # -----------------------------------------------------------------------

    @commands.group(name="birthday", aliases=["bday"], invoke_without_command=True)
    async def birthday_group(self, ctx):
        embed = discord.Embed(
            title       = "🎂 Birthday Commands",
            description = (
                "`t!birthday add <MM-DD>` — Register your own birthday\n"
                "`t!birthday remove` — Remove your registered birthday\n"
                "`t!birthday list` — See everyone's birthdays\n"
                "`t!birthday today` — Check who's celebrating today!"
            ),
            color = discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_footer(text="Example: t!birthday add 03-15 → registers March 15")
        await ctx.send(embed=embed)

    @birthday_group.command(name="add")
    async def birthday_add(self, ctx, date: str = None):
        if not date or len(date) > 10:
            await ctx.send(embed=discord.Embed(
                description="⚠️ Please provide your birthday. Example: `t!birthday add 03-15`",
                color=discord.Color.orange()
            ))
            return
        try:
            parsed = datetime.strptime(date.strip(), "%m-%d")
        except ValueError:
            await ctx.send(embed=discord.Embed(description="⚠️ Invalid date format. Use `MM-DD`.", color=discord.Color.orange()))
            return
        data = {"month": parsed.month, "day": parsed.day, "user_id": ctx.author.id, "name": ctx.author.display_name}
        BIRTHDAYS[str(ctx.author.id)] = data
        save_birthday(str(ctx.author.id), data)
        embed = discord.Embed(
            title       = "🎂 Birthday Registered!",
            description = (
                f"Got it, {ctx.author.mention}! 🎉\n"
                f"Your birthday is set to **{parsed.strftime('%B %d')}**.\n"
                f"I'll make sure to celebrate you on your special day! 🎈💙"
            ),
            color = discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_footer(text="T.O.R.I.E. — marking the calendar 📅")
        await ctx.send(embed=embed)

    @birthday_group.command(name="remove")
    async def birthday_remove(self, ctx):
        key = str(ctx.author.id)
        if key not in BIRTHDAYS:
            await ctx.send(embed=discord.Embed(description="⚠️ You don't have a birthday registered!", color=discord.Color.orange()))
            return
        del BIRTHDAYS[key]
        delete_birthday(key)
        await ctx.send(embed=discord.Embed(description=f"✅ Removed your birthday, {ctx.author.mention}.", color=discord.Color.green()))

    @birthday_group.command(name="list")
    async def birthday_list(self, ctx):
        if not BIRTHDAYS:
            await ctx.send(embed=discord.Embed(description="📋 No birthdays registered yet! 🎂", color=discord.Color.greyple()))
            return
        sorted_entries = sorted(BIRTHDAYS.items(), key=lambda x: (x[1]["month"], x[1]["day"]))
        per_page    = 10
        total_pages = (len(sorted_entries) + per_page - 1) // per_page

        def build_embed(page: int) -> discord.Embed:
            start = page * per_page
            lines = []
            for i, (key, data) in enumerate(sorted_entries[start:start + per_page], start=start + 1):
                date_str = datetime(2000, data["month"], data["day"]).strftime("%B %d")
                mention  = f"<@{data['user_id']}>" if data.get("user_id") else data.get("name", key)
                lines.append(f"`{i}.` {mention} — **{date_str}**")
            embed = discord.Embed(
                title       = "🎂 Birthday List",
                description = "\n".join(lines),
                color       = discord.Color.from_rgb(255, 182, 193)
            )
            embed.set_footer(text=f"Page {page + 1} of {total_pages} • {len(BIRTHDAYS)} registered")
            return embed

        class BirthdayView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.page = 0
                self.message = None
                self.update_buttons()

            def update_buttons(self):
                self.prev_btn.disabled = self.page == 0
                self.next_btn.disabled = self.page >= total_pages - 1

            @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
            async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the command author can flip pages!", ephemeral=True)
                    return
                self.page -= 1
                self.update_buttons()
                await interaction.response.edit_message(embed=build_embed(self.page), view=self)

            @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
            async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("Only the command author can flip pages!", ephemeral=True)
                    return
                self.page += 1
                self.update_buttons()
                await interaction.response.edit_message(embed=build_embed(self.page), view=self)

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                try:
                    await self.message.edit(view=self)
                except Exception:
                    pass

        view = BirthdayView()
        view.message = await ctx.send(embed=build_embed(0), view=view)

    @birthday_group.command(name="today")
    async def birthday_today(self, ctx):
        todays = get_todays_birthdays(BIRTHDAYS)
        if not todays:
            await ctx.send(embed=discord.Embed(description="📋 No birthdays today! 😄", color=discord.Color.greyple()))
            return
        for b in todays:
            mention = f"<@{b['user_id']}>" if b.get("user_id") else b.get("name", "Someone")
            embed = discord.Embed(
                title       = "🎂 Happy Birthday!",
                description = f"Today is {mention}'s birthday! 🎉\nWishing you an amazing day filled with joy and love! 💙🎈",
                color       = discord.Color.gold()
            )
            embed.set_footer(text="T.O.R.I.E. — sending birthday love 🎀")
            await ctx.send(embed=embed)


    # ── Slash commands ───────────────────────────────────────────────────────

    birthday_slash = discord.app_commands.Group(name="birthday", description="Birthday registration and lookup")

    @birthday_slash.command(name="add", description="Register your birthday")
    @discord.app_commands.describe(date="Your birthday in MM-DD format (e.g. 03-15)")
    async def birthday_add_slash(self, interaction: discord.Interaction, date: str):
        if not date or len(date) > 10:
            await interaction.response.send_message("⚠️ Please provide your birthday. Example: `/birthday add 03-15`", ephemeral=True)
            return
        try:
            parsed = datetime.strptime(date.strip(), "%m-%d")
        except ValueError:
            await interaction.response.send_message("⚠️ Invalid date format. Use `MM-DD`.", ephemeral=True)
            return
        data = {"month": parsed.month, "day": parsed.day, "user_id": interaction.user.id, "name": interaction.user.display_name}
        BIRTHDAYS[str(interaction.user.id)] = data
        save_birthday(str(interaction.user.id), data)
        embed = discord.Embed(
            title="🎂 Birthday Registered!",
            description=f"Got it, {interaction.user.mention}! 🎉\nYour birthday is set to **{parsed.strftime('%B %d')}**.\nI'll make sure to celebrate you on your special day! 🎈💙",
            color=discord.Color.from_rgb(255, 182, 193)
        )
        embed.set_footer(text="T.O.R.I.E. — marking the calendar 📅")
        await interaction.response.send_message(embed=embed)

    @birthday_slash.command(name="remove", description="Remove your registered birthday")
    async def birthday_remove_slash(self, interaction: discord.Interaction):
        key = str(interaction.user.id)
        if key not in BIRTHDAYS:
            await interaction.response.send_message("⚠️ You don't have a birthday registered!", ephemeral=True)
            return
        del BIRTHDAYS[key]
        delete_birthday(key)
        await interaction.response.send_message(f"✅ Removed your birthday, {interaction.user.mention}.")

    @birthday_slash.command(name="list", description="Browse all registered birthdays")
    async def birthday_list_slash(self, interaction: discord.Interaction):
        if not BIRTHDAYS:
            await interaction.response.send_message("📋 No birthdays registered yet! 🎂")
            return
        sorted_entries = sorted(BIRTHDAYS.items(), key=lambda x: (x[1]["month"], x[1]["day"]))
        per_page, total_pages = 10, (len(sorted_entries) + 10 - 1) // 10

        def build_embed(page: int) -> discord.Embed:
            start = page * per_page
            lines = []
            for i, (key, data) in enumerate(sorted_entries[start:start + per_page], start=start + 1):
                date_str = datetime(2000, data["month"], data["day"]).strftime("%B %d")
                mention = f"<@{data['user_id']}>" if data.get("user_id") else data.get("name", key)
                lines.append(f"`{i}.` {mention} — **{date_str}**")
            embed = discord.Embed(
                title="🎂 Birthday List",
                description="\n".join(lines),
                color=discord.Color.from_rgb(255, 182, 193)
            )
            embed.set_footer(text=f"Page {page + 1} of {total_pages} • {len(BIRTHDAYS)} registered")
            return embed

        author = interaction.user

        class BirthdayView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.page = 0
                self.message = None
                self.update_buttons()

            def update_buttons(self):
                self.prev_btn.disabled = self.page == 0
                self.next_btn.disabled = self.page >= total_pages - 1

            @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
            async def prev_btn(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user != author:
                    await button_interaction.response.send_message("Only the command author can flip pages!", ephemeral=True)
                    return
                self.page -= 1
                self.update_buttons()
                await button_interaction.response.edit_message(embed=build_embed(self.page), view=self)

            @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
            async def next_btn(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                if button_interaction.user != author:
                    await button_interaction.response.send_message("Only the command author can flip pages!", ephemeral=True)
                    return
                self.page += 1
                self.update_buttons()
                await button_interaction.response.edit_message(embed=build_embed(self.page), view=self)

            async def on_timeout(self):
                for child in self.children:
                    child.disabled = True
                try:
                    await self.message.edit(view=self)
                except Exception:
                    pass

        view = BirthdayView()
        await interaction.response.send_message(embed=build_embed(0), view=view)
        view.message = await interaction.original_response()

    @birthday_slash.command(name="today", description="Check who's celebrating today!")
    async def birthday_today_slash(self, interaction: discord.Interaction):
        todays = get_todays_birthdays(BIRTHDAYS)
        if not todays:
            await interaction.response.send_message("📋 No birthdays today! 😄")
            return
        for b in todays:
            mention = f"<@{b['user_id']}>" if b.get("user_id") else b.get("name", "Someone")
            embed = discord.Embed(
                title="🎂 Happy Birthday!",
                description=f"Today is {mention}'s birthday! 🎉\nWishing you an amazing day filled with joy and love! 💙🎈",
                color=discord.Color.gold()
            )
            embed.set_footer(text="T.O.R.I.E. — sending birthday love 🎀")
            await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    cog = BirthdayCog(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.birthday_slash)
