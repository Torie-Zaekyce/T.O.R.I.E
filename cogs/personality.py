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


async def setup(bot: commands.Bot):
    await bot.add_cog(PersonalityCog(bot))
