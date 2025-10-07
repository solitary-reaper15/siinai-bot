import os
import ssl
from dotenv import load_dotenv
import certifi

# Keep-alive for web services (ADD THIS AT THE TOP)
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Fix SSL certificate issues (macOS specific)
os.environ["SSL_CERT_FILE"] = certifi.where()
ssl._create_default_https_context = ssl.create_default_context

# Load environment variables
load_dotenv()

import discord
from discord.ext import commands

# Get token with error handling
token = os.getenv('DISCORD_TOKEN')
if not token:
    print("❌ ERROR: No bot token found!")
    print("Please create a .env file with DISCORD_TOKEN=your_token")
    exit(1)

print(f"✅ Token loaded successfully")

# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Your server configuration
GUILD_ID = 1421159009796231231
START_CHANNEL_ID = 1425083905853358163

# Role IDs - UPDATE THESE WITH YOUR ACTUAL ROLE IDs
ROLE_MEMBER = 1425066557582872599
DOMAINS = {
    "Social Science, Humanities, Arts": 1425070996313997403,
    "Management": 1425071371003625492,
    "CS/Math": 1425071277663588382,
    "Natural + Physical Sciences": 1425071159422091264
}
RESEARCHER_TYPES = {
    "Dedicated": 1425066979311747153,
    "Intermediate": 1425067233692090409,
    "Casual": 1425067365783179294
}

# In-memory tracking of users' progress
user_progress = {}

# Add error handling (ADD THIS NEW CODE)
@bot.event
async def on_error(event, *args, **kwargs):
    print(f"❌ Error in {event}: {args} {kwargs}")

@bot.event
async def on_command_error(ctx, error):
    print(f"❌ Command error: {error}")
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"An error occurred: {str(error)}")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    print(f"✅ Bot is in {len(bot.guilds)} guild(s)")
    
    # Verify bot has necessary permissions (ADD THIS NEW CODE)
    for guild in bot.guilds:
        print(f"Checking permissions in: {guild.name}")
        bot_member = guild.get_member(bot.user.id)
        if bot_member:
            permissions = bot_member.guild_permissions
            print(f"Manage Roles: {permissions.manage_roles}")
            print(f"Send Messages: {permissions.send_messages}")
            print(f"Read Messages: {permissions.read_messages}")

# Add test command (ADD THIS NEW CODE)
@bot.command()
async def test(ctx):
    """Test if bot is working"""
    await ctx.send("✅ Bot is working! Interaction test successful.")

# Step 1: Verification reaction
@bot.event
async def on_raw_reaction_add(payload):
    if payload.channel_id != START_CHANNEL_ID:
        return

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    # Ignore bot reactions
    if member.bot:
        return

    # Step 1: User clicks ✅
    if str(payload.emoji) == "✅":
        # CHECK IF USER ALREADY HAS DOMAIN OR RESEARCHER ROLES (already verified)
        user_domain_roles = [role for role in member.roles if role.id in DOMAINS.values()]
        user_researcher_roles = [role for role in member.roles if role.id in RESEARCHER_TYPES.values()]
        
        if user_domain_roles or user_researcher_roles:
            # User already has roles, don't let them restart
            try:
                await member.send("❌ You have already completed verification! If you need to change your domain or researcher type, **please ping an exec** in the server.")
            except discord.Forbidden:
                pass
            return

        role = guild.get_role(ROLE_MEMBER)
        if role and role not in member.roles:
            await member.add_roles(role)
            user_progress[member.id] = {"step": 1, "domain": None, "researcher": None}

            try:
                await member.send("✅ Member role added! Next, select your **domain**.")
                await send_domain_selection(member)
            except discord.Forbidden:
                # Can't send DM to user
                channel = guild.get_channel(START_CHANNEL_ID)
                await channel.send(
                    f"{member.mention} I couldn't DM you! Please enable DMs from server members to continue.",
                    delete_after=30)

# Step 2: Domain selection via DM
async def send_domain_selection(member):
    embed = discord.Embed(
        title="🔬 Select Your Domain",
        description="Choose the domain you're most interested in:\n\n**⚠️ Note: This choice is permanent!**\nIf you need to change it later, **please ping an exec**.",
        color=0x00ff00
    )

    view = DomainSelectionView()
    try:
        await member.send(embed=embed, view=view)
    except discord.Forbidden:
        pass

# Step 3: Researcher selection via DM
async def send_researcher_selection(member):
    embed = discord.Embed(
        title="🧪 Select Your Researcher Type", 
        description="Choose how you prefer to conduct research:\n\n**⚠️ Note: This choice is permanent!**\nIf you need to change it later, **please ping an exec**.",
        color=0x00ff00
    )

    view = ResearcherSelectionView()
    try:
        await member.send(embed=embed, view=view)
    except discord.Forbidden:
        pass

