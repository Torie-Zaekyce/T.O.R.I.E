# bot/bot.py — cog loading (replace your existing setup_commands() call with this)
#
# In your main async setup / on_ready, call:
#
#   await load_cogs(bot)
#   await bot.tree.sync()      # only needed once after slash commands change

COGS = [
    "cogs.general",
    "cogs.moderation",
    "cogs.birthday",
    "cogs.personality",
    "cogs.permissions",
    "cogs.memory",
    "cogs.interactions",
]


async def load_cogs(bot):
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {type(e).__name__}: {e}")
