import contextlib
import discord # type: ignore
from redbot.core import commands, Config, checks # type: ignore
import redbot.core.data_manager # type: ignore
import random
import os
import datetime
import logging
import traceback
import requests
import asyncio
from discord_slash import SlashCommand, SlashContext # type: ignore
from discord_slash.utils.manage_commands import create_option, create_choice # type: ignore

class VSMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.slash = SlashCommand(bot, sync_commands=True)
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
            'enable_debug': False,  # Added enable_debug option
            'suggestion_channel_id': None,
            'status_channel_id': None,
            'last_status': None
        }
        self.config.register_guild(**default_guild)
        self.bot.loop.create_task(self.check_status())
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
        # sourcery skip: low-code-quality
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, ctx.command.name, f"Error: {str(error)}")
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("Sorry, I couldn't find that command. Use `!help` for a list of available commands.")
        if ctx.command.name == 'add':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please provide the words you want to add.")
        elif ctx.command.name == 'remove':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please provide the words you want to remove.")
        elif ctx.command.name == 'set_warn':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please provide the warning threshold.")
        elif ctx.command.name == 'set_mute':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please provide the mute threshold and time.")
        elif ctx.command.name == 'set_ban':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please provide the banning threshold.")
        elif ctx.command.name == 'warn':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please mention the user and provide a reason.")
        elif ctx.command.name == 'kick':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please mention the user and provide a reason.")
        elif ctx.command.name == 'mute':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please mention the user, provide a mute duration, and provide a reason.")
        elif ctx.command.name == 'ban':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please mention the user and provide a reason.")
        elif ctx.command.name == 'unmute':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please mention the user.")
        elif ctx.command.name == 'unban':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please mention the user.")
        elif ctx.command.name == 'clear_warnings':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please mention the user.")
        elif ctx.command.name == 'view_warnings':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please mention the user.")
        elif ctx.command.name == 'set_suggestion_channel':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please provide the channel.")
        elif ctx.command.name == '_suggest':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please provide your suggestion.")
        elif ctx.command.name == 'set_mute_duration':
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("Please provide the mute duration.")

        if isinstance(error, commands.UserInputError):
            await ctx.send("There was an issue with the provided argument. Please check your input and try again.")
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
            # Handle any other specific errors here, or provide a generic error message
            await ctx.send("An error occurred while processing the command. Please try again later.")

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @commands.group(name="banned_words")
    async def _banned_words(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_banned_words' command")
            return

    @_banned_words.command()
    async def add(self, ctx, *, words: str):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'add' sub-command of '_banned_words' command")
            return
        words = [word.strip().lower() for word in words.replace(" ", "").split(",")]
        banned_words = await self.config.guild(ctx.guild).banned_words()
        banned_words.extend(words)
        await self.config.guild(ctx.guild).banned_words.set(list(set(banned_words)))  # Remove duplicates
        await ctx.send(f'Added {", ".join(words)} to the list of banned words.')

    @_banned_words.command()
    async def remove(self, ctx, *, words: str):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'remove' sub-command of '_banned_words' command")
            return
        words = [word.strip().lower() for word in words.replace(" ", "").split(",")]
        banned_words = await self.config.guild(ctx.guild).banned_words()
        updated_banned_words = [word for word in banned_words if word not in words]
        await self.config.guild(ctx.guild).banned_words.set(updated_banned_words)
        await ctx.send(f'Removed {", ".join(words)} from the list of banned words.')

    @_banned_words.command()
    async def list(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'list' sub-command of '_banned_words' command")
            return
        banned_words = await self.config.guild(ctx.guild).banned_words()
        await ctx.send(f'Banned words: {", ".join(banned_words)}')

    @_banned_words.command(name="purge")
    async def purge_banned_words(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'purge_banned_words' sub-command of '_banned_words' command")
            return
        await self.config.guild(ctx.guild).banned_words.set([])
        await ctx.send("Banned words list has been purged.")

    @_banned_words.group(name="settings")
    async def _bw_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_bw_settings' sub-command of '_banned_words' command")
            return

    @_bw_settings.command(name="view")
    async def view_bw_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'view' sub-command of 'settings' command")
            return

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
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_warn_bw_settings' sub-command of '_bw_settings' command")
            return

    @_bw_settings.group(name="mute")
    async def _mute_bw_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_mute_bw_settings' sub-command of '_bw_settings' command")
            return

    @_bw_settings.group(name="ban")
    async def _ban_bw_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_ban_bw_settings' sub-command of '_bw_settings' command")
            return

    # Set commands
    @_warn_bw_settings.command(name="set")
    async def set_warn(self, ctx, threshold: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_warn' sub-command of '_warn_bw_settings' command")
            return

        # Set warning threshold
        await self.config.guild(ctx.guild).actions.warning.set(True)
        await self.config.guild(ctx.guild).thresholds.warning_threshold.set(threshold)
        await ctx.send(f'Set warning threshold to {threshold}.')

    @_mute_bw_settings.command(name="set")
    async def set_mute(self, ctx, threshold: int, time: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_mute' sub-command of '_mute_bw_settings' command")
            return

        # Set muting actions and thresholds
        await self.config.guild(ctx.guild).actions.muting.set(True)
        await self.config.guild(ctx.guild).thresholds.muting_threshold.set(threshold)
        await self.config.guild(ctx.guild).thresholds.muting_time.set(time)

        await ctx.send(f'Set mute threshold to {threshold} warnings and mute duration to {time} minutes.')

    @_ban_bw_settings.command(name="set")
    async def set_ban(self, ctx, threshold: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_ban' sub-command of '_ban_bw_settings' command")
            return

        # Set banning threshold
        await self.config.guild(ctx.guild).actions.banning.set(True)
        await self.config.guild(ctx.guild).thresholds.banning_threshold.set(threshold)
        await ctx.send(f'Set banning threshold to {threshold}.')

    # Enable/Disable commands
    @_warn_bw_settings.command(name="enable")
    async def warn_enable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'warn_enable' sub-command of '_warn_bw_settings' command")
            return

        # Enable warning threshold
        await self.config.guild(ctx.guild).actions.warning.set(True)
        await ctx.send('Warning threshold has been enabled.')

    @_warn_bw_settings.command(name="disable")
    async def warn_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'warn_disable' sub-command of '_warn_bw_settings' command")
            return

        # Disable warning threshold
        await self.config.guild(ctx.guild).actions.warning.set(False)
        await ctx.send('Warning threshold has been disabled.')

    @_mute_bw_settings.command(name="enable")
    async def mute_enable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'mute_enable' sub-command of '_mute_bw_settings' command")
            return

        # Enable muting threshold
        await self.config.guild(ctx.guild).actions.muting.set(True)
        await ctx.send('Muting threshold has been enabled.')

    @_mute_bw_settings.command(name="disable")
    async def mute_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'mute_disable' sub-command of '_mute_bw_settings' command")
            return

        # Disable muting threshold
        await self.config.guild(ctx.guild).actions.muting.set(False)
        await ctx.send('Muting threshold has been disabled.')

    @_ban_bw_settings.command(name="enable")
    async def ban_enable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'ban_enable' sub-command of '_ban_bw_settings' command")
            return

        # Enable banning threshold
        await self.config.guild(ctx.guild).actions.banning.set(True)
        await ctx.send('Banning threshold has been enabled.')

    @_ban_bw_settings.command(name="disable")
    async def ban_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'ban_disable' sub-command of '_ban_bw_settings' command")
            return

        # Disable banning threshold
        await self.config.guild(ctx.guild).actions.banning.set(False)
        await ctx.send('Banning threshold has been disabled.')

    async def contains_invite_link(self, input_string):
        return "discord.gg" in input_string

    @commands.Cog.listener()  # sourcery skip: low-code-quality
    async def on_message(self, message):
        if message.guild is None or message.author.bot:
            return
        #Add debug print statement
        if await self.config.guild(message.guild).enable_debug():
            await self.debug_log(message.guild, "on_message", "Running 'on_message' listener")
            return

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
                    # Send a DM to the user
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
                    # Send a DM to the user
                    await message.author.send(f'You have been banned from the server {message.guild.name} for repeatedly using banned words.')
                    await message.author.send('Reason: Used banned words')

            if actions['muting']:
                # Check if muted role exists, create one if not
                muted_role = await self.get_muted_role(message.guild)
                if muted_role is None:
                    await self.create_muted_role(message.guild)
                    muted_role = await self.get_muted_role(message.guild)

                # If after creating it's still None, something went wrong, log it
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
                    # Calculate the mute duration (in minutes)
                    mute_duration = thresholds['muting_time']

                    # Send a DM to the user with the mute duration
                    await message.author.send(f'You have been muted in the server {message.guild.name} for using banned words for {mute_duration} minutes.')
                    await message.author.send('Reason: Used banned words')

                    await message.author.add_roles(muted_role)

                # Delete the message and notify the user
                await message.delete()
                await message.author.send(f"Your message has been removed from {message.guild.name} for containing a banned word.")
                await message.channel.send(f'{message.author.mention}, your message has been removed for containing a banned word.')

        # Invite Link Filter
        if await self.config.guild(message.guild).actions.invite_link_filter() and await self.contains_invite_link(message.content):
            print("Detected invite link in message:", message.content)  # Debug print
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

                    await asyncio.sleep(muting_time * 60)  # Sleep for muting time in seconds
                    await message.author.remove_roles(muted_role)
                    await message.author.send(f'You have been unmuted in the server {message.guild.name}.')

                try:
                    await message.delete()
                    print(f"Deleted message from {message.author} containing an invite link")  # Debug print
                except discord.Forbidden:
                    print("Bot doesn't have permission to delete messages.")  # Debug print

                try:
                    await message.author.send(f"Your message has been removed from {message.guild.name} for sending an invite link.")
                    print("Sent DM to the user")  # Debug print
                except discord.Forbidden:
                    print("Bot can't send DMs to the user.")  # Debug print

                try:
                    await message.channel.send(f'{message.author.mention}, your message has been removed for sending an invite link.')
                    print("Sent message to the channel")  # Debug print
                except discord.Forbidden:
                    print("Bot can't send messages to the channel.")
                    print("Bot can't send messages to the channel.")

    async def handle_warn(self, ctx, user: discord.Member, reason: str):
        warnings = await self.config.guild(ctx.guild).warnings()
        user_warnings = warnings.get(str(user.id), [])
        user_warnings.append(reason)
        warnings[str(user.id)] = user_warnings
        await self.config.guild(ctx.guild).warnings.set(warnings)

        await user.send(f'You have received a warning in the server {ctx.guild.name}. Reason: {reason}')
        await ctx.send(f'{user.mention} has been warned for: {reason}')

    @commands.command(name="warn")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def warn_command(self, ctx, user: discord.Member, *, reason: str):
        await self.handle_warn(ctx, user, reason)

    @slash.slash( # type: ignore
        name="warn",
        description="Warn a member for a specified reason",
        options=[
            create_option(
                name="user",
                description="The member to warn",
                option_type=6,  # User type
                required=True
            ),
            create_option(
                name="reason",
                description="The reason for warning the user",
                option_type=3,  # String type
                required=True
            ),
        ],
    )
    async def warn_slash(self, ctx: SlashContext, user: discord.Member, reason: str):
        await self.handle_warn(ctx, user, reason)


    @slash.slash( # type: ignore
        name="kick",
        description="Kick a member for a specified reason",
        options=[
            create_option(
                name="user",
                description="The member to kick",
                option_type=6,  # User type
                required=True
            ),
            create_option(
                name="reason",
                description="The reason for kicking the user",
                option_type=3,  # String type
                required=True
            ),
        ],
    )
    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(ban_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: str):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running  'kick' command with user {user.name}#{user.discriminator} ({user.id}) and reason: {reason}")
            return
        await user.kick(reason=reason)

        # Send a DM to the user
        await user.send(f'You have been Kicked from the server {ctx.guild.name}.')
        await user.send(f'Reason: {reason}')

        # Log the action
        mod_actions = await self.config.guild(ctx.guild).mod_actions()
        mod_actions.append({
            'moderator': ctx.author.id,
            'action': 'kick',
            'user': user.id,
            'reason': reason
        })
        await self.config.guild(ctx.guild).mod_actions.set(mod_actions)

        await ctx.send(f'{user.mention} has been kicked for: {reason}')

    async def handle_mute(self, ctx, user: discord.Member, time: int, reason: str):
        muted_role = await self.get_muted_role(ctx.guild)
        if muted_role is None:
            await self.create_muted_role(ctx.guild)
            muted_role = await self.get_muted_role(ctx.guild)

        if muted_role is None:
            await ctx.send("Error creating muted role. Please check the bot's permissions and try again.")
            return

        if time is not None:
            await self.config.guild(ctx.guild).actions.muting.set(True)
            await self.config.guild(ctx.guild).thresholds.muting_threshold.set(1)  # Adjust as needed
            await self.config.guild(ctx.guild).thresholds.muting_time.set(time)

        await user.add_roles(muted_role)

        if time is not None:
            await user.send(f'You have been muted in the server {ctx.guild.name} for {time} minutes.')
        else:
            await user.send(f'You have been muted indefinitely in the server {ctx.guild.name}.')
        await user.send(f'Reason: {reason}')

        mod_actions = await self.config.guild(ctx.guild).mod_actions()
        mod_actions.append({
            'moderator': ctx.author.id,
            'action': 'mute',
            'user': user.id,
            'reason': reason
        })
        await self.config.guild(ctx.guild).mod_actions.set(mod_actions)

        if time is not None:
            await ctx.send(f'{user.mention} has been muted for {time} minutes for: {reason}')
        else:
            await ctx.send(f'{user.mention} has been muted indefinitely for: {reason}')

    @commands.command(name="mute")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def mute_command(self, ctx, user: discord.Member, time: int = None, *, reason: str):
        await self.handle_mute(ctx, user, time, reason)

    @slash.slash( # type: ignore
        name="mute",
        description="Mute a member for a specified time and reason",
        options=[
            create_option(
                name="user",
                description="The member to mute",
                option_type=6,  # User type
                required=True
            ),
            create_option(
                name="reason",
                description="The reason for muting the user",
                option_type=3,  # String type
                required=True
            ),
            create_option(
                name="time",
                description="Duration to mute the user (in minutes, optional)",
                option_type=4,  # Integer
                required=False
            ),
        ],
    )
    async def mute_slash(self, ctx: SlashContext, user: discord.Member, reason: str, time: int = None):
        await self.handle_mute(ctx, user, time, reason)



    async def handle_ban(self, ctx, user: discord.Member, reason: str):
        await user.ban(reason=reason)
        await user.send(f'You have been banned from the server {ctx.guild.name}. Reason: {reason}')
        await ctx.send(f'{user.mention} has been banned for: {reason}')

    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_command(self, ctx, user: discord.Member, *, reason: str):
        await self.handle_ban(ctx, user, reason)

    @slash.slash( # type: ignore
        name="ban",
        description="Ban a member for a specified reason",
        options=[
            create_option(
                name="user",
                description="The member to ban",
                option_type=6,  # User type
                required=True
            ),
            create_option(
                name="reason",
                description="The reason for banning the user",
                option_type=3,  # String type
                required=True
            ),
        ],
    )
    async def ban_slash(self, ctx: SlashContext, user: discord.Member, reason: str):
        await self.handle_ban(ctx, user, reason)

    async def handle_unmute(self, ctx, user: discord.Member):
        muted_role = await self.get_muted_role(ctx.guild)
        if muted_role is None:
            await self.create_muted_role(ctx.guild)
            muted_role = await self.get_muted_role(ctx.guild)

        if muted_role is None:
            await ctx.send("Error creating muted role. Please check the bot's permissions and try again.")
            return

        if muted_role and muted_role in user.roles:
            await user.remove_roles(muted_role)
            await ctx.send(f'{user.mention} has been unmuted.')
        else:
            await ctx.send(f'{user.mention} is not muted.')

    @commands.command(name="unmute")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def unmute_command(self, ctx, user: discord.Member):
        await self.handle_unmute(ctx, user)

    @slash.slash( # type: ignore
        name="unmute",
        description="Unmute a member",
        options=[
            create_option(
                name="user",
                description="The member to unmute",
                option_type=6,  # User type
                required=True
            ),
        ],
    )
    async def unmute_slash(self, ctx: SlashContext, user: discord.Member):
        await self.handle_unmute(ctx, user)


    async def handle_unban(self, ctx, user: discord.User):
        await ctx.guild.unban(user)
        await ctx.send(f'{user.mention} has been unbanned.')

    @commands.command(name="unban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def unban_command(self, ctx, user: discord.User):
        await self.handle_unban(ctx, user)

    @slash.slash( # type: ignore
        name="unban",
        description="Unban a member",
        options=[
            create_option(
                name="user",
                description="The user to unban",
                option_type=3,  # String type (Discord User ID or mention)
                required=True
            ),
        ],
    )
    async def unban_slash(self, ctx: SlashContext, user: discord.User):
        await self.handle_unban(ctx, user)


    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(ban_members=True)
    async def clear_warnings(self, ctx, user: discord.Member):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running  'clear_warnings' command with user {user.name}#{user.discriminator} ({user.id})")
            return
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
            await self.debug_log(ctx.guild, "add", "Running 'view_warnings' command")
            return
        if not user:
            user = ctx.author

        # Check if the user is viewing their own warnings or is a moderator
        if user != ctx.author and not ctx.author.guild_permissions.ban_members:
            return await ctx.send("You can only view your own warnings.")

        warnings = await self.config.guild(ctx.guild).warnings()
        user_warnings = warnings.get(str(user.id), [])
        if user_warnings:
            warnings_embeds = []
            instructions = "React with ❌ to delete a warning (only available for moderators).\nReact with ✅ to close this message.\nReact with ✅ to close this message.\nUse ⬅️ ➡️ to navigate."

            # Adding instructions field
            instructions_embed = discord.Embed(
                title="Instructions",
                description=instructions,
                color=discord.Color.green()  # You can change the color as desired
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
            await message.add_reaction("❌")  # Cross emoji
            await message.add_reaction("✅")  # Checkmark emoji

            def check(reaction, user):
                return (
                    user == ctx.author
                    and reaction.message.id == message.id
                    and str(reaction.emoji) in {"❌", "✅", "⬅️", "➡️"}
                )

            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                except TimeoutError:
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
                        # Close the embed
                        await message.delete()
                        break
                    await message.remove_reaction(reaction, user)
        else:
            await ctx.send(f'{user.mention} has no warnings.')

    @commands.command(name="suggest")
    async def _suggest(self, ctx, *, suggestion):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'suggest' command")
            return
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
    @commands.has_permissions(manage_guild=True)
    @commands.group(name="settings")
    async def _settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_settings' command")
            return

    @_settings.group(name="mod")
    async def _mod_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_mod_settings' command")
            return

    @_mod_settings.group(name="mute")
    async def _mute_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_mute_settings' command")
            return

    @_mute_settings.command(name="set_duration")
    async def set_mute_duration(self, ctx, duration: int):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_mute_duration' sub-command of '_mute_settings' command")
            return

        await self.config.guild(ctx.guild).default_mute_duration.set(duration)
        await ctx.send(f'Default mute duration set to {duration} minutes.')

    @_settings.group(name="suggestion")
    async def _suggestion_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_suggestion_settings' command")
            return

    @_suggestion_settings.command(name="set_channel")
    async def set_suggestion_channel(self, ctx, channel: discord.TextChannel):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_suggestion_channel' command")
            return
        if ctx.author.guild_permissions.administrator:
            await self.config.guild(ctx.guild).suggestion_channel_id.set(channel.id)
            await ctx.send(f'Suggestion channel set to {channel.mention}.')
        else:
            await ctx.send('You must have administrator permissions to set the suggestion channel.')


    async def handle_clean(self, ctx, num_messages: int):
        if 1 <= num_messages <= 100:
            deleted_messages = await ctx.channel.purge(limit=num_messages + 1)
            await ctx.send(f"Deleted {len(deleted_messages)} message(s).", delete_after=5)
        else:
            await ctx.send("Please provide a number between 1 and 100.", delete_after=5)

    @commands.command(name="clean", aliases=["purge"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def clean_command(self, ctx, num_messages: int):
        await self.handle_clean(ctx, num_messages)

    @slash.slash( # type: ignore
        name="clean",
        description="Clean a specified number of messages from the channel",
        options=[
            create_option(
                name="num_messages",
                description="Number of messages to delete (1-100)",
                option_type=4,  # Integer
                required=True
            )
        ],
    )
    async def clean_slash(self, ctx: SlashContext, num_messages: int):
        await self.handle_clean(ctx, num_messages)


    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @commands.group(name="invite_filter")
    async def _invite_filter(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'invite_filter' command")
            return

    @_invite_filter.command(name="enable")
    async def enable_invite_filter(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'enable' sub-command of 'invite_filter' command")
            return

        await self.config.guild(ctx.guild).actions.invite_link_filter.set(True)
        await ctx.send('Invite link filter has been enabled.')

    @_invite_filter.command(name="disable")
    async def disable_invite_filter(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'disable' sub-command of 'invite_filter' command")
            return

        await self.config.guild(ctx.guild).actions.invite_link_filter.set(False)
        await ctx.send('Invite link filter has been disabled.')

    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
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
        """Background task to check Discord's status every 5 minutes."""
        try:
            while True:
                try:
                    response = requests.get("https://discordstatus.com/api/v2/status.json")
                    response.raise_for_status()  # Raises HTTPError for bad responses
                    data = response.json()
                except requests.exceptions.RequestException as e:
                    print(f"Error fetching Discord status: {e}")
                    await asyncio.sleep(300)  # Wait 5 minutes before trying again
                    continue  # Skip the rest of the loop and try again

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

                await asyncio.sleep(300)  # Wait 5 minutes before checking again
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
        """Set the channel for Discord status updates."""
        await self.config.guild(ctx.guild).status_channel_id.set(channel.id)
        await ctx.send(f"Discord status updates will be sent to {channel.mention}")
