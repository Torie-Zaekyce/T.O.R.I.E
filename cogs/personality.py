# cogs/personality.py — Custom personality trait management

import discord
from discord.ext import commands

from bot.perms import has_permission


class PersonalityCog(commands.Cog, name="Personality"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="personality", aliases=["persona"], invoke_without_command=True)
    async def personality_group(self, ctx):
        await ctx.send(embed=discord.Embed(
            description="Usage: `t!personality add <trait>` | `t!personality remove <number>` | `t!personality list` | `t!personality clear`",
            color=discord.Color.blurple()
        ))

    @personality_group.command(name="add")
    async def personality_add(self, ctx, *, trait: str):
        if not has_permission(ctx.author, "personality"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to update personality.", color=discord.Color.red()))
            return
        from bot.personality import CUSTOM_TRAITS
        CUSTOM_TRAITS.append(trait.strip())
        await ctx.send(embed=discord.Embed(
            title       = "🧠 Personality Updated!",
            description = f"New trait added: \"{trait.strip()}\"\nI'll keep that in mind! 🧠",
            color       = discord.Color.blurple()
        ))

    @personality_group.command(name="remove")
    async def personality_remove(self, ctx, index: int):
        if not has_permission(ctx.author, "personality"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to update personality.", color=discord.Color.red()))
            return
        from bot.personality import CUSTOM_TRAITS
        if index < 1 or index > len(CUSTOM_TRAITS):
            await ctx.send(embed=discord.Embed(description="⚠️ Invalid number. Use `t!personality list` to see traits.", color=discord.Color.orange()))
            return
        removed = CUSTOM_TRAITS.pop(index - 1)
        await ctx.send(embed=discord.Embed(description=f"✅ Removed trait #{index}: \"{removed}\"", color=discord.Color.green()))

    @personality_group.command(name="list")
    async def personality_list(self, ctx):
        from bot.personality import CUSTOM_TRAITS
        if not CUSTOM_TRAITS:
            await ctx.send(embed=discord.Embed(description="📋 No custom traits yet. Use `t!personality add <trait>`.", color=discord.Color.greyple()))
            return
        embed = discord.Embed(
            title       = "🧠 Custom Personality Traits",
            description = "\n".join(f"`{i+1}.` {trait}" for i, trait in enumerate(CUSTOM_TRAITS)),
            color       = discord.Color.blurple()
        )
        embed.set_footer(text=f"{len(CUSTOM_TRAITS)} trait(s) active")
        await ctx.send(embed=embed)

    @personality_group.command(name="clear")
    async def personality_clear(self, ctx):
        if not has_permission(ctx.author, "personality"):
            await ctx.send(embed=discord.Embed(description="⛔ You don't have permission to clear personality traits.", color=discord.Color.red()))
            return
        from bot.personality import CUSTOM_TRAITS
        count = len(CUSTOM_TRAITS)
        CUSTOM_TRAITS.clear()
        await ctx.send(embed=discord.Embed(description=f"✅ Cleared all {count} trait(s). Back to default me! 😊", color=discord.Color.green()))


    personality_slash = discord.app_commands.Group(name="personality", description="Manage custom personality traits")

    @personality_slash.command(name="add", description="Add a custom personality trait")
    @discord.app_commands.describe(trait="The trait to add")
    async def personality_add_slash(self, interaction: discord.Interaction, trait: str):
        if not has_permission(interaction.user, "personality"):
            await interaction.response.send_message("⛔ You don't have permission to update personality.", ephemeral=True)
            return
        from bot.personality import CUSTOM_TRAITS
        CUSTOM_TRAITS.append(trait.strip())
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🧠 Personality Updated!",
                description=f'New trait added: "{trait.strip()}"\nI\'ll keep that in mind! 🧠',
                color=discord.Color.blurple()
            )
        )

    @personality_slash.command(name="remove", description="Remove a custom personality trait by number")
    @discord.app_commands.describe(index="The trait number to remove (use /personality list)")
    async def personality_remove_slash(self, interaction: discord.Interaction, index: int):
        if not has_permission(interaction.user, "personality"):
            await interaction.response.send_message("⛔ You don't have permission to update personality.", ephemeral=True)
            return
        from bot.personality import CUSTOM_TRAITS
        if index < 1 or index > len(CUSTOM_TRAITS):
            await interaction.response.send_message("⚠️ Invalid number. Use `/personality list` to see traits.", ephemeral=True)
            return
        removed = CUSTOM_TRAITS.pop(index - 1)
        await interaction.response.send_message(f"✅ Removed trait #{index}: \"{removed}\"")

    @personality_slash.command(name="list", description="List all active personality traits")
    async def personality_list_slash(self, interaction: discord.Interaction):
        from bot.personality import CUSTOM_TRAITS
        if not CUSTOM_TRAITS:
            await interaction.response.send_message("📋 No custom traits yet. Use `/personality add <trait>`.")
            return
        embed = discord.Embed(
            title="🧠 Custom Personality Traits",
            description="\n".join(f"`{i+1}.` {trait}" for i, trait in enumerate(CUSTOM_TRAITS)),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"{len(CUSTOM_TRAITS)} trait(s) active")
        await interaction.response.send_message(embed=embed)

    @personality_slash.command(name="clear", description="Clear all custom personality traits")
    async def personality_clear_slash(self, interaction: discord.Interaction):
        if not has_permission(interaction.user, "personality"):
            await interaction.response.send_message("⛔ You don't have permission to clear personality traits.", ephemeral=True)
            return
        from bot.personality import CUSTOM_TRAITS
        count = len(CUSTOM_TRAITS)
        CUSTOM_TRAITS.clear()
        await interaction.response.send_message(f"✅ Cleared all {count} trait(s). Back to default me! 😊")


async def setup(bot: commands.Bot):
    cog = PersonalityCog(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(cog.personality_slash)
