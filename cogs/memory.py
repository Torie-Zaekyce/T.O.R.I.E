# cogs/memory.py — User memory management (t!memory)

from datetime import timezone

import discord
from discord.ext import commands

from bot.family import get_parent_role
from bot.user_memory import (
    get_user_memory, all_memories, add_single_fact,
    remove_fact_by_index, clear_facts, delete_user as delete_user_memory,
)


class MemoryCog(commands.Cog, name="Memory"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="memory", aliases=["mem"], invoke_without_command=True)
    async def memory_group(self, ctx):
        await ctx.send(embed=discord.Embed(
            title       = "🧠 Memory Commands",
            description = (
                "`t!memory view [@user]` — view memories for yourself or a user\n"
                "`t!memory add @user <fact>` — manually add a fact *(parents only)*\n"
                "`t!memory remove @user <number>` — remove a fact by number *(parents only)*\n"
                "`t!memory clear @user` — wipe all facts for a user *(parents only)*\n"
                "`t!memory delete @user` — fully remove a user from memory *(parents only)*\n"
                "`t!memory list` — show all users T.O.R.I.E. remembers *(parents only)*"
            ),
            color = discord.Color.blurple()
        ))

    @memory_group.command(name="view")
    async def memory_view(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        if member and member != ctx.author and not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(
                description="⛔ Only my parents can view other people's memories.", color=discord.Color.red()
            ))
            return
        doc = get_user_memory(str(target.id))
        if not doc or not doc.get("facts"):
            await ctx.send(embed=discord.Embed(
                description=f"🧠 No memories stored for **{target.display_name}** yet.",
                color=discord.Color.greyple()
            ))
            return
        facts_text = "\n".join(f"`{i+1}.` {f}" for i, f in enumerate(doc["facts"]))
        embed = discord.Embed(
            title       = f"🧠 Memory — {target.display_name}",
            description = facts_text,
            color       = discord.Color.blurple()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        last_seen = doc.get("last_seen")
        if last_seen:
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            embed.add_field(name="Last seen",    value=f"<t:{int(last_seen.timestamp())}:R>", inline=True)
        embed.add_field(name="Interactions", value=str(doc.get("interaction_count", 0)), inline=True)
        embed.set_footer(text=f"{len(doc['facts'])} fact(s) stored")
        await ctx.send(embed=embed)

    @memory_group.command(name="add")
    async def memory_add(self, ctx, member: discord.Member, *, fact: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can manually add memories.", color=discord.Color.red()))
            return
        added = add_single_fact(str(member.id), member.display_name, fact.strip())
        if added:
            await ctx.send(embed=discord.Embed(
                description=f"✅ Added to **{member.display_name}**'s memory:\n> {fact.strip()}",
                color=discord.Color.green()
            ))
        else:
            await ctx.send(embed=discord.Embed(
                description=f"⚠️ That fact is already in **{member.display_name}**'s memory.",
                color=discord.Color.orange()
            ))

    @memory_group.command(name="remove")
    async def memory_remove(self, ctx, member: discord.Member, index: int):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can remove memories.", color=discord.Color.red()))
            return
        removed = remove_fact_by_index(str(member.id), index)
        if removed:
            await ctx.send(embed=discord.Embed(
                description=f"✅ Removed fact #{index} from **{member.display_name}**:\n> {removed}",
                color=discord.Color.green()
            ))
        else:
            await ctx.send(embed=discord.Embed(
                description=f"⚠️ No fact #{index} found for **{member.display_name}**. Use `t!memory view` to check.",
                color=discord.Color.orange()
            ))

    @memory_group.command(name="clear")
    async def memory_clear(self, ctx, member: discord.Member):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can clear memories.", color=discord.Color.red()))
            return
        cleared = clear_facts(str(member.id))
        if cleared:
            await ctx.send(embed=discord.Embed(
                description=f"✅ Cleared all memories for **{member.display_name}**.", color=discord.Color.green()
            ))
        else:
            await ctx.send(embed=discord.Embed(
                description=f"⚠️ No memory document found for **{member.display_name}**.", color=discord.Color.orange()
            ))

    @memory_group.command(name="delete")
    async def memory_delete(self, ctx, member: discord.Member):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can delete memory records.", color=discord.Color.red()))
            return
        deleted = delete_user_memory(str(member.id))
        if deleted:
            await ctx.send(embed=discord.Embed(
                description=f"🗑️ Fully removed **{member.display_name}** from T.O.R.I.E.'s memory.",
                color=discord.Color.blurple()
            ))
        else:
            await ctx.send(embed=discord.Embed(
                description=f"⚠️ No memory document found for **{member.display_name}**.", color=discord.Color.orange()
            ))

    @memory_group.command(name="list")
    async def memory_list(self, ctx):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only my parents can list all memories.", color=discord.Color.red()))
            return
        docs = all_memories()
        if not docs:
            await ctx.send(embed=discord.Embed(description="🧠 No user memories stored yet.", color=discord.Color.greyple()))
            return
        lines = [
            f"<@{d['_id']}> **{d.get('display_name', 'Unknown')}** — {d.get('interaction_count', 0)} interaction(s)"
            for d in sorted(docs, key=lambda x: x.get("interaction_count", 0), reverse=True)
        ]
        embed = discord.Embed(
            title       = f"🧠 All Remembered Users ({len(docs)})",
            description = "\n".join(lines),
            color       = discord.Color.blurple()
        )
        embed.set_footer(text="Use t!memory view @user to see their facts")
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemoryCog(bot))
