import discord
from redbot.core import commands, Config, checks
import redbot.core.data_manager
import random
import os
import datetime
import logging

class VSMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        current_directory = redbot.core.data_manager.cog_data_path(cog_instance=self)
        debug_file_path = f"{current_directory}/debug.log"
        self.debug_file = None
        self.identifier = self.bot.user.id
        self.config = Config.get_conf(self, identifier=self.identifier, force_registration=True)
        default_guild = {
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

        self.muted_role = None
        self.muted_role_id = None

    async def cog_before_invoke(self, ctx):
        if not self.muted_role_id:
            await self.create_muted_role()

    async def create_muted_role(self):
        if guild := discord.utils.get(self.bot.guilds, id=self.muted_role_id):
            self.muted_role = discord.utils.get(guild.roles, name="Muted (By VSMod)")
            if not self.muted_role:
                try:
                    self.muted_role = await guild.create_role(name="Muted (By VSMod)")
                    for channel in guild.channels:
                        await channel.set_permissions(self.muted_role, send_messages=False, connect=False)
                except Exception as e:
                    await self.debug_log(f"Error creating muted role: {e}")
                else:
                    self.muted_role_id = self.muted_role.id
                    await self.config.muted_role_id.set(self.muted_role_id)

    async def debug_log(self, guild, command, message):
        current_directory = redbot.core.data_manager.cog_data_path(cog_instance=self)
        debug_file_path = f"{current_directory}/{guild.id}-debug.log"
        debug_file = open(debug_file_path, 'a') 

        debug_file.write(f"{datetime.datetime.now()} - Command '{command}': {message}\n")
        debug_file.close()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await self.debug_log(f"Error: {error} occurred in command '{ctx.command.name}'")
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

    async def filter_invite_links(self, message):
        if message.guild is None or message.author.bot:
            return
        if await self.config.guild(message.guild).actions.invite_link_filter() and "discord.gg/" in message.content:
            await message.delete()
            await message.author.send(f"You cannot send Discord invite links in this server {message.guild.name}.")
            await message.channel.send(f'{message.author.mention}, your message has been removed for containing an invite link.')

    @commands.is_owner()
    @commands.command(name="read_debug_log")
    async def read_debug_log(self, ctx):
        current_directory = redbot.core.data_manager.cog_data_path(cog_instance=self)
        debug_file_path = f"{current_directory}/debug.log"

        try:
            with open(debug_file_path, 'r') as debug_file:
                log_contents = debug_file.read()
                await ctx.send(f"Debug Log Contents:\n```{log_contents}```")
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

    @_banned_words.group(name="settings")
    async def _settings(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running '_settings' sub-command of '_banned_words' command")
            return
    
    @_settings.command()
    async def set_warn(self, ctx, threshold: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'warn' sub-command of '_settings' command")
            return
        await self.config.guild(ctx.guild).actions.warning.set(True)
        await self.config.guild(ctx.guild).thresholds.warning_threshold.set(threshold)
        await ctx.send(f'Set warning threshold to {threshold}.')
    
    @_settings.command(name="warn_disable")
    async def warn_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'warn_disable' sub-command of '_settings' command")
            return
        await self.config.guild(ctx.guild).actions.warning.set(False)
        await ctx.send('Warning threshold has been disabled.')
    
    @_settings.command(name="set_mute")
    async def set_mute(self, ctx, threshold: int, time: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_mute' sub-command of '_settings' command")
            return

        # Set muting actions and thresholds
        await self.config.guild(ctx.guild).actions.muting.set(True)
        await self.config.guild(ctx.guild).thresholds.muting_threshold.set(threshold)
        await self.config.guild(ctx.guild).thresholds.muting_time.set(time)

        await ctx.send(f'Set mute threshold to {threshold} warnings and mute duration to {time} minutes.')

    @_settings.command(name="mute_disable")
    async def mute_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'mute_disable' sub-command of '_settings' command")
            return
        await self.config.guild(ctx.guild).actions.muting.set(False)
        await ctx.send('Muting threshold has been disabled.')
    
    @_settings.command()
    async def set_ban(self, ctx, threshold: int):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'ban' sub-command of '_settings' command")
            return
        await self.config.guild(ctx.guild).actions.banning.set(True)
        await self.config.guild(ctx.guild).thresholds.banning_threshold.set(threshold)
        await ctx.send(f'Set banning threshold to {threshold}.')
    
    @_settings.command(name="ban_disable")
    async def ban_disable(self, ctx):
        # Add debug statement
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'ban_disable' sub-command of '_settings' command")
            return
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

            if actions['muting'] and self.muted_role_id:
                if muted_role := discord.utils.get(
                    message.guild.roles, id=self.muted_role_id
                ):
                    warnings = await self.config.guild(message.guild).warnings()
                    user_warnings = warnings.get(str(message.author.id), [])
                    user_warnings.append("Used banned words")
                    warnings[str(message.author.id)] = user_warnings
                    await self.config.guild(message.guild).warnings.set(warnings)

                    muting_threshold = thresholds['muting_threshold']

                    if len(user_warnings) >= muting_threshold:
                        # Send a DM to the user
                        await message.author.send(f'You have been muted in the server {message.guild.name} for using banned words.')
                        await message.author.send('Reason: Used banned words')

                        await message.author.add_roles(muted_role)

            # Delete the message and notify the user
            await message.delete()
            await message.author.send(f"Your message has been removed from {message.guild.name} for containing a banned word.")
            await message.channel.send(f'{message.author.mention}, your message has been removed for containing a banned word.')
        #Invite link Filter
        await self.filter_invite_links(message)

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
            await self.debug_log(ctx.guild, "add", "Running  'mute' command with user {user.name}#{user.discriminator} ({user.id}) and reason: {reason}")
            return

        if muted_role := discord.utils.get(ctx.guild.roles, id=self.muted_role_id):
            if time is not None:
                # Set muting actions, thresholds, and time
                await self.config.guild(ctx.guild).actions.muting.set(True)
                await self.config.guild(ctx.guild).thresholds.muting_threshold.set(1)  # Change as needed
                await self.config.guild(ctx.guild).thresholds.muting_time.set(time)

            await user.add_roles(muted_role)

            # Send a DM to the user
            await user.send(f'You have been muted in the server {ctx.guild.name}.')
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

            await ctx.send(f'{user.mention} has been muted for: {reason}')
        else:
            await ctx.send("Muted role not found. Please set up the muted role first.")

    async def unmute_after_time(self, guild, user, time):
        await asyncio.sleep(time * 60)  # Convert minutes to seconds
        muted_role = discord.utils.get(guild.roles, id=self.muted_role_id)
        if muted_role and muted_role in user.roles:
            await user.remove_roles(muted_role)
    
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
            await self.debug_log(ctx.guild, "add", "Running  'unmute' command with user {user.name}#{user.discriminator} ({user.id})")
            return
        muted_role = discord.utils.get(ctx.guild.roles, id=self.muted_role_id)
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

    @commands.group(name="mod_settings")
    async def _mod_settings(self, ctx):
        pass

    @commands.group(name="suggestion_settings")
    async def _suggestion_settings(self, ctx):
        pass

    @_mod_settings.command(name="set_mute_duration")
    async def set_mute_duration(self, ctx, duration: int):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_mute_duration' sub-command of '_settings' command")
            return

        await self.config.guild(ctx.guild).default_mute_duration.set(duration)
        await ctx.send(f'Default mute duration set to {duration} minutes.')

    @_suggestion_settings.command(name="set_suggestion_channel")
    async def set_suggestion_channel(self, ctx, channel: discord.TextChannel):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'set_suggestion_channel' command")
            return
        if ctx.author.guild_permissions.administrator:
            await self.config.guild(ctx.guild).suggestion_channel_id.set(channel.id)
            await ctx.send(f'Suggestion channel set to {channel.mention}.')
        else:
            await ctx.send('You must have administrator permissions to set the suggestion channel.')

    @commands.is_owner()
    @commands.command()
    async def purge_banned_words(self, ctx):
        if await self.config.guild(ctx.guild).enable_debug():
            await self.debug_log(ctx.guild, "add", "Running 'purge_banned_words' command")
            return
        await self.config.guild(ctx.guild).banned_words.set([])
        await ctx.send("Banned words list has been purged.")
    
    @commands.guild_only()
    @commands.bot_has_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @commands.group(name="enable_debug")
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