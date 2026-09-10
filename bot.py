import os
import discord
from discord.ext import commands


PHOTO_CONTEST_CHANNEL_ID = 1547228944728592435

entry_counter = 0
votes_by_entry = {}
user_votes = {}
entry_submitters = {}
entry_photo_urls = {}

contest_open = True
contest_id = 1
current_theme = None


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
                "🔒 This photo belongs to an old contest. Voting is closed.",
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
            old_count = votes_by_entry.get(previous_vote, 0)

            if old_count > 0:
                votes_by_entry[previous_vote] = old_count - 1

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
    def __init__(self, admin_id, theme):
        super().__init__(timeout=60)

        self.admin_id = admin_id
        self.theme = theme

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
        global entry_photo_urls
        global contest_open
        global contest_id
        global current_theme

        channel = interaction.client.get_channel(
            PHOTO_CONTEST_CHANNEL_ID
        )

        deleted_photos = 0
        deleted_announcements = 0

        if channel is not None:
            async for message in channel.history(limit=None):
                if message.author.id != interaction.client.user.id:
                    continue

                if message.content.startswith("📸 Photo #"):
                    try:
                        await message.delete()
                        deleted_photos += 1
                    except discord.HTTPException:
                        pass

                elif message.content.startswith(
                    "📸 **NEW PHOTO CONTEST!**"
                ):
                    try:
                        await message.delete()
                        deleted_announcements += 1
                    except discord.HTTPException:
                        pass

        contest_id += 1

        entry_counter = 0
        votes_by_entry = {}
        user_votes = {}
        entry_submitters = {}
        entry_photo_urls = {}

        contest_open = True
        current_theme = self.theme

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                "🆕 New photo contest started!\n\n"
                "🎨 Theme: **"
                + current_theme
                + "**\n"
                "🗑️ Deleted "
                + str(deleted_photos)
                + " old photo post(s).\n"
                "🧹 Deleted "
                + str(deleted_announcements)
                + " old contest announcement(s).\n"
                "📸 The next submission will be Photo #1.\n"
                "🗳️ Voting is open."
            ),
            view=self
        )

        if channel is not None:
            announcement = (
                "📸 **NEW PHOTO CONTEST!**\n\n"
                "🎨 **Theme: "
                + current_theme
                + "**\n\n"
                "📷 Submit your best photo matching this week's theme!\n"
                "🗳️ Voting is open!"
            )

            await channel.send(announcement)

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
                "❌ New contest cancelled. Nothing was changed."
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
    print("Bot is online as " + str(bot.user))


def is_admin(interaction: discord.Interaction):
    return (
        isinstance(interaction.user, discord.Member)
        and interaction.user.guild_permissions.administrator
    )


def build_results_text(title):
    result_lines = []

    for photo_id in range(1, entry_counter + 1):
        votes = votes_by_entry.get(photo_id, 0)

        line = (
            "📸 Photo #"
            + str(photo_id)
            + " — "
            + str(votes)
            + " vote(s)"
        )

        result_lines.append(line)

    total_votes = len(user_votes)

    theme_text = ""

    if current_theme:
        theme_text = (
            "\n🎨 Theme: **"
            + current_theme
            + "**"
        )

    return (
        title
        + theme_text
        + "\n\n"
        + "\n".join(result_lines)
        + "\n\n🗳️ Total votes: "
        + str(total_votes)
    )


def get_podium_groups():
    vote_levels = sorted(
        {
            votes_by_entry.get(photo_id, 0)
            for photo_id in range(1, entry_counter + 1)
            if votes_by_entry.get(photo_id, 0) > 0
        },
        reverse=True
    )

    top_levels = vote_levels[:3]
    groups = []

    for votes in top_levels:
        photo_ids = []

        for photo_id in range(1, entry_counter + 1):
            if votes_by_entry.get(photo_id, 0) == votes:
                photo_ids.append(photo_id)

        groups.append(
            {
                "votes": votes,
                "photo_ids": photo_ids
            }
        )

    return groups


def get_submitter_mention(photo_id):
    submitter = entry_submitters.get(photo_id)

    if submitter is None:
        return "Unknown"

    return (
        "<@"
        + str(submitter["user_id"])
        + ">"
    )


