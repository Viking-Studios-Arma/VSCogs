import discord
from discord.ext import commands
from redbot.core import commands
import json
import os
import asyncio
import re
import sys
import getpass

COG_DIR = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH = os.path.join(COG_DIR, "config")

class VSMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data_path = CONFIG_PATH
        self.warnings = {}
        self.banned_words = {}
        self.mutes = {}
        self.bans = {}
        self.kicks = {}
        self.offenses = {}
        self.thresholds = {}
        current_user = getpass.getuser()
        self.log_file_path = f'/home/{current_user}/cogs/VSMod/logs/output.log'
        sys.stdout = open(self.log_file_path, 'w')
        self.load_data()

    def load_data(self):
        for guild in self.bot.guilds:
            guild_id = guild.id
            self.warnings[guild_id] = self.load_data_for_guild(guild_id, "warnings")
            self.mutes[guild_id] = self.load_data_for_guild(guild_id, "mutes")
            self.bans[guild_id] = self.load_data_for_guild(guild_id, "bans")
            self.kicks[guild_id] = self.load_data_for_guild(guild_id, "kicks")
            self.banned_words[guild_id] = self.load_data_for_guild(guild_id, "banned_words")
            self.thresholds[guild_id] = self.load_data_for_guild(guild_id, "thresholds")
    def load_data_for_guild(self, guild_id, data_name):
        file_path = os.path.join(CONFIG_PATH, f'guild_{guild_id}_{data_name}.json')
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                print(f"Loaded data for guild {guild_id}, data_name {data_name}: {data}")
                return data
        except FileNotFoundError:
            print(f"Data file not found for guild {guild_id}, data_name {data_name}")
            # Create an empty data file if it doesn't exist
            with open(file_path, 'w') as file:
                json.dump({}, file)
            return {}

    def save_data(self, guild_id, data_name):
        file_path = os.path.join(self.data_path, f'guild_{guild_id}_{data_name}.json')
        data = getattr(self, data_name).get(guild_id, {})

        with open(file_path, 'w') as file:
            json.dump(data, file)

    def load_from_file(self, data_name):
        data = {}
        for guild in self.bot.guilds:
            guild_id = guild.id
            file_path = os.path.join(self.data_path, f'guild_{guild_id}_{data_name}.json')

            try:
                with open(file_path, 'r') as file:
                    data[guild_id] = json.load(file)
            except FileNotFoundError:
                data[guild_id] = {}

        return data
        
    def save_all_data(self):
        data_types = ["mutes", "bans", "warnings", "kicks", "banned_words", "thresholds"]
        for data_type in data_types:
            for guild_id in self.bot.guilds:
                self.save_data(guild_id, data_type)

    def save_to_file(self, data_name, data):
        file_path = os.path.join(self.data_path, f'{data_name}.json')
        with open(file_path, 'w') as file:
            json.dump(data, file)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.author == self.bot.user:
            return
    
        guild_id = message.guild.id
        user_id = message.author.id
    
        offenses = self.offenses.get(guild_id, {}).get(user_id, 0)
    
        content = message.content.lower()
        for word in self.banned_words.get(guild_id, []):
            pattern = re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE)
            if pattern.search(content):
                print(f"Banned word detected: {word}")
                await self.track_offenses(message)
                action_message = await self.apply_actions(message, offenses)
    
                if action_message:
                    await message.delete()
                    await message.channel.send(f"{message.author.mention}, your message has been deleted for containing a banned word. "
                                               f"Please refrain from using such language.")
                break

    async def apply_actions(self, message, offenses):
        guild_id = message.guild.id

        warning_threshold = self.thresholds.get(guild_id, {}).get('warning', 3)
        mute_threshold = self.thresholds.get(guild_id, {}).get('mute', 5)
        ban_threshold = self.thresholds.get(guild_id, {}).get('ban', 10)

        await message.delete()
        await message.channel.send(f"{message.author.mention}, your message has been deleted for containing a banned word. Please refrain from using such language.")

        if offenses >= ban_threshold:
            member = message.author
            await message.guild.ban(member, reason="Repeated offenses", delete_message_days=0)
            return f"{member.mention} has been banned for repeated offenses."

        if offenses >= mute_threshold:
            member = message.author
            muted_role = discord.utils.get(message.guild.roles, name='Muted')

            if not muted_role:
                muted_role = await message.guild.create_role(name='Muted')
                overwrite = discord.PermissionOverwrite()
                overwrite.send_messages = False

                for channel in message.guild.channels:
                    await channel.set_permissions(muted_role, overwrite=overwrite)

            await member.add_roles(muted_role)
            await asyncio.sleep(parse_time(mute_duration))
            await member.remove_roles(muted_role)
            return f"{member.mention} has been muted for repeated offenses."

        if offenses >= warning_threshold:
            user_id = message.author.id
            guild_id = message.guild.id

            if guild_id not in self.warnings:
                self.warnings[guild_id] = {}

            if user_id not in self.warnings[guild_id]:
                self.warnings[guild_id][user_id] = []

            self.warnings[guild_id][user_id].append("Warning for using banned words")
            self.save_to_file(guild_id, "warnings")

            user = message.author
            await user.send(f"You have received a warning for using banned words in the server. Please refrain from doing so in the future.")

        return None

    async def track_offenses(self, message):
        user_id = message.author.id
        guild_id = message.guild.id

        if guild_id not in self.offenses:
            self.offenses[guild_id] = {}

        if user_id not in self.offenses[guild_id]:
            self.offenses[guild_id][user_id] = 0

        self.offenses[guild_id][user_id] += 1
        
        self.save_offenses(guild_id)
    
    async def cog_check(self, ctx):
        if ctx.guild:
            return ctx.author.guild_permissions.administrator
        return False

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def banned_words(self, ctx, action, *words):
        guild_id = ctx.guild.id
        if guild_id not in self.banned_words:
            self.banned_words[guild_id] = []

        if action not in ['add', 'remove']:
            await ctx.send("Invalid action. Use 'add' or 'remove'.")
            return

        for word in words:
            word = word.lower()  # Convert to lowercase for case-insensitive matching

            if action == 'add':
                if word not in self.banned_words[guild_id]:
                    self.banned_words[guild_id].append(word)
            elif action == 'remove':
                if word in self.banned_words[guild_id]:
                    self.banned_words[guild_id].remove(word)

        self.save_data(guild_id, "banned_words")
        await ctx.send(f"Banned words updated: {', '.join(words)}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def banned_word_settings(self, ctx, action, threshold):
        guild_id = ctx.guild.id
        if guild_id not in self.thresholds:
            self.thresholds[guild_id] = {}

        if action not in ['warning', 'mute', 'ban']:
            await ctx.send("Invalid action. Use 'warning', 'mute', or 'ban'.")
            return

        self.thresholds[guild_id][action] = int(threshold)
        self.save_data(guild_id, "thresholds")
        await ctx.send(f"{action} threshold set to {threshold}.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def list_banned_words(self, ctx):
        guild_id = ctx.guild.id
        banned_words = self.banned_words.get(guild_id, {})

        if banned_words:
            embed = discord.Embed(title="List of Banned Words", color=discord.Color.red())
            for word in banned_words:
                embed.add_field(name=word, value="Banned", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("There are no banned words in this server.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, duration: str = None):
        muted_role = discord.utils.get(ctx.guild.roles, name='Muted')

        if not muted_role:
            muted_role = await ctx.guild.create_role(name='Muted')

            overwrite = discord.PermissionOverwrite()
            overwrite.send_messages = False
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, overwrite=overwrite)

        await member.add_roles(muted_role)
        await ctx.send(f"{member.mention} has been muted.")

        if duration:
            self.mutes[ctx.guild.id][member.id] = parse_time(duration)
            self.save_data(ctx.guild.id, "mutes")
            await asyncio.sleep(parse_time(duration))
            await member.remove_roles(muted_role)
            del self.mutes[ctx.guild.id][member.id]
            self.save_data(ctx.guild.id, "mutes")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, duration: str = None):
        await member.ban()
        await ctx.send(f"{member.mention} has been banned.")

        if duration:
            self.bans[ctx.guild.id][member.id] = parse_time(duration)
            self.save_data(ctx.guild.id, "bans")
            await asyncio.sleep(parse_time(duration))
            await member.unban()
            del self.bans[ctx.guild.id][member.id]
            self.save_data(ctx.guild.id, "bans")

    @commands.command()
    async def user_info(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        roles = [role.name for role in member.roles[1:]]  # Skip @everyone role

        embed = discord.Embed(title=f"User Information for {member}", color=discord.Color.green())
        embed.set_thumbnail(url=member.avatar_url)
        embed.add_field(name="ID", value=member.id, inline=False)
        embed.add_field(name="Nickname", value=member.display_name, inline=False)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def set_command_roles(self, ctx, command_name, *roles):
        guild_id = ctx.guild.id
        if guild_id not in self.command_roles:
            self.command_roles[guild_id] = {}

        self.command_roles[guild_id][command_name] = roles
        self.save_command_roles(guild_id)
        await ctx.send(f"Roles for {command_name} command set to: {', '.join(roles)}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason):
        guild_id = ctx.guild.id
        user_id = member.id

        if guild_id not in self.warnings:
            self.warnings[guild_id] = {}

        if user_id not in self.warnings[guild_id]:
            self.warnings[guild_id][user_id] = []

        self.warnings[guild_id][user_id].append(reason)
        self.save_data(guild_id, "warnings")
        await ctx.send(f"{member.mention} has been warned for: {reason}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason):
        guild_id = ctx.guild.id
        user_id = member.id

        if guild_id not in self.kicks:
            self.kicks[guild_id] = {}

        if user_id not in self.kicks[guild_id]:
            self.kicks[guild_id][user_id] = []

        self.kicks[guild_id][user_id].append(reason)
        self.save_data(guild_id, "kicks")
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} has been kicked for: {reason}")

    @commands.command()
    async def view_warnings(self, ctx, member: discord.Member):
        guild_id = ctx.guild.id
        user_id = member.id

        warnings = self.warnings.get(guild_id, {}).get(user_id)
        print(self.warnings)
        
        if warnings:
            embed = discord.Embed(title=f"Warnings for {member}", color=discord.Color.gold())
            for index, warning in enumerate(warnings):
                embed.add_field(name=f"Warning {index + 1}", value=warning, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{member} has no warnings.")
        


    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        guild_id = ctx.guild.id
        user_id = member.id

        if guild_id in self.warnings and user_id in self.warnings[guild_id]:
            del self.warnings[guild_id][user_id]
            self.save_data(guild_id, "warnings")
            await ctx.send(f"Warnings for {member} have been cleared.")
        else:
            await ctx.send(f"{member} has no warnings.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_warning_expiry(self, ctx, duration: str = "6m"):
        guild_id = ctx.guild.id

        # Parse the duration
        expiry_time = parse_time(duration)

        if guild_id not in self.warning_expiry:
            self.warning_expiry[guild_id] = {}  # Ensure there's a dictionary for this guild

        # Save the expiry time to the config
        self.warning_expiry[guild_id] = expiry_time
        self.save_data(guild_id, "warning_expiry")

        await ctx.send(f"Warning expiry time set to {expiry_time} seconds.")

    def parse_time(duration):
        units = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
        }

        unit = duration[-1]
        if unit in units:
            return int(duration[:-1]) * units[unit]
        else:
            return int(duration)

def setup(bot):
    bot.add_cog(VSMod(bot))