# Step 4: Completion
async def complete_verification(member):
    # Remove from progress tracking
    if member.id in user_progress:
        del user_progress[member.id]

    try:
        await member.send("🎉 All steps completed! You now have full server access with your selected roles.\n\n**Remember:** Your domain and researcher type are permanent. **Please ping an exec** if you need changes.")
    except discord.Forbidden:
        pass

# UPDATED Button Views with error handling
class DomainSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout

    @discord.ui.button(label="Social Science, Humanities, Arts", style=discord.ButtonStyle.primary)
    async def social_science_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.handle_domain_selection(interaction, "Social Science, Humanities, Arts")
        except Exception as e:
            print(f"Domain selection error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)

    @discord.ui.button(label="Management", style=discord.ButtonStyle.primary)
    async def management_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.handle_domain_selection(interaction, "Management")
        except Exception as e:
            print(f"Domain selection error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)

    @discord.ui.button(label="CS/Math", style=discord.ButtonStyle.primary)
    async def cs_math_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.handle_domain_selection(interaction, "CS/Math")
        except Exception as e:
            print(f"Domain selection error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)

    @discord.ui.button(label="Natural + Physical Sciences", style=discord.ButtonStyle.primary)
    async def natural_sciences_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.handle_domain_selection(interaction, "Natural + Physical Sciences")
        except Exception as e:
            print(f"Domain selection error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)

    async def handle_domain_selection(self, interaction: discord.Interaction, domain: str):
        try:
            # Defer the response first
            await interaction.response.defer(ephemeral=True)
            
            member = interaction.user
            
            # Get guild from bot
            guild = bot.get_guild(GUILD_ID)
            if not guild:
                await interaction.followup.send("Error: Cannot find server.", ephemeral=True)
                return

            # Get the member object from the guild
            guild_member = guild.get_member(member.id)
            if not guild_member:
                await interaction.followup.send("Error: You are not in the server.", ephemeral=True)
                return

            # PREVENT CHANGES: Check if user already has any domain role
            user_domain_roles = [role for role in guild_member.roles if role.id in DOMAINS.values()]
            if user_domain_roles:
                await interaction.followup.send("❌ You already have a domain role! To change it, **please ping an exec**.", ephemeral=True)
                return

            # Get domain role
            domain_role_id = DOMAINS.get(domain)
            if not domain_role_id:
                await interaction.followup.send("Error: Domain role not found.", ephemeral=True)
                return

            domain_role = guild.get_role(domain_role_id)
            if not domain_role:
                await interaction.followup.send("Error: Domain role not found in server.", ephemeral=True)
                return

            # Add domain role and update progress
            if domain_role not in guild_member.roles:
                await guild_member.add_roles(domain_role)

            if guild_member.id in user_progress:
                user_progress[guild_member.id]["step"] = 2
                user_progress[guild_member.id]["domain"] = domain

            await interaction.followup.send(f"✅ **{domain}** domain selected! Now choose your researcher type.", ephemeral=True)
            await send_researcher_selection(guild_member)
            
        except Exception as e:
            print(f"Error in domain selection: {e}")
            await interaction.followup.send("❌ Failed to assign domain role. Please contact an admin.", ephemeral=True)

class ResearcherSelectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout

    @discord.ui.button(label="Dedicated", style=discord.ButtonStyle.success)
    async def dedicated_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.handle_researcher_selection(interaction, "Dedicated")
        except Exception as e:
            print(f"Researcher selection error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)

    @discord.ui.button(label="Intermediate", style=discord.ButtonStyle.success)
    async def intermediate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.handle_researcher_selection(interaction, "Intermediate")
        except Exception as e:
            print(f"Researcher selection error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)

    @discord.ui.button(label="Casual", style=discord.ButtonStyle.success)
    async def casual_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.handle_researcher_selection(interaction, "Casual")
        except Exception as e:
            print(f"Researcher selection error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred. Please try again or contact an admin.", ephemeral=True)

    async def handle_researcher_selection(self, interaction: discord.Interaction, researcher: str):
        try:
            # Defer the response first
            await interaction.response.defer(ephemeral=True)
            
            member = interaction.user
            
            # Get guild from bot
            guild = bot.get_guild(GUILD_ID)
            if not guild:
                await interaction.followup.send("Error: Cannot find server.", ephemeral=True)
                return

            # Get the member object from the guild
            guild_member = guild.get_member(member.id)
            if not guild_member:
                await interaction.followup.send("Error: You are not in the server.", ephemeral=True)
                return

            # PREVENT CHANGES: Check if user already has any researcher role
            user_researcher_roles = [role for role in guild_member.roles if role.id in RESEARCHER_TYPES.values()]
            if user_researcher_roles:
                await interaction.followup.send("❌ You already have a researcher type! To change it, **please ping an exec**.", ephemeral=True)
                return

            # Get researcher role
            researcher_role_id = RESEARCHER_TYPES.get(researcher)
            if not researcher_role_id:
                await interaction.followup.send("Error: Researcher role not found.", ephemeral=True)
                return

            researcher_role = guild.get_role(researcher_role_id)
            if not researcher_role:
                await interaction.followup.send("Error: Researcher role not found in server.", ephemeral=True)
                return

            # Add researcher role and update progress
            if researcher_role not in guild_member.roles:
                await guild_member.add_roles(researcher_role)

            if guild_member.id in user_progress:
                user_progress[guild_member.id]["step"] = 3
                user_progress[guild_member.id]["researcher"] = researcher

            await interaction.followup.send(f"✅ **{researcher}** type selected! Completing your verification...", ephemeral=True)
            await complete_verification(guild_member)
            
        except Exception as e:
            print(f"Error in researcher selection: {e}")
            await interaction.followup.send("❌ Failed to assign researcher role. Please contact an admin.", ephemeral=True)

# ========== EXEC COMMANDS FOR MANUAL MANAGEMENT ==========

@bot.command()
@commands.has_permissions(administrator=True)
async def change_domain(ctx, member: discord.Member, new_domain: str):
    """Exec command to change a user's domain"""
    if new_domain not in DOMAINS:
        await ctx.send(f"❌ Invalid domain. Choose from: {', '.join(DOMAINS.keys())}")
        return
    
    # Get current domain roles to remove
    current_domain_roles = [role for role in member.roles if role.id in DOMAINS.values()]
    
    # Get new domain role
    new_domain_role_id = DOMAINS[new_domain]
    new_domain_role = ctx.guild.get_role(new_domain_role_id)
    
    if not new_domain_role:
        await ctx.send("❌ Error: New domain role not found in server.")
        return
    
    # Remove old domain roles and add new one
    if current_domain_roles:
        await member.remove_roles(*current_domain_roles)
    
    await member.add_roles(new_domain_role)
    
    await ctx.send(f"✅ Changed {member.mention}'s domain to **{new_domain}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def change_researcher(ctx, member: discord.Member, new_researcher: str):
    """Exec command to change a user's researcher type"""
    if new_researcher not in RESEARCHER_TYPES:
        await ctx.send(f"❌ Invalid researcher type. Choose from: {', '.join(RESEARCHER_TYPES.keys())}")
        return
    
    # Get current researcher roles to remove
    current_researcher_roles = [role for role in member.roles if role.id in RESEARCHER_TYPES.values()]
    
    # Get new researcher role
    new_researcher_role_id = RESEARCHER_TYPES[new_researcher]
    new_researcher_role = ctx.guild.get_role(new_researcher_role_id)
    
    if not new_researcher_role:
        await ctx.send("❌ Error: New researcher role not found in server.")
        return
    
    # Remove old researcher roles and add new one
    if current_researcher_roles:
        await member.remove_roles(*current_researcher_roles)
    
    await member.add_roles(new_researcher_role)
    
    await ctx.send(f"✅ Changed {member.mention}'s researcher type to **{new_researcher}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def view_roles(ctx, member: discord.Member):
    """View a user's current domain and researcher roles"""
    domain_roles = [role for role in member.roles if role.id in DOMAINS.values()]
    researcher_roles = [role for role in member.roles if role.id in RESEARCHER_TYPES.values()]
    
    domain_str = domain_roles[0].name if domain_roles else "None"
    researcher_str = researcher_roles[0].name if researcher_roles else "None"
    
    embed = discord.Embed(title=f"Roles for {member.display_name}", color=0x00ff00)
    embed.add_field(name="Domain", value=domain_str, inline=True)
    embed.add_field(name="Researcher Type", value=researcher_str, inline=True)
    
    await ctx.send(embed=embed)

# Optional: Add a command to check progress
@bot.command()
@commands.has_permissions(administrator=True)
async def check_progress(ctx, member: discord.Member = None):
    if not member:
        member = ctx.author

    if member.id in user_progress:
        progress = user_progress[member.id]
        await ctx.send(f"**{member.display_name}'s Progress:**\n"
                       f"Step: {progress['step']}/3\n"
                       f"Domain: {progress.get('domain', 'Not selected')}\n"
                       f"Researcher: {progress.get('researcher', 'Not selected')}")
    else:
        await ctx.send(f"{member.display_name} hasn't started the verification process.")

@bot.command()
@commands.has_permissions(administrator=True)
async def reset_progress(ctx, member: discord.Member):
    if member.id in user_progress:
        del user_progress[member.id]
        await ctx.send(f"Reset progress for {member.display_name}")
    else:
        await ctx.send(f"No progress found for {member.display_name}")

# This should be at the VERY END of your file
if __name__ == "__main__":
    keep_alive()  # ADD THIS LINE
    bot.run(token)
