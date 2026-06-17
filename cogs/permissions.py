# cogs/permissions.py — Permission management (t!perm)

import discord
from discord.ext import commands

from bot.db import load_user_perms, grant_perm, revoke_perm
from bot.family import get_parent_role, get_role
from bot.perms import VALID_PERMS, family_defaults_for


class PermissionsCog(commands.Cog, name="Permissions"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="perm", invoke_without_command=True)
    async def perm_group(self, ctx):
        await ctx.send(embed=discord.Embed(
            title       = "🔑 Permission Commands",
            description = (
                "`t!perm add @user <perm>` — Grant a permission\n"
                "`t!perm remove @user <perm>` — Revoke a permission\n"
                "`t!perm list [@user]` — View permissions\n\n"
                f"**Valid perms:** `{'` `'.join(sorted(VALID_PERMS))}`\n"
                "`mod` grants all permissions at once."
            ),
            color = discord.Color.blurple()
        ))

    @perm_group.command(name="add")
    async def perm_add(self, ctx, member: discord.Member, perm: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can grant permissions.", color=discord.Color.red()))
            return
        perm = perm.lower()
        if perm not in VALID_PERMS:
            await ctx.send(embed=discord.Embed(
                description=f"⚠️ Invalid permission. Valid: `{'` `'.join(sorted(VALID_PERMS))}`",
                color=discord.Color.orange()
            ))
            return
        grant_perm(member.id, perm)
        await ctx.send(embed=discord.Embed(description=f"✅ Granted `{perm}` to {member.mention}.", color=discord.Color.green()))

    @perm_group.command(name="remove")
    async def perm_remove(self, ctx, member: discord.Member, perm: str):
        if not get_parent_role(ctx.author):
            await ctx.send(embed=discord.Embed(description="⛔ Only parents can revoke permissions.", color=discord.Color.red()))
            return
        revoke_perm(member.id, perm.lower())
        await ctx.send(embed=discord.Embed(description=f"✅ Revoked `{perm}` from {member.mention}.", color=discord.Color.green()))

    @perm_group.command(name="list")
    async def perm_list(self, ctx, member: discord.Member = None):
        target    = member or ctx.author
        db_perms  = load_user_perms(target.id)
        role      = get_role(target)
        fam_perms = family_defaults_for(role)
        lines = []
        if db_perms:
            lines.append(f"**Granted:** `{'` `'.join(sorted(db_perms))}`")
        if fam_perms:
            lines.append(f"**Family defaults:** `{'` `'.join(sorted(fam_perms))}`")
        if not lines:
            lines.append("No permissions assigned.")
        embed = discord.Embed(
            title       = f"🔑 Permissions — {target.display_name}",
            description = "\n".join(lines),
            color       = discord.Color.blurple()
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PermissionsCog(bot))
