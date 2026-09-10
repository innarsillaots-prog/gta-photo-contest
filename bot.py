import os
import discord
from discord.ext import commands


PHOTO_CONTEST_CHANNEL_ID = 1547228944728592435

entry_counter = 0
votes_by_entry = {}
user_votes = {}
entry_submitters = {}

contest_open = True
contest_id = 1


class VoteButton(discord.ui.View):
    def __init__(self, photo_id, photo_contest_id):
        super().__init__(timeout=None)

        self.photo_id = photo_id
        self.photo_contest_id = photo_contest_id

        button = discord.ui.Button(
            label="Vote",
            emoji="🗳️",
            style=discord.ButtonStyle.primary
        )

        button.callback = self.vote
        self.add_item(button)

    async def vote(self, interaction: discord.Interaction):
        global contest_open
        global contest_id

        if self.photo_contest_id != contest_id:
            await interaction.response.send_message(
                "🔒 This photo belongs to an old contest. "
                "Voting is closed.",
                ephemeral=True
            )
            return

        if not contest_open:
            await interaction.response.send_message(
                "🔒 Voting for this contest is closed.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        previous_vote = user_votes.get(user_id)

        if previous_vote == self.photo_id:
            await interaction.response.send_message(
                "✅ You have already voted for Photo #"
                + str(self.photo_id)
                + ".",
                ephemeral=True
            )
            return

        if previous_vote is not None:
            old_count = votes_by_entry.get(
                previous_vote,
                0
            )

            if old_count > 0:
                votes_by_entry[previous_vote] = (
                    old_count - 1
                )

        user_votes[user_id] = self.photo_id

        votes_by_entry[self.photo_id] = (
            votes_by_entry.get(self.photo_id, 0) + 1
        )

        if previous_vote is None:
            message = (
                "✅ Voted for Photo #"
                + str(self.photo_id)
                + "!"
            )

        else:
            message = (
                "🔄 Your vote was changed from Photo #"
                + str(previous_vote)
                + " to Photo #"
                + str(self.photo_id)
                + "!"
            )

        await interaction.response.send_message(
            message,
            ephemeral=True
        )


class NewContestConfirmView(discord.ui.View):
    def __init__(self, admin_id):
        super().__init__(timeout=60)

        self.admin_id = admin_id

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message(
                "❌ Only the administrator who started "
                "this action can use these buttons.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Start New Contest",
        emoji="✅",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        global entry_counter
        global votes_by_entry
        global user_votes
        global entry_submitters
        global contest_open
        global contest_id

        channel = interaction.client.get_channel(
            PHOTO_CONTEST_CHANNEL_ID
        )

        deleted_photos = 0

        if channel is not None:
            async for message in channel.history(
                limit=None
            ):
                if (
                    message.author.id
                    == interaction.client.user.id
                    and message.content.startswith(
                        "📸 Photo #"
                    )
                ):
                    try:
                        await message.delete()
                        deleted_photos += 1
                    except discord.HTTPException:
                        pass

        contest_id += 1

        entry_counter = 0
        votes_by_entry = {}
        user_votes = {}
        entry_submitters = {}

        contest_open = True

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                "🆕 New photo contest started!\n\n"
                "🗑️ Deleted "
                + str(deleted_photos)
                + " old photo post(s).\n"
                "📸 The next submission will be Photo #1.\n"
                "🗳️ Voting is open."
            ),
            view=self
        )

        self.stop()

    @discord.ui.button(
        label="Cancel",
        emoji="❌",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                "❌ New contest cancelled. "
                "Nothing was changed."
            ),
            view=self
        )

        self.stop()


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
    print(
        "Bot is online as "
        + str(bot.user)
    )


def is_admin(interaction: discord.Interaction):
    return (
        isinstance(
            interaction.user,
            discord.Member
        )
        and interaction.user
        .guild_permissions
        .administrator
    )


def build_results_text(title):
    result_lines = []

    for photo_id in range(
        1,
        entry_counter + 1
    ):
        votes = votes_by_entry.get(
            photo_id,
            0
        )

        line = (
            "📸 Photo #"
            + str(photo_id)
            + " — "
            + str(votes)
            + " vote(s)"
        )

        result_lines.append(line)

    total_votes = len(user_votes)

    text = (
        title
        + "\n\n"
        + "\n".join(result_lines)
        + "\n\n🗳️ Total votes: "
        + str(total_votes)
    )

    return text


