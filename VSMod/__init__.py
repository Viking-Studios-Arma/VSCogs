from .vsmod import VSMod

__red_end_user_data_statement__ = (
    'Data such as UIDs of server members and Moderators along with GuildID and RoleID may be stored by the cog for keeping track of user warnings, mutes, bans, and offenses.'
)

async def setup(bot):
    cog = VSMod(bot)
    await bot.add_cog(cog)

    # Sync the slash commands globally or to a specific guild
    await bot.tree.sync()
