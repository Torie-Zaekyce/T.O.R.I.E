COGS = [
    "cogs.general",
    "cogs.moderation_commands",
    "cogs.birthday",
    "cogs.personality",
    "cogs.permissions",
    "cogs.memory",
    "cogs.interactions",
    "cogs.voice",
    "cogs.settings",
]


async def load_cogs(bot):
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            print(f"❌ Failed to load cog {cog}: {type(e).__name__}: {e}")
