import os
import discord
from discord.ext import commands


PHOTO_CONTEST_CHANNEL_ID = 1547228944728592435

# Temporary contest data
entry_counter = 0
votes_by_entry = {}
user_votes = {}


class VoteButton(discord.ui.View):
    def __init__(self, entry_id):
        super().__init__(timeout=None)
        self.entry_id = entry_id

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

        # One vote per user for the whole contest
        if user_id in user_votes:
            await interaction.response.send_message(
                "❌ You have already voted in this contest.",
                ephemeral=True
            )
            return

        # Save which entry this user voted for
        user_votes[user_id] = self.entry_id

        # Add one vote to this entry
        votes_by_entry[self.entry_id] = (
            votes_by_entry.get(self.entry_id, 0) + 1
        )

        await interaction.response.send_message(
            f"✅ Your vote for Entry #{self.entry_id} has been recorded!",
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
    global entry_counter

    channel = bot.get_channel(PHOTO_CONTEST_CHANNEL_ID)

    if channel is None:
        await interaction.response.send_message(
            "❌ Photo contest channel was not found.",
            ephemeral=True
        )
        return

    # Only allow images
    if photo.content_type is not None:
        if not photo.content_type.startswith("image/"):
            await interaction.response.send_message(
                "❌ Please submit an image file.",
                ephemeral=True
            )
            return

    entry_counter += 1
    entry_id = entry_counter

    votes_by_entry[entry_id] = 0

    file = await photo.to_file()
    view = VoteButton(entry_id)

    await channel.send(
        content=f"📸 **Entry #{entry_id}**",
        file=file,
        view=view
    )

    await interaction.response.send_message(
        f"✅ Your photo was submitted anonymously as Entry #{entry_id}!",
        ephemeral=True
    )


@bot.tree.command(
    name="results",
    description="View the current contest results"
)
async def results(interaction: discord.Interaction):

    # Admin only
    if (
        not isinstance(interaction.user, discord.Member)
        or not interaction.user.guild_permissions.administrator
    ):
        await interaction.response.send_message(
            "❌ Only administrators can view the results.",
            ephemeral=True
        )
        return

    if entry_counter == 0:
        await interaction.response.send_message(
            "📊 There are no contest entries yet.",
            ephemeral=True
        )
        return

    result_lines = []

    for entry_id in range(1, entry_counter + 1):
        votes = votes_by_entry.get(entry_id, 0)
        result_lines.append(
            f"📸 Entry #{entry_id} — **{votes} vote(s)**"
        )

    total_votes = len(user_votes)

    results_text = (
        "🏆 **PHOTO CONTEST RESULTS**\n\n"
        + "\n".join(result_lines)
        + f"\n\n🗳️ Total votes: **{total_votes}**"
    )

    await interaction.response.send_message(
        results_text,
        ephemeral=True
    )


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

bot.run(TOKEN)