@bot.tree.command(
    name="ping",
    description="Check if the bot is working"
)
async def ping(
    interaction: discord.Interaction
):
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

    if not contest_open:
        await interaction.response.send_message(
            "🔒 This contest is closed. "
            "New photos cannot be submitted.",
            ephemeral=True
        )
        return

    channel = bot.get_channel(
        PHOTO_CONTEST_CHANNEL_ID
    )

    if channel is None:
        await interaction.response.send_message(
            "❌ Photo contest channel was not found.",
            ephemeral=True
        )
        return

    if (
        photo.content_type is not None
        and not photo.content_type.startswith(
            "image/"
        )
    ):
        await interaction.response.send_message(
            "❌ Please submit an image file.",
            ephemeral=True
        )
        return

    entry_counter += 1

    photo_id = entry_counter

    votes_by_entry[photo_id] = 0

    if isinstance(
        interaction.user,
        discord.Member
    ):
        nickname = interaction.user.display_name

    else:
        nickname = str(
            interaction.user
        )

    entry_submitters[photo_id] = {
        "user_id": interaction.user.id,
        "nickname": nickname
    }

    file = await photo.to_file()

    view = VoteButton(
        photo_id,
        contest_id
    )

    photo_text = (
        "📸 Photo #"
        + str(photo_id)
    )

    await channel.send(
        content=photo_text,
        file=file,
        view=view
    )

    confirmation = (
        "✅ Your photo was submitted "
        "anonymously as Photo #"
        + str(photo_id)
        + "!"
    )

    await interaction.response.send_message(
        confirmation,
        ephemeral=True
    )


@bot.tree.command(
    name="results",
    description="View the current contest results"
)
async def results(
    interaction: discord.Interaction
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can "
            "view the results.",
            ephemeral=True
        )
        return

    if entry_counter == 0:
        await interaction.response.send_message(
            "📊 There are no contest photos yet.",
            ephemeral=True
        )
        return

    results_text = build_results_text(
        "🏆 PHOTO CONTEST RESULTS"
    )

    await interaction.response.send_message(
        results_text,
        ephemeral=True
    )


@bot.tree.command(
    name="entries",
    description="View contest photo owners"
)
async def entries(
    interaction: discord.Interaction
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can "
            "view photo owners.",
            ephemeral=True
        )
        return

    if entry_counter == 0:
        await interaction.response.send_message(
            "📸 There are no contest photos yet.",
            ephemeral=True
        )
        return

    entry_lines = []

    for photo_id in range(
        1,
        entry_counter + 1
    ):
        submitter = entry_submitters.get(
            photo_id
        )

        if submitter is None:
            owner_text = "Unknown"

        else:
            owner_text = submitter[
                "nickname"
            ]

        line = (
            "📸 Photo #"
            + str(photo_id)
            + " — "
            + owner_text
        )

        entry_lines.append(line)

    entries_text = (
        "🔒 ADMIN — CONTEST PHOTOS\n\n"
        + "\n".join(entry_lines)
    )

    await interaction.response.send_message(
        entries_text,
        ephemeral=True
    )


@bot.tree.command(
    name="closecontest",
    description="Close the current photo contest"
)
async def closecontest(
    interaction: discord.Interaction
):
    global contest_open

    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can "
            "close the contest.",
            ephemeral=True
        )
        return

    if not contest_open:
        await interaction.response.send_message(
            "🔒 The contest is already closed.",
            ephemeral=True
        )
        return

    if entry_counter == 0:
        await interaction.response.send_message(
            "📸 There are no contest photos "
            "to close.",
            ephemeral=True
        )
        return

    contest_open = False

    max_votes = max(
        votes_by_entry.get(
            photo_id,
            0
        )
        for photo_id in range(
            1,
            entry_counter + 1
        )
    )

    winners = []

    for photo_id in range(
        1,
        entry_counter + 1
    ):
        photo_votes = votes_by_entry.get(
            photo_id,
            0
        )

        if photo_votes == max_votes:
            winners.append(photo_id)

    results_text = build_results_text(
        "🔒 PHOTO CONTEST CLOSED"
    )

    if max_votes == 0:
        winner_text = (
            "\n\n🏆 No winner — "
            "no votes were cast."
        )

    elif len(winners) == 1:
        winner_text = (
            "\n\n🏆 Winner: Photo #"
            + str(winners[0])
            + " with "
            + str(max_votes)
            + " vote(s)!"
        )

    else:
        winner_numbers = []

        for photo_id in winners:
            winner_numbers.append(
                "#"
                + str(photo_id)
            )

        winner_text = (
            "\n\n🏆 Tie: Photos "
            + ", ".join(winner_numbers)
            + " with "
            + str(max_votes)
            + " vote(s) each!"
        )

    await interaction.response.send_message(
        results_text + winner_text,
        ephemeral=True
    )


@bot.tree.command(
    name="newcontest",
    description="Start a new photo contest"
)
async def newcontest(
    interaction: discord.Interaction
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can "
            "start a new contest.",
            ephemeral=True
        )
        return

    warning = (
        "⚠️ START A NEW PHOTO CONTEST?\n\n"
        "This will delete all photo posts from "
        "the previous contest and reset the photo "
        "numbers, votes, and submitter list.\n\n"
        "🗑️ Deleted photo posts cannot be restored."
    )

    await interaction.response.send_message(
        warning,
        view=NewContestConfirmView(
            interaction.user.id
        ),
        ephemeral=True
    )


TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

if not TOKEN:
    raise ValueError(
        "DISCORD_TOKEN is not set"
    )

bot.run(TOKEN)
