import os
import discord
from discord.ext import commands

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

@bot.tree.command(name="ping", description="Check if the bot is working")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏁 GTA Photo Contest bot is online!")

@bot.event
async def setup_hook():
    await bot.tree.sync()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

bot.run(TOKEN)
