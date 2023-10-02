import discord
from redbot.core import commands, Config, checks
import redbot.core.data_manager
import random
import os
import datetime
import logging
import traceback

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
            'enable_debug': False,  # Added enable_debug option
            'suggestion_channel_id': None 
        }
        self.config.register_guild(**default_guild)

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
        debug_file = open(debug_file_path, 'a') 

        debug_file.write(f"{datetime.datetime.now()} - Command '{command}': {message}\n")
        debug_file.close()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
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
        elif isinstance(error, commands.UserInputError):
            await ctx.send(f"Invalid input. Please check the command usage with `!help {ctx.command}`.")
        elif isinstance(error, commands.CommandError):
            await ctx.send(f"An error occurred while processing the command: {error}")
        else:
            # Handle any other specific errors here, or provide a generic error message
            await ctx.send("An error occurred while processing the command. Please try again later.")

    @commands.is_owner()
    @commands.command(name="read_debug_log")
    async def read_debug_log(self, ctx):
        current_directory = redbot.core.data_manager.cog_data_path(cog_instance=self)
        debug_file_path = f"{current_directory}/{ctx.guild.id}-debug.log"
    
        try:
            with open(debug_file_path, 'r') as debug_file:
                log_contents = debug_file.read()
                await ctx.send(f"Debug Log Contents for {ctx.guild.name}:\n```{log_contents}```")
        except FileNotFoundError:
            await ctx.send("debug.log file not found.")

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
            await self.debug_log(ctx.guild, "add", "Running '_settings' sub-command of '_banned_words' command")
            return

    @_bw_settings.group(name="warn")
    async def _warn_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_warn_settings' sub-command of '_settings' command")
            return

    @_bw_settings.group(name="mute")
    async def _mute_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_mute_settings' sub-command of '_settings' command")
            return

    @_bw_settings.group(name="ban")
    async def _ban_settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_ban_settings' sub-command of '_settings' command")
            return

    @_bw_settings.command(name="view")
    async def view_settings(self, ctx):
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

    # Set commands
    @_warn_settings.command(name="set")
    async def set_warn(self, ctx, threshold: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_warn' sub-command of '_warn_settings' command")
            return

        # Set warning threshold
        await self.config.guild(ctx.guild).actions.warning.set(True)
        await self.config.guild(ctx.guild).thresholds.warning_threshold.set(threshold)
        await ctx.send(f'Set warning threshold to {threshold}.')

    @_mute_settings.command(name="set")
    async def set_mute(self, ctx, threshold: int, time: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_mute' sub-command of '_mute_settings' command")
            return

        # Set muting actions and thresholds
        await self.config.guild(ctx.guild).actions.muting.set(True)
        await self.config.guild(ctx.guild).thresholds.muting_threshold.set(threshold)
        await self.config.guild(ctx.guild).thresholds.muting_time.set(time)

        await ctx.send(f'Set mute threshold to {threshold} warnings and mute duration to {time} minutes.')

    @_ban_settings.command(name="set")
    async def set_ban(self, ctx, threshold: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_ban' sub-command of '_ban_settings' command")
            return

        # Set banning threshold
        await self.config.guild(ctx.guild).actions.banning.set(True)
        await self.config.guild(ctx.guild).thresholds.banning_threshold.set(threshold)
        await ctx.send(f'Set banning threshold to {threshold}.')

    # Enable/Disable commands
    @_warn_settings.command(name="enable")
    async def warn_enable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'warn_enable' sub-command of '_warn_settings' command")
            return

        # Enable warning threshold
        await self.config.guild(ctx.guild).actions.warning.set(True)
        await ctx.send('Warning threshold has been enabled.')

    @_warn_settings.command(name="disable")
    async def warn_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'warn_disable' sub-command of '_warn_settings' command")
            return

        # Disable warning threshold
        await self.config.guild(ctx.guild).actions.warning.set(False)
        await ctx.send('Warning threshold has been disabled.')

    @_mute_settings.command(name="enable")
    async def mute_enable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'mute_enable' sub-command of '_mute_settings' command")
            return

        # Enable muting threshold
        await self.config.guild(ctx.guild).actions.muting.set(True)
        await ctx.send('Muting threshold has been enabled.')

    @_mute_settings.command(name="disable")
    async def mute_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'mute_disable' sub-command of '_mute_settings' command")
            return

        # Disable muting threshold
        await self.config.guild(ctx.guild).actions.muting.set(False)
        await ctx.send('Muting threshold has been disabled.')

    @_ban_settings.command(name="enable")
    async def ban_enable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'ban_enable' sub-command of '_ban_settings' command")
            return

        # Enable banning threshold
        await self.config.guild(ctx.guild).actions.banning.set(True)
        await ctx.send('Banning threshold has been enabled.')

    @_ban_settings.command(name="disable")
    async def ban_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'ban_disable' sub-command of '_ban_settings' command")
            return

        # Disable banning threshold
        await self.config.guild(ctx.guild).actions.banning.set(False)
        await ctx.send('Banning threshold has been disabled.')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.author.bot:
            return
        #Add debug print statement
        if await self.config.guild(message.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'on_message' listener")
            return

        content = message.content.lower()

        if content.startswith("!banned_words add") or content.startswith("!banned_words remove"):
            return

        banned_words = await self.config.guild(message.guild).banned_words()

        if any(word in content for word in banned_words):
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
        if await self.config.guild(message.guild).actions.invite_link_filter():
            if await self.contains_invite_link(message.content):
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
    
                await message.delete()
                await message.author.send(f"Your message has been removed from {message.guild.name} for sending an invite link.")
                await message.channel.send(f'{message.author.mention}, your message has been removed for sending an invite link.')
    

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(ban_members=True)
    async def warn(self, ctx, user: discord.Member, *, reason: str):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running  'warn' command with user {user.name}#{user.discriminator} ({user.id}) and reason: {reason}")
            return
        warnings = await self.config.guild(ctx.guild).warnings()
        user_warnings = warnings.get(str(user.id), [])
        user_warnings.append(reason)
        warnings[str(user.id)] = user_warnings
        await self.config.guild(ctx.guild).warnings.set(warnings)

        # Send a DM to the user
        await user.send(f'You have received a warning in the server {ctx.guild.name}.')
        await user.send(f'Reason: {reason}')

        # Log the action
        mod_actions = await self.config.guild(ctx.guild).mod_actions()
        mod_actions.append({
            'moderator': ctx.author.id,
            'action': 'warn',
            'user': user.id,
            'reason': reason
        })
        await self.config.guild(ctx.guild).mod_actions.set(mod_actions)

        await ctx.send(f'{user.mention} has been warned for: {reason}')

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

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def mute(self, ctx, user: discord.Member, time: int = None, *, reason: str):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", f"Running 'mute' command with user {user.name}#{user.discriminator} ({user.id}) and reason: {reason}")
            return

        # Check if muted role exists, create one if not
        muted_role = await self.get_muted_role(ctx.guild)
        if muted_role is None:
            await self.create_muted_role(ctx.guild)
            muted_role = await self.get_muted_role(ctx.guild)

        # If after creating it's still None, something went wrong, notify the user
        if muted_role is None:
            await ctx.send("Error creating muted role. Please check the bot's permissions and try again.")
            return

        if time is not None:
            # Set muting actions, thresholds, and time
            await self.config.guild(ctx.guild).actions.muting.set(True)
            await self.config.guild(ctx.guild).thresholds.muting_threshold.set(1)  # Change as needed
            await self.config.guild(ctx.guild).thresholds.muting_time.set(time)

        await user.add_roles(muted_role)

        # Send a DM to the user
        if time is not None:
            await user.send(f'You have been muted in the server {ctx.guild.name} for {time} minutes.')
        else:
            await user.send(f'You have been muted indefinitely in the server {ctx.guild.name}.')
        await user.send(f'Reason: {reason}')

        # Log the action
        mod_actions = await self.config.guild(ctx.guild).mod_actions()
        mod_actions.append({
            'moderator': ctx.author.id,
            'action': 'mute',
            'user': user.id,
            'reason': reason
        })
        await self.config.guild(ctx.guild).mod_actions.set(mod_actions)

        # Mention the user and notify the channel
        if time is not None:
            await ctx.send(f'{user.mention} has been muted for {time} minutes for: {reason}')
        else:
            await ctx.send(f'{user.mention} has been muted indefinitely for: {reason}')

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(ban_members=True)
    async def ban(self, ctx, user: discord.Member, *, reason: str):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running  'ban' command with user {user.name}#{user.discriminator} ({user.id}) and reason: {reason}")
            return
        await user.ban(reason=reason)

        # Send a DM to the user
        await user.send(f'You have been banned from the server {ctx.guild.name}.')
        await user.send(f'Reason: {reason}')

        # Log the action
        mod_actions = await self.config.guild(ctx.guild).mod_actions()
        mod_actions.append({
            'moderator': ctx.author.id,
            'action': 'ban',
            'user': user.id,
            'reason': reason
        })
        await self.config.guild(ctx.guild).mod_actions.set(mod_actions)

        await ctx.send(f'{user.mention} has been banned for: {reason}')
    
    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(manage_roles=True)
    async def unmute(self, ctx, user: discord.Member):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", f"Running 'unmute' command with user {user.name}#{user.discriminator} ({user.id})")
            return
    
        # Check if muted role exists, create one if not
        muted_role = await self.get_muted_role(ctx.guild)
        if muted_role is None:
            await self.create_muted_role(ctx.guild)
            muted_role = await self.get_muted_role(ctx.guild)
    
        # If after creating it's still None, something went wrong, notify the user
        if muted_role is None:
            await ctx.send("Error creating muted role. Please check the bot's permissions and try again.")
            return
    
        if muted_role and muted_role in user.roles:
            await user.remove_roles(muted_role)
            await ctx.send(f'{user.mention} has been unmuted.')
        else:
            await ctx.send(f'{user.mention} is not muted.')

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running  'unban' command with user {user.name}#{user.discriminator} ({user.id})")
            return
        await ctx.guild.unban(user)
        await ctx.send(f'{user.mention} has been unbanned.')

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
                    elif str(reaction.emoji) == "❌":
                        # Delete the warning if user is a moderator
                        if ctx.author.guild_permissions.ban_members:
                            user_warnings.pop(current_page-1)  # Subtract 1 to account for the instructions page
                            warnings[str(user.id)] = user_warnings
                            await self.config.guild(ctx.guild).warnings.set(warnings)
                            if len(user_warnings) > 0:
                                current_page = min(current_page, len(user_warnings))
                                await message.edit(embed=warnings_embeds[current_page])
                            else:
                                await message.delete()
                                break
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

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def clean(self, ctx, num_messages: int):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", f"Running 'clean' command to delete {num_messages} messages")
            return

        # Ensure the number of messages to delete is within a reasonable range
        if 1 <= num_messages <= 100:
            # Delete the specified number of messages
            deleted_messages = await ctx.channel.purge(limit=num_messages+1)
            await ctx.send(f"Deleted {len(deleted_messages)} message(s).", delete_after=5)
        else:
            await ctx.send("Please provide a number between 1 and 100.", delete_after=5)

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