import contextlib
import discord  # type: ignore
from redbot.core import commands, Config, checks  # type: ignore
import redbot.core.data_manager  # type: ignore
import random
import os
import datetime
import logging
import traceback
import requests
import asyncio
from discord import app_commands  # type: ignore

class VSMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        current_directory = redbot.core.data_manager.cog_data_path(cog_instance=self)
        debug_file_path = f"{current_directory}/debug.log"
        self.debug_file = None
        self.identifier = self.bot.user.id
        self.config = Config.get_conf(self, identifier=self.identifier, force_registration=True)
        default_guild = {
            'muted_role_id': None,
            'banned_words': [],
            'actions': {
                'warning': False,
                'banning': False,
                'muting': False,
                'invite_link_filter': False
            },
            'thresholds': {
                'warning_threshold': 3,
                'muting_threshold': 5,
                'banning_threshold': 7,
                'muting_time': 5
            },
            'mod_actions': [],
            'warnings': {},
            'default_mute_duration': 5,
            'enable_debug': False,
            'suggestion_channel_id': None,
            'status_channel_id': None,
            'last_status': None
        }
        self.config.register_guild(**default_guild)
        self.status_task = self.bot.loop.create_task(self.check_status())

    def cog_unload(self):
        if self.status_task:
            self.status_task.cancel()

    async def cog_before_invoke(self, ctx):
        if not await self.get_muted_role(ctx.guild):
            await self.create_muted_role(ctx.guild)

    async def get_muted_role(self, guild):
        muted_role_id = await self.config.guild(guild).muted_role_id()
        if muted_role_id:
            return discord.utils.get(guild.roles, id=muted_role_id)
        return None

    async def create_muted_role(self, guild):
        muted_role = discord.utils.get(guild.roles, name="Muted")
        if not muted_role:
            try:
                muted_role = await guild.create_role(name="Muted")
                for channel in guild.channels:
                    await channel.set_permissions(muted_role, send_messages=False)
                await self.config.guild(guild).muted_role_id.set(muted_role.id)
            except Exception as e:
                print(f"Error creating muted role: {e}")

    async def debug_log(self, guild, command, message):
        current_directory = redbot.core.data_manager.cog_data_path(cog_instance=self)
        debug_file_path = f"{current_directory}/{guild.id}-debug.log"
        with open(debug_file_path, 'a') as debug_file:
            debug_file.write(f"{datetime.datetime.now()} - Command '{command}': {message}\n")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, ctx.command.name, f"Error: {str(error)}")

        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Sorry, I couldn't find that command. Use `!help` for a list of available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Oops! Looks like you're missing a required argument. Please check the command usage with `!help <command>`.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("One or more arguments are of the wrong type. Please check the command usage with `!help <command>`.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You do not have permission to use this command.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds.")
        elif isinstance(error, commands.DisabledCommand):
            await ctx.send("Sorry, this command is currently disabled.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command cannot be used in private messages.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send("I'm missing some permissions to execute this command.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You're missing some permissions to use this command.")
        elif isinstance(error, commands.CommandInvokeError):
            original_error = getattr(error, "original", error)
            await ctx.send(f"An error occurred while processing the command: {original_error}")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"An error occurred while processing the command: {error}")
        else:
            await ctx.send("An error occurred while processing the command. Please try again later.")

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @checks.has_permissions(manage_guild=True)
    @commands.group(name="banned_words")
    async def _banned_words(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "banned_words", "Running '_banned_words' command")

    @_banned_words.command()
    async def add(self, ctx, *, words: str):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'add' sub-command of '_banned_words' command")

        words = [word.strip().lower() for word in words.replace(" ", "").split(",")]
        banned_words = await self.config.guild(ctx.guild).banned_words()
        banned_words.extend(words)
        await self.config.guild(ctx.guild).banned_words.set(list(set(banned_words)))
        await ctx.send(f'Added {", ".join(words)} to the list of banned words.')

    @_banned_words.command()
    async def remove(self, ctx, *, words: str):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "remove", "Running 'remove' sub-command of '_banned_words' command")

        words = [word.strip().lower() for word in words.replace(" ", "").split(",")]
        banned_words = await self.config.guild(ctx.guild).banned_words()
        updated_banned_words = [word for word in banned_words if word not in words]
        await self.config.guild(ctx.guild).banned_words.set(updated_banned_words)
        await ctx.send(f'Removed {", ".join(words)} from the list of banned words.')

    @_banned_words.command()
    async def list(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "list", "Running 'list' sub-command of '_banned_words' command")

        banned_words = await self.config.guild(ctx.guild).banned_words()
        await ctx.send(f'Banned words: {", ".join(banned_words)}')

    @_banned_words.command(name="purge")
    async def purge_banned_words(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "purge", "Running 'purge_banned_words' sub-command of '_banned_words' command")

        await self.config.guild(ctx.guild).banned_words.set([])
        await ctx.send("Banned words list has been purged.")

    @_banned_words.group(name="settings")
    async def _bw_settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "settings", "Running '_bw_settings' sub-command of '_banned_words' command")

    @_bw_settings.command(name="view")
    async def view_bw_settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "view", "Running 'view' sub-command of '_bw_settings' command")

        actions = await self.config.guild(ctx.guild).actions()
        thresholds = await self.config.guild(ctx.guild).thresholds()

        embed = discord.Embed(
            title="Banned Words Settings",
            description="Current settings for banned words in this server",
            color=discord.Color.blue()
        )

        embed.add_field(name="Warning Enabled", value=str(actions['warning']))
        embed.add_field(name="Banning Enabled", value=str(actions['banning']))
        embed.add_field(name="Muting Enabled", value=str(actions['muting']))
        embed.add_field(name="Invite Link Filter Enabled", value=str(actions['invite_link_filter']))
        embed.add_field(name="Warning Threshold", value=str(thresholds['warning_threshold']))
        embed.add_field(name="Muting Threshold", value=str(thresholds['muting_threshold']))
        embed.add_field(name="Banning Threshold", value=str(thresholds['banning_threshold']))
        embed.add_field(name="Muting Time (minutes)", value=str(thresholds['muting_time']))

        await ctx.send(embed=embed)

    @_bw_settings.group(name="warn")
    async def _warn_bw_settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "warn_settings", "Running '_warn_bw_settings' sub-command of '_bw_settings' command")

    @_bw_settings.group(name="mute")
    async def _mute_bw_settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "mute_settings", "Running '_mute_bw_settings' sub-command of '_bw_settings' command")

    @_bw_settings.group(name="ban")
    async def _ban_bw_settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "ban_settings", "Running '_ban_bw_settings' sub-command of '_bw_settings' command")

    @_warn_bw_settings.command(name="set")
    async def set_warn(self, ctx, threshold: int):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "set_warn", "Running 'set_warn' sub-command of '_warn_bw_settings' command")

        await self.config.guild(ctx.guild).actions.warning.set(True)
        await self.config.guild(ctx.guild).thresholds.warning_threshold.set(threshold)
        await ctx.send(f'Set warning threshold to {threshold}.')

    @_mute_bw_settings.command(name="set")
    async def set_mute(self, ctx, threshold: int, time: int):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "set_mute", "Running 'set_mute' sub-command of '_mute_bw_settings' command")

        await self.config.guild(ctx.guild).actions.muting.set(True)
        await self.config.guild(ctx.guild).thresholds.muting_threshold.set(threshold)
        await self.config.guild(ctx.guild).thresholds.muting_time.set(time)

        await ctx.send(f'Set mute threshold to {threshold} warnings and mute duration to {time} minutes.')

    @_ban_bw_settings.command(name="set")
    async def set_ban(self, ctx, threshold: int):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "set_ban", "Running 'set_ban' sub-command of '_ban_bw_settings' command")

        await self.config.guild(ctx.guild).actions.banning.set(True)
        await self.config.guild(ctx.guild).thresholds.banning_threshold.set(threshold)
        await ctx.send(f'Set banning threshold to {threshold}.')

    @_warn_bw_settings.command(name="enable")
    async def warn_enable(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "warn_enable", "Running 'warn_enable' sub-command of '_warn_bw_settings' command")

        await self.config.guild(ctx.guild).actions.warning.set(True)
        await ctx.send('Warning threshold has been enabled.')

    @_warn_bw_settings.command(name="disable")
    async def warn_disable(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "warn_disable", "Running 'warn_disable' sub-command of '_warn_bw_settings' command")

        await self.config.guild(ctx.guild).actions.warning.set(False)
        await ctx.send('Warning threshold has been disabled.')

    @_mute_bw_settings.command(name="enable")
    async def mute_enable(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "mute_enable", "Running 'mute_enable' sub-command of '_mute_bw_settings' command")

        await self.config.guild(ctx.guild).actions.muting.set(True)
        await ctx.send('Muting threshold has been enabled.')

    @_mute_bw_settings.command(name="disable")
    async def mute_disable(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "mute_disable", "Running 'mute_disable' sub-command of '_mute_bw_settings' command")

        await self.config.guild(ctx.guild).actions.muting.set(False)
        await ctx.send('Muting threshold has been disabled.')

    @_ban_bw_settings.command(name="enable")
    async def ban_enable(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "ban_enable", "Running 'ban_enable' sub-command of '_ban_bw_settings' command")

        await self.config.guild(ctx.guild).actions.banning.set(True)
        await ctx.send('Banning threshold has been enabled.')

    @_ban_bw_settings.command(name="disable")
    async def ban_disable(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "ban_disable", "Running 'ban_disable' sub-command of '_ban_bw_settings' command")

        await self.config.guild(ctx.guild).actions.banning.set(False)
        await ctx.send('Banning threshold has been disabled.')

    async def contains_invite_link(self, input_string):
        return "discord.gg" in input_string

    @commands.Cog.listener()
    async def on_message(self, message):  # sourcery skip: low-code-quality
        if message.guild is None or message.author.bot:
            return

        if await self.config.guild(message.guild).enable_debug():
            await self.debug_log(message.guild, "on_message", "Running 'on_message' listener")

        content = message.content.lower()
        content_words = content.split()

        if content.startswith("!banned_words add") or content.startswith("!banned_words remove"):
            return

        banned_words = await self.config.guild(message.guild).banned_words()

        if any(word in content_words for word in banned_words):
            actions = await self.config.guild(message.guild).actions()
            thresholds = await self.config.guild(message.guild).thresholds()

            if actions['warning']:
                warnings = await self.config.guild(message.guild).warnings()
                user_warnings = warnings.get(str(message.author.id), [])
                user_warnings.append("Used banned words")
                warnings[str(message.author.id)] = user_warnings
                await self.config.guild(message.guild).warnings.set(warnings)

                warning_threshold = thresholds['warning_threshold']

                if len(user_warnings) >= warning_threshold:
                    await message.channel.send(f'{message.author.mention}, you have reached the warning threshold and may face further actions.')
                    await message.author.send(f'You have received a warning in the server {message.guild.name} for using banned words.')
                    await message.author.send('Reason: Used banned words')

            if actions['banning']:
                warnings = await self.config.guild(message.guild).warnings()
                user_warnings = warnings.get(str(message.author.id), [])
                user_warnings.append("Used banned words")
                warnings[str(message.author.id)] = user_warnings
                await self.config.guild(message.guild).warnings.set(warnings)

                banning_threshold = thresholds['banning_threshold']

                if len(user_warnings) >= banning_threshold:
                    await message.author.ban(reason='Used banned words.')
                    await message.author.send(f'You have been banned from the server {message.guild.name} for repeatedly using banned words.')
                    await message.author.send('Reason: Used banned words')

            if actions['muting']:
                muted_role = await self.get_muted_role(message.guild)
                if muted_role is None:
                    await self.create_muted_role(message.guild)
                    muted_role = await self.get_muted_role(message.guild)

                if muted_role is None:
                    await self.debug_log(message.guild, "on_message", f"Error creating muted role for server {message.guild.name}")
                    return

                warnings = await self.config.guild(message.guild).warnings()
                user_warnings = warnings.get(str(message.author.id), [])
                user_warnings.append("Used banned words")
                warnings[str(message.author.id)] = user_warnings
                await self.config.guild(message.guild).warnings.set(warnings)

                muting_threshold = thresholds['muting_threshold']

                if len(user_warnings) >= muting_threshold:
                    mute_duration = thresholds['muting_time']
                    await message.author.send(f'You have been muted in the server {message.guild.name} for using banned words for {mute_duration} minutes.')
                    await message.author.send('Reason: Used banned words')

                    await message.author.add_roles(muted_role)

                await message.delete()
                await message.author.send(f"Your message has been removed from {message.guild.name} for containing a banned word.")
                await message.channel.send(f'{message.author.mention}, your message has been removed for containing a banned word.')

        if await self.config.guild(message.guild).actions.invite_link_filter() and await self.contains_invite_link(message.content):
            print("Detected invite link in message:", message.content)

            actions = await self.config.guild(message.guild).actions()
            thresholds = await self.config.guild(message.guild).thresholds()

            if actions['warning']:
                warnings = await self.config.guild(message.guild).warnings()
                user_warnings = warnings.get(str(message.author.id), [])
                user_warnings.append("Sent an invite link")
                warnings[str(message.author.id)] = user_warnings
                await self.config.guild(message.guild).warnings.set(warnings)

                warning_threshold = thresholds['warning_threshold']

                if len(user_warnings) >= warning_threshold:
                    await message.channel.send(f'{message.author.mention}, you have reached the warning threshold and may face further actions.')
                    await message.author.send(f'You have received a warning in the server {message.guild.name} for sending an invite link.')
                    await message.author.send('Reason: Sent an invite link')

            if actions['banning']:
                warnings = await self.config.guild(message.guild).warnings()
                user_warnings = warnings.get(str(message.author.id), [])
                user_warnings.append("Sent an invite link")
                warnings[str(message.author.id)] = user_warnings
                await self.config.guild(message.guild).warnings.set(warnings)

                banning_threshold = thresholds['banning_threshold']

                if len(user_warnings) >= banning_threshold:
                    await message.author.ban(reason='Sent an invite link.')
                    await message.author.send(f'You have been banned from the server {message.guild.name} for repeatedly sending invite links.')
                    await message.author.send('Reason: Sent an invite link.')

            if actions['muting']:
                muted_role = await self.get_muted_role(message.guild)
                if muted_role is None:
                    await self.create_muted_role(message.guild)
                    muted_role = await self.get_muted_role(message.guild)

                if muted_role is None:
                    await self.debug_log(message.guild, "on_message", f"Error creating muted role for server {message.guild.name}")
                    return

                warnings = await self.config.guild(message.guild).warnings()
                user_warnings = warnings.get(str(message.author.id), [])
                user_warnings.append("Sent an invite link")
                warnings[str(message.author.id)] = user_warnings
                await self.config.guild(message.guild).warnings.set(warnings)

                muting_threshold = thresholds['muting_threshold']

                if len(user_warnings) >= muting_threshold:
                    await message.author.send(f'You have been muted in the server {message.guild.name} for sending an invite link.')
                    await message.author.send('Reason: Sent an invite link.')
                    await message.author.add_roles(muted_role)

                    muting_time = thresholds['muting_time']
                    await asyncio.sleep(muting_time * 60)
                    await message.author.remove_roles(muted_role)
                    await message.author.send(f'You have been unmuted in the server {message.guild.name}.')

                try:
                    await message.delete()
                    print(f"Deleted message from {message.author} containing an invite link")
                except discord.Forbidden:
                    print("Bot doesn't have permission to delete messages.")

                try:
                    await message.author.send(f"Your message has been removed from {message.guild.name} for sending an invite link.")
                    print("Sent DM to the user")
                except discord.Forbidden:
                    print("Bot can't send DMs to the user.")

                try:
                    await message.channel.send(f'{message.author.mention}, your message has been removed for sending an invite link.')
                    print("Sent message to the channel")
                except discord.Forbidden:
                    print("Bot can't send messages to the channel.")

    async def handle_warn(self, interaction_or_ctx, user: discord.Member, reason: str):
        guild = interaction_or_ctx.guild
        warnings = await self.config.guild(guild).warnings()
        user_warnings = warnings.get(str(user.id), [])
        user_warnings.append(reason)
        warnings[str(user.id)] = user_warnings
        await self.config.guild(guild).warnings.set(warnings)

        await user.send(f'You have received a warning in the server {guild.name}. Reason: {reason}')

        if isinstance(interaction_or_ctx, commands.Context):
            await interaction_or_ctx.send(f'{user.mention} has been warned for: {reason}')
        else:
            await interaction_or_ctx.response.send_message(f'{user.mention} has been warned for: {reason}', ephemeral=True)

    @commands.command(name="warn")
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    async def warn_command(self, ctx, user: discord.Member, *, reason: str):
        await self.handle_warn(ctx, user, reason)

    @app_commands.command(name="warn", description="Warn a member for a specified reason")
    @app_commands.describe(user="The member to warn", reason="The reason for warning the user")
    async def warn_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await self.handle_warn(interaction, user, reason)

    async def handle_kick(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if await self.config.guild(interaction.guild).enable_debug():
            await self.debug_log(interaction.guild, "kick", f"Running 'kick' command with user {user.name}#{user.discriminator} ({user.id}) and reason: {reason}")
            return

        await user.kick(reason=reason)

        try:
            await user.send(f'You have been kicked from the server {interaction.guild.name}. Reason: {reason}')
        except discord.Forbidden:
            await interaction.response.send_message(f'Could not send a DM to {user.mention}.')

        mod_actions = await self.config.guild(interaction.guild).mod_actions()
        mod_actions.append({
            'moderator': interaction.user.id,
            'action': 'kick',
            'user': user.id,
            'reason': reason
        })
        await self.config.guild(interaction.guild).mod_actions.set(mod_actions)

        await interaction.response.send_message(f'{user.mention} has been kicked for: {reason}')

    @commands.command(name="kick")
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    async def kick_command(self, ctx, user: discord.Member, *, reason: str):
        await self.handle_kick(ctx, user, reason)

    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    @app_commands.command(name="kick", description="Kick a member for a specified reason")
    @app_commands.describe(user="The member to kick", reason="The reason for kicking the user")
    async def kick_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await self.handle_kick(interaction, user, reason)

    async def handle_mute(self, interaction: discord.Interaction, user: discord.Member, time: int, reason: str):
        muted_role = await self.get_muted_role(interaction.guild)
        if muted_role is None:
            await self.create_muted_role(interaction.guild)
            muted_role = await self.get_muted_role(interaction.guild)

        if muted_role is None:
            await interaction.response.send_message("Error creating muted role. Please check the bot's permissions and try again.")
            return

        if time is not None:
            await self.config.guild(interaction.guild).actions.muting.set(True)
            await self.config.guild(interaction.guild).thresholds.muting_threshold.set(1)
            await self.config.guild(interaction.guild).thresholds.muting_time.set(time)

        await user.add_roles(muted_role)

        try:
            if time is not None:
                await user.send(f'You have been muted in the server {interaction.guild.name} for {time} minutes. Reason: {reason}')
            else:
                await user.send(f'You have been muted indefinitely in the server {interaction.guild.name}. Reason: {reason}')
        except discord.Forbidden:
            await interaction.response.send_message(f'Could not send a DM to {user.mention}.')

        mod_actions = await self.config.guild(interaction.guild).mod_actions()
        mod_actions.append({
            'moderator': interaction.user.id,
            'action': 'mute',
            'user': user.id,
            'reason': reason
        })
        await self.config.guild(interaction.guild).mod_actions.set(mod_actions)

        if time is not None:
            await interaction.response.send_message(f'{user.mention} has been muted for {time} minutes for: {reason}')
        else:
            await interaction.response.send_message(f'{user.mention} has been muted indefinitely for: {reason}')

    @commands.command(name="mute")
    @commands.guild_only()
    @checks.has_permissions(manage_roles=True)
    async def mute_command(self, ctx, user: discord.Member, time: int = None, *, reason: str):
        await self.handle_mute(ctx, user, time, reason)

    @commands.guild_only()
    @checks.has_permissions(manage_roles=True)
    @app_commands.command(name="mute", description="Mute a member for a specified time and reason")
    @app_commands.describe(user="The member to mute", reason="The reason for muting the user", time="Duration to mute the user (in minutes, optional)")
    async def mute_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str, time: int = None):
        await self.handle_mute(interaction, user, time, reason)

    async def handle_ban(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await user.ban(reason=reason)
        try:
            await user.send(f'You have been banned from the server {interaction.guild.name}. Reason: {reason}')
        except discord.Forbidden:
            await interaction.response.send_message(f'Could not send a DM to {user.mention}.')

        await interaction.response.send_message(f'{user.mention} has been banned for: {reason}')

    @commands.command(name="ban")
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    async def ban_command(self, ctx, user: discord.Member, *, reason: str):
        await self.handle_ban(ctx, user, reason)

    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    @app_commands.command(name="ban", description="Ban a member for a specified reason")
    @app_commands.describe(user="The member to ban", reason="The reason for banning the user")
    async def ban_slash(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await self.handle_ban(interaction, user, reason)

    async def handle_unmute(self, interaction: discord.Interaction, user: discord.Member):
        muted_role = await self.get_muted_role(interaction.guild)
        if muted_role is None:
            await self.create_muted_role(interaction.guild)
            muted_role = await self.get_muted_role(interaction.guild)

        if muted_role is None:
            await interaction.response.send_message("Error creating muted role. Please check the bot's permissions and try again.")
            return

        if muted_role and muted_role in user.roles:
            await user.remove_roles(muted_role)
            await interaction.response.send_message(f'{user.mention} has been unmuted.')
        else:
            await interaction.response.send_message(f'{user.mention} is not muted.')

    @commands.command(name="unmute")
    @commands.guild_only()
    @checks.has_permissions(manage_roles=True)
    async def unmute_command(self, ctx, user: discord.Member):
        await self.handle_unmute(ctx, user)

    @commands.guild_only()
    @checks.has_permissions(manage_roles=True)
    @app_commands.command(name="unmute", description="Unmute a member")
    @app_commands.describe(user="The member to unmute")
    async def unmute_slash(self, interaction: discord.Interaction, user: discord.Member):
        await self.handle_unmute(interaction, user)

    async def handle_unban(self, interaction: discord.Interaction, user: discord.User):
        await interaction.guild.unban(user)
        await interaction.response.send_message(f'{user.mention} has been unbanned.')

    @commands.command(name="unban")
    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    async def unban_command(self, ctx, user: discord.User):
        await self.handle_unban(ctx, user)

    @commands.guild_only()
    @checks.has_permissions(ban_members=True)
    @app_commands.command(name="unban", description="Unban a member")
    @app_commands.describe(user="The user to unban")
    async def unban_slash(self, interaction: discord.Interaction, user: discord.User):
        await self.handle_unban(interaction, user)

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(ban_members=True)
    async def clear_warnings(self, ctx, user: discord.Member):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "clear_warnings", f"Running 'clear_warnings' command with user {user.name}#{user.discriminator} ({user.id})")

        warnings = await self.config.guild(ctx.guild).warnings()
        if user_warnings := warnings.get(str(user.id), []):
            warnings[str(user.id)] = []
            await self.config.guild(ctx.guild).warnings.set(warnings)
            await ctx.send(f'Warnings for {user.mention} have been cleared.')
        else:
            await ctx.send(f'{user.mention} has no warnings.')

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(ban_members=True)
    async def view_warnings(self, ctx, user: discord.Member = None):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "view_warnings", "Running 'view_warnings' command")

        if not user:
            user = ctx.author

        if user != ctx.author and not ctx.author.guild_permissions.ban_members:
            return await ctx.send("You can only view your own warnings.")

        warnings = await self.config.guild(ctx.guild).warnings()
        user_warnings = warnings.get(str(user.id), [])
        if user_warnings:
            warnings_embeds = []
            instructions = "React with ❌ to delete a warning (only available for moderators).\nReact with ✅ to close this message.\nUse ⬅️ ➡️ to navigate."

            instructions_embed = discord.Embed(
                title="Instructions",
                description=instructions,
                color=discord.Color.green()
            )
            warnings_embeds.append(instructions_embed)

            for idx, reason in enumerate(user_warnings, start=1):
                embed = discord.Embed(
                    title=f'Warning {idx}',
                    description=f'User: {user.mention}\nModerator: {ctx.author.mention}\nReason: {reason}',
                    color=discord.Color.orange()
                )
                embed.set_footer(text=f'Page {idx}/{len(user_warnings)}')
                warnings_embeds.append(embed)

            current_page = 0
            message = await ctx.send(embed=warnings_embeds[current_page])
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")
            await message.add_reaction("❌")
            await message.add_reaction("✅")

            def check(reaction, user):
                return (
                    user == ctx.author
                    and reaction.message.id == message.id
                    and str(reaction.emoji) in {"❌", "✅", "⬅️", "➡️"}
                )

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                except asyncio.TimeoutError:
                    break
                else:
                    if str(reaction.emoji) == "➡️":
                        if current_page < len(warnings_embeds) - 1:
                            current_page += 1
                            await message.edit(embed=warnings_embeds[current_page])
                    elif str(reaction.emoji) == "⬅️":
                        if current_page > 0:
                            current_page -= 1
                            await message.edit(embed=warnings_embeds[current_page])
                    elif str(reaction.emoji) == "\u274c":
                        if ctx.author.guild_permissions.ban_members:
                            if 0 <= current_page - 1 < len(user_warnings):
                                deleted_warning = user_warnings.pop(current_page - 1)
                                warnings[str(user.id)] = user_warnings

                                warnings_embeds = [instructions_embed]
                                for idx, reason in enumerate(user_warnings, start=1):
                                    embed = discord.Embed(
                                        title=f'Warning {idx}',
                                        description=f'User: {user.mention}\nModerator: {ctx.author.mention}\nReason: {reason}',
                                        color=discord.Color.orange()
                                    )
                                    embed.set_footer(text=f'Page {idx}/{len(user_warnings)}')
                                    warnings_embeds.append(embed)

                                await self.config.guild(ctx.guild).warnings.set(warnings)

                                if len(user_warnings) > 0:
                                    current_page = min(current_page, len(user_warnings))
                                    await message.edit(embed=warnings_embeds[current_page])
                                else:
                                    with contextlib.suppress(discord.NotFound):
                                        await message.delete()
                                    break
                            else:
                                await ctx.send("Invalid page index.")
                        else:
                            await ctx.send("You do not have permission to delete warnings.")
                    elif str(reaction.emoji) == "✅":
                        await message.delete()
                        break
                    await message.remove_reaction(reaction, user)
        else:
            await ctx.send(f'{user.mention} has no warnings.')

    @commands.command(name="suggest")
    async def _suggest(self, ctx, *, suggestion):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "suggest", "Running 'suggest' command")

        suggestion_channel_id = await self.config.guild(ctx.guild).suggestion_channel_id()

        if suggestion_channel_id is None:
            await ctx.send('Please ask the server owner to set the suggestion channel first.')
            return

        suggestion_channel = self.bot.get_channel(suggestion_channel_id)

        if suggestion_channel is not None:
            embed = discord.Embed(
                title="New Suggestion",
                description=suggestion,
                color=discord.Color.blue()
            )

            embed.set_footer(text=f"Suggested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)

            message = await suggestion_channel.send(embed=embed)
            await message.add_reaction("👍")
            await message.add_reaction("👎")

            await ctx.message.delete()
            await ctx.send('Your suggestion has been submitted!')
        else:
            await ctx.send('Suggestion channel not found. Please ask the server owner to set it.')

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @checks.has_permissions(manage_guild=True)
    @commands.group(name="settings")
    async def _settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "settings", "Running '_settings' command")

    @_settings.group(name="mod")
    async def _mod_settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "mod_settings", "Running '_mod_settings' command")

    @_mod_settings.group(name="mute")
    async def _mute_settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "mute_settings", "Running '_mute_settings' command")

    @_mute_settings.command(name="set_duration")
    async def set_mute_duration(self, ctx, duration: int):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "set_mute_duration", "Running 'set_mute_duration' sub-command of '_mute_settings' command")

        await self.config.guild(ctx.guild).default_mute_duration.set(duration)
        await ctx.send(f'Default mute duration set to {duration} minutes.')

    @_settings.group(name="suggestion")
    async def _suggestion_settings(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "suggestion_settings", "Running '_suggestion_settings' command")

    @_suggestion_settings.command(name="set_channel")
    async def set_suggestion_channel(self, ctx, channel: discord.TextChannel):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "set_suggestion_channel", "Running 'set_suggestion_channel' command")

        if ctx.author.guild_permissions.administrator:
            await self.config.guild(ctx.guild).suggestion_channel_id.set(channel.id)
            await ctx.send(f'Suggestion channel set to {channel.mention}.')
        else:
            await ctx.send('You must have administrator permissions to set the suggestion channel.')

    async def handle_clean(self, interaction_or_ctx, num_messages: int):
        if 1 <= num_messages <= 100:
            channel = interaction_or_ctx.channel
            deleted_messages = await channel.purge(limit=num_messages + 1)
            if isinstance(interaction_or_ctx, commands.Context):
                await interaction_or_ctx.send(f"Deleted {len(deleted_messages)} message(s).", delete_after=5)
            else:
                await interaction_or_ctx.response.send_message(f"Deleted {len(deleted_messages)} message(s).", ephemeral=True)
        elif isinstance(interaction_or_ctx, commands.Context):
            await interaction_or_ctx.send("Please provide a number between 1 and 100.", delete_after=5)
        else:
            await interaction_or_ctx.response.send_message("Please provide a number between 1 and 100.", ephemeral=True)

    @commands.command(name="clean", aliases=["purge"])
    @commands.guild_only()
    @checks.has_permissions(manage_messages=True)
    async def clean_command(self, ctx, num_messages: int):
        await self.handle_clean(ctx, num_messages)

    @app_commands.command(name="clean", description="Clean a specified number of messages from the channel")
    @app_commands.describe(num_messages="Number of messages to delete (1-100)")
    async def clean_slash(self, interaction: discord.Interaction, num_messages: int):
        await self.handle_clean(interaction, num_messages)

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @checks.has_permissions(manage_guild=True)
    @commands.group(name="invite_filter")
    async def _invite_filter(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "invite_filter", "Running 'invite_filter' command")

    @_invite_filter.command(name="enable")
    async def enable_invite_filter(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "enable_invite_filter", "Running 'enable' sub-command of 'invite_filter' command")

        await self.config.guild(ctx.guild).actions.invite_link_filter.set(True)
        await ctx.send('Invite link filter has been enabled.')

    @_invite_filter.command(name="disable")
    async def disable_invite_filter(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "disable_invite_filter", "Running 'disable' sub-command of 'invite_filter' command")

        await self.config.guild(ctx.guild).actions.invite_link_filter.set(False)
        await ctx.send('Invite link filter has been disabled.')

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @checks.has_permissions(manage_guild=True)
    @commands.group(name="owner_settings")
    async def _owner_settings(self, ctx):
        pass

    @_owner_settings.group(name="enable_debug")
    async def _enable_debug(self, ctx):
        pass

    @_enable_debug.command()
    async def true(self, ctx):
        await self.config.guild(ctx.guild).enable_debug.set(True)
        await ctx.send("Debug mode enabled.")

    @_enable_debug.command()
    async def false(self, ctx):
        await self.config.guild(ctx.guild).enable_debug.set(False)
        await ctx.send("Debug mode disabled.")

    @_owner_settings.command(name="read_debug_log")
    async def read_debug_log(self, ctx):
        current_directory = redbot.core.data_manager.cog_data_path(cog_instance=self)
        debug_file_path = f"{current_directory}/{ctx.guild.id}-debug.log"

        try:
            with open(debug_file_path, 'r') as debug_file:
                log_contents = debug_file.read()
                await ctx.send(f"Debug Log Contents for {ctx.guild.name}:\n```{log_contents}```")
        except FileNotFoundError:
            await ctx.send("debug.log file not found.")

    async def check_status(self):
        try:
            while True:
                try:
                    response = requests.get("https://discordstatus.com/api/v2/status.json")
                    response.raise_for_status()
                    data = response.json()
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching Discord status: {e}")
                    await asyncio.sleep(300)
                    continue

                current_status = data['status']['description']
                components = data['components']

                for guild in self.bot.guilds:
                    status_channel_id = await self.config.guild(guild).status_channel_id()
                    if not status_channel_id:
                        continue

                    last_status = await self.config.guild(guild).last_status()

                    if current_status != last_status:
                        status_message = self.format_status_message(current_status, components)
                        await self.post_update(guild, status_message)
                        await self.config.guild(guild).last_status.set(current_status)

                await asyncio.sleep(300)
        except asyncio.CancelledError:
            print("Status checking task was cancelled.")

    def format_status_message(self, status, components):
        message = f"**Discord Status Update**\n\n"
        message += f"**Status**: {status}\n\n"
        for component in components:
            if component['status'] != "operational":
                message += f"**{component['name']}**: {component['status']}\n"
        return message

    async def post_update(self, guild, message):
        channel_id = await self.config.guild(guild).status_channel_id()
        if channel := self.bot.get_channel(channel_id):
            await channel.send(message)

    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    @commands.group(name="settings", invoke_without_command=True)
    async def _settings(self, ctx):
        await ctx.send("Available settings: mod, discord-status, suggestion")

    @_settings.group(name="discord-status", invoke_without_command=True)
    async def _discord_status(self, ctx):
        await ctx.send("Available discord-status commands: setstatuschannel")

    @_discord_status.command(name="setstatuschannel")
    async def set_status_channel(self, ctx, channel: discord.TextChannel):
        await self.config.guild(ctx.guild).status_channel_id.set(channel.id)
        await ctx.send(f"Discord status updates will be sent to {channel.mention}")
