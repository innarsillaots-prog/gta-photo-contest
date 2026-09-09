import os
import discord
from discord.ext import commands


PHOTO_CONTEST_CHANNEL_ID = 1547228944728592435

voted_users = set()


class VoteButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Vote",
        emoji="🗳️",
        style=discord.ButtonStyle.primary
    )
    async def vote(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user_id = interaction.user.id

        if user_id in voted_users:
            await interaction.response.send_message(
                "❌ You have already voted in this contest.",
                ephemeral=True
            )
            return

        voted_users.add(user_id)

        await interaction.response.send_message(
            "✅ Your vote has been recorded!",
            ephemeral=True
        )


class ContestBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()


intents = discord.Intents.default()

bot = ContestBot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")


@bot.tree.command(
    name="ping",
    description="Check if the bot is working"
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🏁 GTA Photo Contest bot is online!"
    )


@bot.tree.command(
    name="submit",
    description="Submit a photo to the contest"
)
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
    view = VoteButton()

    await channel.send(
        content="📸 New anonymous contest entry",
        file=file,
        view=view
    )

    await interaction.response.send_message(
        "✅ Your photo was submitted anonymously!",
        ephemeral=True
    )


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

bot.run(TOKEN)
