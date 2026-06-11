import asyncio
import re
import discord
from discord.ext import commands
from bot.commands import has_permission, add_warn
from bot.utils import fmt_duration
from bot.config import MUTED_ROLE_ID, MUTED_CHANNEL_ID, GENERAL_CHANNEL


async def handle_warn(
    message: discord.Message, targets: list, clean_msg: str, bot: commands.Bot
) -> None:
    """Issue a warning to a user with auto-mute."""
    if not has_permission(message.author, "warn"):
        await message.channel.send(
            embed=discord.Embed(
                description="⛔ You don't have permission to warn users.",
                color=discord.Color.red(),
            )
        )
        return

    target = targets[0]
    reason = re.sub(r"<@!?\d+>", "", clean_msg)
    reason = re.sub(r"\bwarn\b", "", reason, flags=re.I).strip() or "No reason provided"
    warn_count = add_warn(str(target.id), reason, message.author.display_name)

    await message.channel.send(
        embed=discord.Embed(
            title="⚠️ User Warned",
            description=(
                f"{target.mention} has been warned!\n"
                f"**Reason:** {reason}\n"
                f"**Total warnings:** {warn_count}\n"
                f"Auto-muted for **10 minutes**."
            ),
            color=discord.Color.orange(),
        )
    )

    muted_role = message.guild.get_role(MUTED_ROLE_ID)
    muted_ch = bot.get_channel(MUTED_CHANNEL_ID)
    if muted_role:
        try:
            await target.add_roles(
                muted_role, reason=f"Warned by {message.author} — auto-mute"
            )
            if muted_ch:
                warn_embed = discord.Embed(
                    title="⚠️ You have been warned and muted",
                    description=(
                        f"Hey {target.mention}, you've been warned!\n"
                        f"**Reason:** {reason}\n"
                        f"**Total warnings:** {warn_count}\n"
                        f"You are automatically muted for **10 minutes**."
                    ),
                    color=discord.Color.orange(),
                )
                warn_embed.set_footer(text=f"Warned by {message.author.display_name}")
                warn_msg = await muted_ch.send(embed=warn_embed)
                await warn_msg.delete(delay=180)
            task = asyncio.create_task(
                auto_unmute(target, muted_role, 600, muted_ch, bot)
            )
        except discord.Forbidden:
            pass


async def handle_mute(
    message: discord.Message,
    targets: list,
    clean_msg: str,
    bot: commands.Bot,
    mute_tasks: dict[int, asyncio.Task],
) -> None:
    """Mute a user for a specified duration."""
    if not has_permission(message.author, "mute"):
        await message.channel.send(
            embed=discord.Embed(
                description="⛔ You don't have permission to mute users.",
                color=discord.Color.red(),
            )
        )
        return

    from bot.utils import parse_duration

    target = targets[0]
    duration = parse_duration(clean_msg) or __import__("datetime").timedelta(
        minutes=10
    )
    default = not parse_duration(clean_msg)

    if duration > __import__("datetime").timedelta(days=28):
        await message.channel.send(
            embed=discord.Embed(
                description="⚠️ Maximum mute duration is 28 days.",
                color=discord.Color.orange(),
            )
        )
        return

    duration_str = fmt_duration(duration)
    muted_role = message.guild.get_role(MUTED_ROLE_ID)

    if not muted_role:
        print(f"⚠️ Muted role ID {MUTED_ROLE_ID} not found — cannot mute")
        await message.channel.send(
            embed=discord.Embed(
                description="⛔ Muted role not found. Contact an admin.",
                color=discord.Color.red(),
            )
        )
        return

    try:
        if target.id in mute_tasks:
            mute_tasks[target.id].cancel()

        await target.add_roles(muted_role, reason=f"Muted by {message.author} via T.O.R.I.E.")

        desc = f"🔇 Muted {target.mention} for **{duration_str}**."
        if default:
            desc += " *(no duration specified — defaulted to 10 minutes)*"
        await message.channel.send(
            embed=discord.Embed(description=desc, color=discord.Color.red())
        )

        muted_ch = bot.get_channel(MUTED_CHANNEL_ID)
        if muted_ch:
            mute_embed = discord.Embed(
                title="🔇 You have been muted",
                description=(
                    f"Hey {target.mention}, you've been muted for **{duration_str}**.\n"
                    f"You can only see this channel while muted.\n"
                    f"Your mute will be lifted automatically when the time runs out."
                ),
                color=discord.Color.red(),
            )
            mute_embed.set_footer(text=f"Muted by {message.author.display_name}")
            mute_msg = await muted_ch.send(embed=mute_embed)
            await mute_msg.delete(delay=180)

        task = asyncio.create_task(
            auto_unmute(target, muted_role, int(duration.total_seconds()), muted_ch, bot)
        )
        mute_tasks[target.id] = task

    except discord.Forbidden:
        await message.channel.send(
            embed=discord.Embed(
                description="⛔ I don't have permission to mute that user.",
                color=discord.Color.red(),
            )
        )
    except Exception as e:
        print(f"❌ Mute error: {e}")