def build_podium_description(groups):
    medal_labels = [
        ("🥇", "1st"),
        ("🥈", "2nd"),
        ("🥉", "3rd")
    ]

    lines = []

    for index, group in enumerate(groups):
        medal, place_name = medal_labels[index]

        for photo_id in group["photo_ids"]:
            line = (
                medal
                + " **"
                + place_name
                + " — Photo #"
                + str(photo_id)
                + "** — "
                + str(group["votes"])
                + " vote(s) — "
                + get_submitter_mention(photo_id)
            )
            lines.append(line)

    return "\n".join(lines)


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

    if not contest_open:
        await interaction.response.send_message(
            "🔒 This contest is closed. New photos cannot be submitted.",
            ephemeral=True
        )
        return

    for submitter in entry_submitters.values():
        if submitter["user_id"] == interaction.user.id:
            await interaction.response.send_message(
                "❌ You have already submitted a photo to this contest.",
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
        and not photo.content_type.startswith("image/")
    ):
        await interaction.response.send_message(
            "❌ Please submit an image file.",
            ephemeral=True
        )
        return

    entry_counter += 1

    photo_id = entry_counter

    votes_by_entry[photo_id] = 0

    if isinstance(interaction.user, discord.Member):
        nickname = interaction.user.display_name
    else:
        nickname = str(interaction.user)

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

    sent_message = await channel.send(
        content=photo_text,
        file=file,
        view=view
    )

    if sent_message.attachments:
        entry_photo_urls[photo_id] = (
            sent_message.attachments[0].url
        )

    confirmation = (
        "✅ Your photo was submitted anonymously as Photo #"
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
async def results(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can view the results.",
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
async def entries(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can view photo owners.",
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

    for photo_id in range(1, entry_counter + 1):
        submitter = entry_submitters.get(photo_id)

        if submitter is None:
            owner_text = "Unknown"
        else:
            owner_text = submitter["nickname"]

        line = (
            "📸 Photo #"
            + str(photo_id)
            + " — "
            + owner_text
        )

        entry_lines.append(line)

    theme_text = ""

    if current_theme:
        theme_text = (
            "\n🎨 Theme: **"
            + current_theme
            + "**"
        )

    entries_text = (
        "🔒 ADMIN — CONTEST PHOTOS"
        + theme_text
        + "\n\n"
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
async def closecontest(interaction: discord.Interaction):
    global contest_open

    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can close the contest.",
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
            "📸 There are no contest photos to close.",
            ephemeral=True
        )
        return

    contest_open = False

    max_votes = max(
        votes_by_entry.get(photo_id, 0)
        for photo_id in range(1, entry_counter + 1)
    )

    results_text = build_results_text(
        "🔒 PHOTO CONTEST CLOSED"
    )

    if max_votes == 0:
        await interaction.response.send_message(
            results_text
            + "\n\n🏆 No winner — no votes were cast.",
            ephemeral=True
        )

        channel = bot.get_channel(
            PHOTO_CONTEST_CHANNEL_ID
        )

        if channel is not None:
            no_votes_embed = discord.Embed(
                title="🏁 PHOTO CONTEST CLOSED!",
                description=(
                    "🎨 **Theme: "
                    + str(current_theme)
                    + "**\n\n"
                    "No winner this time because no votes were cast."
                )
            )

            await channel.send(
                embed=no_votes_embed
            )

        return

    groups = get_podium_groups()

    first_place_group = groups[0]
    first_place_ids = first_place_group["photo_ids"]

    if len(first_place_ids) == 1:
        admin_winner_text = (
            "\n\n🏆 Winner: Photo #"
            + str(first_place_ids[0])
            + " with "
            + str(first_place_group["votes"])
            + " vote(s)!"
        )
    else:
        tied_ids = []

        for photo_id in first_place_ids:
            tied_ids.append(
                "#"
                + str(photo_id)
            )

        admin_winner_text = (
            "\n\n🏆 Tie for 1st: Photos "
            + ", ".join(tied_ids)
            + " with "
            + str(first_place_group["votes"])
            + " vote(s) each!"
        )

    await interaction.response.send_message(
        results_text + admin_winner_text,
        ephemeral=True
    )

    channel = bot.get_channel(
        PHOTO_CONTEST_CHANNEL_ID
    )

    if channel is None:
        return

    podium_text = build_podium_description(
        groups
    )

    public_embed = discord.Embed(
        title="🏆 PHOTO CONTEST RESULTS!",
        description=(
            "🎨 **Theme: "
            + str(current_theme)
            + "**\n\n"
            + podium_text
        )
    )

    if len(first_place_ids) == 1:
        winner_photo_id = first_place_ids[0]
        winner_photo_url = entry_photo_urls.get(
            winner_photo_id
        )

        if winner_photo_url:
            public_embed.set_image(
                url=winner_photo_url
            )

        public_embed.set_footer(
            text=(
                "Winning photo: Photo #"
                + str(winner_photo_id)
            )
        )

        winner_submitter = entry_submitters.get(
            winner_photo_id
        )

        if winner_submitter is not None:
            winner_ping = (
                "🎉 Congratulations <@"
                + str(winner_submitter["user_id"])
                + ">!"
            )
        else:
            winner_ping = "🎉 Congratulations!"

        await channel.send(
            content=winner_ping,
            embed=public_embed,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False
            )
        )

    else:
        winner_mentions = []

        for photo_id in first_place_ids:
            submitter = entry_submitters.get(
                photo_id
            )

            if submitter is not None:
                winner_mentions.append(
                    "<@"
                    + str(submitter["user_id"])
                    + ">"
                )

        if winner_mentions:
            winner_ping = (
                "🎉 Congratulations "
                + " & ".join(winner_mentions)
                + "!"
            )
        else:
            winner_ping = (
                "🎉 Congratulations to the winners!"
            )

        await channel.send(
            content=winner_ping,
            embed=public_embed,
            allowed_mentions=discord.AllowedMentions(
                users=True,
                roles=False,
                everyone=False
            )
        )


@bot.tree.command(
    name="newcontest",
    description="Start a new photo contest"
)
@discord.app_commands.describe(
    theme="Theme for the new photo contest"
)
async def newcontest(
    interaction: discord.Interaction,
    theme: str
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can start a new contest.",
            ephemeral=True
        )
        return

    theme = theme.strip()

    if not theme:
        await interaction.response.send_message(
            "❌ Please enter a contest theme.",
            ephemeral=True
        )
        return

    warning = (
        "⚠️ START A NEW PHOTO CONTEST?\n\n"
        "🎨 Theme: **"
        + theme
        + "**\n\n"
        "This will delete all photo posts and the old "
        "contest announcement from the previous contest. "
        "The rules post will stay in the channel.\n\n"
        "Photo numbers, votes, and the submitter list "
        "will also be reset.\n\n"
        "🗑️ Deleted contest posts cannot be restored."
    )

    await interaction.response.send_message(
        warning,
        view=NewContestConfirmView(
            interaction.user.id,
            theme
        ),
        ephemeral=True
    )


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError(
        "DISCORD_TOKEN is not set"
    )

bot.run(TOKEN)
