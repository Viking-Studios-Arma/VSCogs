from .vsmod import VSMod

async def setup(bot):
    await bot.add_cog(VSMod(bot))