async def handle_unmute(
    message: discord.Message, targets: list, bot: commands.Bot, mute_tasks: dict
) -> None:
    """Unmute a user."""
    if not has_permission(message.author, "unmute"):
        await message.channel.send(
            embed=discord.Embed(
                description="⛔ You don't have permission to unmute users.",
                color=discord.Color.red(),
            )
        )
        return
    target = targets[0]
    try:
        if target.id in mute_tasks:
            mute_tasks[target.id].cancel()
            mute_tasks.pop(target.id, None)
        muted_role = message.guild.get_role(MUTED_ROLE_ID)
        if muted_role and muted_role in target.roles:
            await target.remove_roles(
                muted_role, reason=f"Unmuted by {message.author} via T.O.R.I.E."
            )
        await message.channel.send(
            embed=discord.Embed(
                description=f"🔊 Unmuted {target.mention}. Welcome back!",
                color=discord.Color.green(),
            )
        )
        muted_ch = bot.get_channel(MUTED_CHANNEL_ID)
        if muted_ch:
            done_msg = await muted_ch.send(
                embed=discord.Embed(
                    description=f"🔊 {target.mention} has been unmuted early. Welcome back!",
                    color=discord.Color.green(),
                )
            )
            await done_msg.delete(delay=180)
    except discord.Forbidden:
        await message.channel.send(
            embed=discord.Embed(
                description="⛔ I don't have permission to unmute that user.",
                color=discord.Color.red(),
            )
        )
    except Exception as e:
        print(f"❌ Unmute error: {e}")


async def auto_unmute(
    member: discord.Member, role, seconds: int, muted_ch, bot: commands.Bot
) -> None:
    """Auto-unmute after timeout expires."""
    await asyncio.sleep(seconds)
    try:
        await member.remove_roles(role, reason="Mute duration expired — T.O.R.I.E.")
        if muted_ch:
            done_msg = await muted_ch.send(
                embed=discord.Embed(
                    description=f"🔊 {member.mention} your mute has expired. You can now chat again!",
                    color=discord.Color.green(),
                )
            )
            await done_msg.delete(delay=180)
        gen_ch = bot.get_channel(GENERAL_CHANNEL)
        if gen_ch:
            gen_embed = discord.Embed(
                description=f"🔊 {member.mention} has been unmuted and is back in the server!",
                color=discord.Color.green(),
            )
            gen_embed.set_footer(text="T.O.R.I.E. — mute timer expired")
            await gen_ch.send(embed=gen_embed)
        print(f"✅ Auto-unmuted {member.display_name}")
    except Exception as e:
        print(f"⚠️ Auto-unmute failed for {member.display_name}: {e}")
