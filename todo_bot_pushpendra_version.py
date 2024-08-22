import discord
from discord.ext import commands, tasks
import random
import json

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Revised Leveling System with Hardcore Progression
level_roles = {
    1: {"threshold": 0, "role_name": "Recruit"},
    2: {"threshold": 50, "role_name": "Contender"},
    3: {"threshold": 200, "role_name": "Survivor"},
    4: {"threshold": 600, "role_name": "Warrior"},
    5: {"threshold": 1500, "role_name": "Champion"},
    6: {"threshold": 4000, "role_name": "Eliminator"},
    7: {"threshold": 10000, "role_name": "Conqueror"},
    8: {"threshold": 25000, "role_name": "Apex Predator"},
    9: {"threshold": 50000, "role_name": "Legend"}, 
}

# Dynamic Task Difficulty Levels
difficulty_levels = {
    "Easy": {"xp_min": 50, "xp_max": 100},
    "Medium": {"xp_min": 100, "xp_max": 200},
    "Hard": {"xp_min": 200, "xp_max": 400},
    "Extreme": {"xp_min": 400, "xp_max": 800}
}

# Inactivity Penalty System
inactivity_penalty = 0.10  # 10% XP penalty for inactivity

# Example user data structure stored in JSON for persistence
user_data_file = "user_data.json"

# Helper function to load user data
def load_user_data():
    try:
        with open(user_data_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Helper function to save user data
def save_user_data():
    with open(user_data_file, "w") as file:
        json.dump(user_data, file, indent=4)

user_data = load_user_data()

def get_user_level(user_id):
    xp = user_data.get(user_id, {}).get('xp', 0)
    for level, info in sorted(level_roles.items(), reverse=True):
        if xp >= info["threshold"]:
            return level, info["role_name"]
    return 1, "Beginner"

def calculate_xp(task_difficulty):
    xp_range = difficulty_levels[task_difficulty]
    return random.randint(xp_range["xp_min"], xp_range["xp_max"])

def get_challenge_xp(level_diff):
    return max(10, 50 - level_diff * 5)

def apply_inactivity_penalty(user_id):
    if user_id in user_data:
        user_data[user_id]['xp'] *= (1 - inactivity_penalty)
        user_data[user_id]['inactivity_days'] = 0  # Reset inactivity days

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    check_inactivity.start()  # Start the inactivity check loop

@tasks.loop(hours=24)
async def check_inactivity():
    for user_id, data in user_data.items():
        data['inactivity_days'] = data.get('inactivity_days', 0) + 1
        if data['inactivity_days'] > 5:
            apply_inactivity_penalty(user_id)
    save_user_data()

@bot.command(name="task_complete")
async def task_complete(ctx, task_difficulty: str):
    user_id = str(ctx.author.id)
    task_difficulty = task_difficulty.capitalize()

    if task_difficulty not in difficulty_levels:
        await ctx.send(f"Invalid task difficulty. Choose from: {', '.join(difficulty_levels.keys())}.")
        return
    
    xp_gain = calculate_xp(task_difficulty)
    
    if user_id in user_data:
        user_data[user_id]['xp'] += xp_gain
        user_data[user_id]['inactivity_days'] = 0
    else:
        user_data[user_id] = {'xp': xp_gain, 'inactivity_days': 0, 'tasks_completed': 0}
    
    user_data[user_id]['tasks_completed'] += 1
    level, role_name = get_user_level(user_id)
    
    # Update user's role in Discord
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        await ctx.author.add_roles(role)
    
    await ctx.send(f"{ctx.author.mention} completed a {task_difficulty} task! Gained {xp_gain} XP and is now a {role_name}.")
    save_user_data()

@bot.command(name="challenge")
async def challenge(ctx, opponent: discord.Member):
    challenger_id = str(ctx.author.id)
    opponent_id = str(opponent.id)

    if challenger_id == opponent_id:
        await ctx.send("You can't challenge yourself!")
        return
    
    challenger_level, _ = get_user_level(challenger_id)
    opponent_level, _ = get_user_level(opponent_id)
    
    level_diff = abs(challenger_level - opponent_level)
    xp_gain = get_challenge_xp(level_diff)
    
    if challenger_level >= opponent_level:
        user_data[challenger_id]['xp'] += xp_gain
    else:
        user_data[opponent_id]['xp'] += xp_gain
    
    await ctx.send(f"{ctx.author.mention} challenged {opponent.mention}! {xp_gain} XP awarded to the winner!")
    save_user_data()

@bot.command(name="profile")
async def profile(ctx):
    user_id = str(ctx.author.id)
    xp = user_data.get(user_id, {}).get('xp', 0)
    tasks_completed = user_data.get(user_id, {}).get('tasks_completed', 0)
    level, role_name = get_user_level(user_id)
    await ctx.send(f"{ctx.author.mention}'s Profile:\nLevel {level} - {role_name}\nXP: {xp}\nTasks Completed: {tasks_completed}")

@bot.command(name="assign_task")
@commands.has_role("Admin")  # Only admins can assign tasks
async def assign_task(ctx, member: discord.Member, task_difficulty: str):
    task_difficulty = task_difficulty.capitalize()
    
    if task_difficulty not in difficulty_levels:
        await ctx.send(f"Invalid task difficulty. Choose from: {', '.join(difficulty_levels.keys())}.")
        return
    
    user_id = str(member.id)
    
    if user_id in user_data:
        xp_gain = calculate_xp(task_difficulty)
        user_data[user_id]['xp'] += xp_gain
        user_data[user_id]['inactivity_days'] = 0
        user_data[user_id]['tasks_completed'] += 1
    else:
        user_data[user_id] = {'xp': xp_gain, 'inactivity_days': 0, 'tasks_completed': 1}
    
    level, role_name = get_user_level(user_id)
    
    # Update user's role in Discord
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
    
    await ctx.send(f"Assigned a {task_difficulty} task to {member.mention}! They gained {xp_gain} XP and are now a {role_name}.")
    save_user_data()

@bot.command(name="rank_shield")
async def rank_shield(ctx):
    user_id = str(ctx.author.id)
    xp = user_data.get(user_id, {}).get('xp', 0)
    level, role_name = get_user_level(user_id)

    shield_threshold = level_roles[level]["threshold"] * 0.9
    
    if xp > shield_threshold:
        await ctx.send(f"{ctx.author.mention}, your rank is currently protected! You have {xp} XP, and the protection threshold is {shield_threshold} XP.")
    else:
        await ctx.send(f"{ctx.author.mention}, your rank is not protected. Consider completing more tasks to ensure your rank.")
    
bot.run('YOUR_BOT_TOKEN_HERE')
