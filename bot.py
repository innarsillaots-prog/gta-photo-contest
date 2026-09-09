import os
import discord
from discord.ext import commands

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

PHOTO_CONTEST_CHANNEL_ID = 1547228944728592435

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

@bot.tree.command(name="ping", description="Check if the bot is working")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏁 GTA Photo Contest bot is online!")
@bot.tree.command(name="submit", description="Submit a photo to the contest")
async def submit(
    interaction: discord.Interaction,
    photo: discord.Attachment
):
    channel = bot.get_channel(PHOTO_CONTEST_CHANNEL_ID)

    if channel is None:
        await interaction.response.send_message(
            "❌ Photo contest channel was not found.",
            ephemeral=True
        )
        return

    file = await photo.to_file()

    await channel.send(
        content="📸 New anonymous contest entry",
        file=file
    )

    await interaction.response.send_message(
        "✅ Your photo was submitted anonymously!",
        ephemeral=True
    )
@bot.event
async def setup_hook():
    await bot.tree.sync()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

bot.run(TOKEN)
