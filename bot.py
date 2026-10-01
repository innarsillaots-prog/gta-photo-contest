import os
import time
import io
import discord
from discord.ext import commands

PHOTO_CONTEST_CHANNEL_ID = 1547228944728592435
WEEKLY_WINNER_CHANNEL_ID = 1547518516750585948

entry_counter = 0
votes_by_entry = {}
user_votes = {}
entry_submitters = {}
entry_photo_urls = {}
entry_message_ids = {}

contest_phase = "closed"
contest_id = 1
current_theme = None
submission_deadline = None
voting_deadline = None


def discord_timestamp(timestamp):
    return "<t:" + str(int(timestamp)) + ":F>"


def discord_relative_timestamp(timestamp):
    return "<t:" + str(int(timestamp)) + ":R>"


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
        global contest_phase, contest_id

        if self.photo_contest_id != contest_id:
            await interaction.response.send_message(
                "🔒 This photo belongs to an old contest. Voting is closed.",
                ephemeral=True
            )
            return

        if contest_phase == "submissions":
            await interaction.response.send_message(
                "⏳ Voting is not open yet. Photo submissions are still open.",
                ephemeral=True
            )
            return

        if contest_phase != "voting":
            await interaction.response.send_message(
                "🔒 Voting for this contest is closed.",
                ephemeral=True
            )
            return

        submitter = entry_submitters.get(self.photo_id)
        if submitter is not None and submitter["user_id"] == interaction.user.id:
            await interaction.response.send_message(
                "❌ You cannot vote for your own photo.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        previous_vote = user_votes.get(user_id)

        if previous_vote == self.photo_id:
            await interaction.response.send_message(
                "✅ You have already voted for Photo #" + str(self.photo_id) + ".",
                ephemeral=True
            )
            return

        if previous_vote is not None:
            old_count = votes_by_entry.get(previous_vote, 0)
            if old_count > 0:
                votes_by_entry[previous_vote] = old_count - 1

        user_votes[user_id] = self.photo_id
        votes_by_entry[self.photo_id] = votes_by_entry.get(self.photo_id, 0) + 1

        if previous_vote is None:
            message = "✅ Voted for Photo #" + str(self.photo_id) + "!"
        else:
            message = (
                "🔄 Your vote was changed from Photo #"
                + str(previous_vote)
                + " to Photo #"
                + str(self.photo_id)
                + "!"
            )

        await interaction.response.send_message(message, ephemeral=True)


class NewContestConfirmView(discord.ui.View):
    def __init__(self, admin_id, theme):
        super().__init__(timeout=60)
        self.admin_id = admin_id
        self.theme = theme

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.admin_id:
            await interaction.response.send_message(
                "❌ Only the administrator who started this action can use these buttons.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label="Start New Contest",
        emoji="✅",
        style=discord.ButtonStyle.danger
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        global entry_counter, votes_by_entry, user_votes, entry_submitters
        global entry_photo_urls, entry_message_ids, contest_phase, contest_id
        global current_theme, submission_deadline, voting_deadline

        channel = interaction.client.get_channel(PHOTO_CONTEST_CHANNEL_ID)
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
                elif message.content.startswith("📸 **NEW PHOTO CONTEST!**"):
                    try:
                        await message.delete()
                        deleted_announcements += 1
                    except discord.HTTPException:
                        pass
                elif message.content.startswith("🗳️ **VOTING IS NOW OPEN!**"):
                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass

        contest_id += 1
        entry_counter = 0
        votes_by_entry = {}
        user_votes = {}
        entry_submitters = {}
        entry_photo_urls = {}
        entry_message_ids = {}

        contest_phase = "submissions"
        current_theme = self.theme

        contest_start_time = int(time.time())
        submission_deadline = contest_start_time + (5 * 24 * 60 * 60)
        voting_deadline = contest_start_time + (7 * 24 * 60 * 60)

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                "🆕 New photo contest started!\n\n"
                "🎨 Theme: **" + current_theme + "**\n"
                "🗑️ Deleted " + str(deleted_photos) + " old photo post(s).\n"
                "🧹 Deleted " + str(deleted_announcements) + " old contest announcement(s).\n"
                "📸 Photo submissions are open.\n"
                "⏳ Voting is not open yet.\n\n"
                "⏰ Submissions close: " + discord_timestamp(submission_deadline) + "\n"
                + discord_relative_timestamp(submission_deadline) + "\n"
                "🏆 Voting closes: " + discord_timestamp(voting_deadline) + "\n"
                + discord_relative_timestamp(voting_deadline)
            ),
            view=self
        )

        if channel is not None:
            await channel.send(
                "📸 **NEW PHOTO CONTEST!**\n\n"
                "🎨 **Theme: " + current_theme + "**\n\n"
                "📷 Submit your best photo matching this week's theme!\n"
                "✅ Photo submissions are open.\n"
                "⏳ Voting will open later.\n\n"
                "⏰ **Submissions close:** " + discord_timestamp(submission_deadline) + "\n"
                "🗳️ **Voting begins:** " + discord_timestamp(submission_deadline) + "\n"
                "🕒 " + discord_relative_timestamp(submission_deadline)
            )
        self.stop()

    @discord.ui.button(label="Cancel", emoji="❌", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="❌ New contest cancelled. Nothing was changed.",
            view=self
        )
        self.stop()


class ContestBot(commands.Bot):
    async def setup_hook(self):
        await self.tree.sync()


intents = discord.Intents.default()
bot = ContestBot(command_prefix="!", intents=intents)


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
        result_lines.append(
            "📸 Photo #" + str(photo_id) + " — " + str(votes) + " vote(s)"
        )

    theme_text = ""
    if current_theme:
        theme_text = "\n🎨 Theme: **" + current_theme + "**"

    return (
        title + theme_text + "\n\n"
        + "\n".join(result_lines)
        + "\n\n🗳️ Total votes: " + str(len(user_votes))
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

    groups = []
    for votes in vote_levels[:3]:
        photo_ids = [
            photo_id
            for photo_id in range(1, entry_counter + 1)
            if votes_by_entry.get(photo_id, 0) == votes
        ]
        groups.append({"votes": votes, "photo_ids": photo_ids})
    return groups


def get_submitter_mention(photo_id):
    submitter = entry_submitters.get(photo_id)
    if submitter is None:
        return "Unknown"
    return "<@" + str(submitter["user_id"]) + ">"


def build_podium_description(groups):
    medal_labels = [("🥇", "1st"), ("🥈", "2nd"), ("🥉", "3rd")]
    lines = []

    for index, group in enumerate(groups):
        medal, place_name = medal_labels[index]
        for photo_id in group["photo_ids"]:
            lines.append(
                medal + " **" + place_name + " — Photo #" + str(photo_id)
                + "** — " + str(group["votes"]) + " vote(s) — "
                + get_submitter_mention(photo_id)
            )
    return "\n".join(lines)


async def copy_photo_file(photo_id):
    channel = bot.get_channel(PHOTO_CONTEST_CHANNEL_ID)
    message_id = entry_message_ids.get(photo_id)

    if channel is None or message_id is None:
        return None

    try:
        message = await channel.fetch_message(message_id)
        if not message.attachments:
            return None

        attachment = message.attachments[0]
        data = await attachment.read()

        extension = os.path.splitext(attachment.filename)[1]
        if not extension:
            extension = ".png"

        filename = "winning_photo_" + str(photo_id) + extension
        return discord.File(io.BytesIO(data), filename=filename)

    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


@bot.tree.command(name="ping", description="Check if the bot is working")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏁 GTA Photo Contest bot is online!")


@bot.tree.command(name="submit", description="Submit a photo to the contest")
async def submit(interaction: discord.Interaction, photo: discord.Attachment):
    global entry_counter

    if contest_phase == "closed":
        await interaction.response.send_message(
            "🔒 There is no active photo contest right now.", ephemeral=True
        )
        return

    if contest_phase == "voting":
        await interaction.response.send_message(
            "🔒 Photo submissions are closed. Voting is now open.", ephemeral=True
        )
        return

    for submitter in entry_submitters.values():
        if submitter["user_id"] == interaction.user.id:
            await interaction.response.send_message(
                "❌ You have already submitted a photo to this contest.", ephemeral=True
            )
            return

    channel = bot.get_channel(PHOTO_CONTEST_CHANNEL_ID)
    if channel is None:
        await interaction.response.send_message(
            "❌ Photo contest channel was not found.", ephemeral=True
        )
        return

    if photo.content_type is not None and not photo.content_type.startswith("image/"):
        await interaction.response.send_message(
            "❌ Please submit an image file.", ephemeral=True
        )
        return

    entry_counter += 1
    photo_id = entry_counter
    votes_by_entry[photo_id] = 0

    nickname = (
        interaction.user.display_name
        if isinstance(interaction.user, discord.Member)
        else str(interaction.user)
    )

    entry_submitters[photo_id] = {
        "user_id": interaction.user.id,
        "nickname": nickname
    }

    file = await photo.to_file()
    sent_message = await channel.send(
        content="📸 Photo #" + str(photo_id),
        file=file,
        view=VoteButton(photo_id, contest_id)
    )

    entry_message_ids[photo_id] = sent_message.id
    if sent_message.attachments:
        entry_photo_urls[photo_id] = sent_message.attachments[0].url

    await interaction.response.send_message(
        "✅ Your photo was submitted anonymously as Photo #" + str(photo_id) + "!",
        ephemeral=True
    )


@bot.tree.command(name="startvoting", description="Close submissions and open voting")
async def startvoting(interaction: discord.Interaction):
    global contest_phase

    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can start voting.", ephemeral=True
        )
        return

    if contest_phase == "closed":
        await interaction.response.send_message(
            "❌ There is no active photo contest.", ephemeral=True
        )
        return

    if contest_phase == "voting":
        await interaction.response.send_message("🗳️ Voting is already open.", ephemeral=True)
        return

    if entry_counter == 0:
        await interaction.response.send_message(
            "📸 There are no submitted photos yet.", ephemeral=True
        )
        return

    contest_phase = "voting"
    await interaction.response.send_message(
        "🗳️ Voting is now open!\n🔒 Photo submissions are now closed.",
        ephemeral=True
    )

    channel = bot.get_channel(PHOTO_CONTEST_CHANNEL_ID)
    if channel is not None:
        announcement = (
            "🗳️ **VOTING IS NOW OPEN!**\n\n"
            "🎨 **Theme: " + str(current_theme) + "**\n\n"
            "🔒 Photo submissions are now closed.\n"
            "✅ Everyone can vote for their favourite photo.\n"
            "🚫 You cannot vote for your own photo.\n"
            "🔄 You may change your vote before voting closes."
        )
        if voting_deadline is not None:
            announcement += (
                "\n\n⏰ **Voting closes:** " + discord_timestamp(voting_deadline)
                + "\n🕒 " + discord_relative_timestamp(voting_deadline)
                + "\n🏆 The winner will be announced after voting closes."
            )
        await channel.send(announcement)


@bot.tree.command(name="results", description="View the current contest results")
async def results(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can view the results.", ephemeral=True
        )
        return

    if entry_counter == 0:
        await interaction.response.send_message(
            "📊 There are no contest photos yet.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        build_results_text("🏆 PHOTO CONTEST RESULTS"), ephemeral=True
    )


@bot.tree.command(name="entries", description="View contest photo owners")
async def entries(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can view photo owners.", ephemeral=True
        )
        return

    if entry_counter == 0:
        await interaction.response.send_message(
            "📸 There are no contest photos yet.", ephemeral=True
        )
        return

    lines = []
    for photo_id in range(1, entry_counter + 1):
        submitter = entry_submitters.get(photo_id)
        owner_text = "Unknown" if submitter is None else submitter["nickname"]
        lines.append("📸 Photo #" + str(photo_id) + " — " + owner_text)

    theme_text = ""
    if current_theme:
        theme_text = "\n🎨 Theme: **" + current_theme + "**"

    await interaction.response.send_message(
        "🔒 ADMIN — CONTEST PHOTOS" + theme_text + "\n\n" + "\n".join(lines),
        ephemeral=True
    )


@bot.tree.command(name="closecontest", description="Close the current photo contest")
async def closecontest(interaction: discord.Interaction):
    global contest_phase

    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can close the contest.", ephemeral=True
        )
        return

    if contest_phase == "closed":
        await interaction.response.send_message(
            "🔒 The contest is already closed.", ephemeral=True
        )
        return

    if contest_phase == "submissions":
        await interaction.response.send_message(
            "⏳ Voting has not started yet.\nUse /startvoting before closing the contest.",
            ephemeral=True
        )
        return

    if entry_counter == 0:
        await interaction.response.send_message(
            "📸 There are no contest photos to close.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    max_votes = max(
        votes_by_entry.get(photo_id, 0)
        for photo_id in range(1, entry_counter + 1)
    )

    results_text = build_results_text("🔒 PHOTO CONTEST CLOSED")
    winner_channel = bot.get_channel(WEEKLY_WINNER_CHANNEL_ID)

    if max_votes == 0:
        contest_phase = "closed"
        await interaction.followup.send(
            results_text + "\n\n🏆 No winner — no votes were cast.",
            ephemeral=True
        )

        if winner_channel is not None:
            embed = discord.Embed(
                title="🏁 PHOTO CONTEST CLOSED!",
                description=(
                    "🎨 **Theme: " + str(current_theme)
                    + "**\n\nNo winner this time because no votes were cast."
                )
            )
            await winner_channel.send(embed=embed)
        return

    groups = get_podium_groups()
    first_place_group = groups[0]
    first_place_ids = first_place_group["photo_ids"]

    if winner_channel is None:
        await interaction.followup.send(
            "❌ Winners channel was not found. The contest was NOT closed.",
            ephemeral=True
        )
        return

    # Copy winning image bytes BEFORE closing/resetting anything.
    copied_files = []
    for photo_id in first_place_ids:
        winner_file = await copy_photo_file(photo_id)
        if winner_file is None:
            await interaction.followup.send(
                "❌ Photo #" + str(photo_id)
                + " could not be copied to the winners channel.\n"
                "The contest was NOT closed, so the original photos are still safe.",
                ephemeral=True
            )
            return
        copied_files.append((photo_id, winner_file))

    podium_text = build_podium_description(groups)

    if len(first_place_ids) == 1:
        photo_id, winner_file = copied_files[0]
        submitter = entry_submitters.get(photo_id)

        winner_ping = (
            "🎉 Congratulations <@" + str(submitter["user_id"]) + ">!"
            if submitter is not None
            else "🎉 Congratulations!"
        )

        embed = discord.Embed(
            title="🏆 PHOTO CONTEST RESULTS!",
            description=(
                "🎨 **Theme: " + str(current_theme) + "**\n\n" + podium_text
            )
        )
        embed.set_image(url="attachment://" + winner_file.filename)
        embed.set_footer(text="Winning photo: Photo #" + str(photo_id))

        try:
            await winner_channel.send(
                content=winner_ping,
                embed=embed,
                file=winner_file,
                allowed_mentions=discord.AllowedMentions(
                    users=True, roles=False, everyone=False
                )
            )
        except discord.HTTPException:
            await interaction.followup.send(
                "❌ The winning photo could not be archived. "
                "The contest was NOT closed.",
                ephemeral=True
            )
            return

    else:
        mentions = []
        for photo_id in first_place_ids:
            submitter = entry_submitters.get(photo_id)
            if submitter is not None:
                mentions.append("<@" + str(submitter["user_id"]) + ">")

        winner_ping = (
            "🎉 Congratulations " + " & ".join(mentions) + "!"
            if mentions
            else "🎉 Congratulations to the winners!"
        )

        summary_embed = discord.Embed(
            title="🏆 PHOTO CONTEST RESULTS!",
            description=(
                "🎨 **Theme: " + str(current_theme) + "**\n\n"
                + podium_text + "\n\n⚖️ **Tie for 1st place!**"
            )
        )

        try:
            await winner_channel.send(
                content=winner_ping,
                embed=summary_embed,
                allowed_mentions=discord.AllowedMentions(
                    users=True, roles=False, everyone=False
                )
            )

            for photo_id, winner_file in copied_files:
                photo_embed = discord.Embed(
                    title="🥇 TIED WINNING PHOTO — Photo #" + str(photo_id)
                )
                photo_embed.set_image(url="attachment://" + winner_file.filename)
                photo_embed.set_footer(text="Winning photo: Photo #" + str(photo_id))

                await winner_channel.send(
                    embed=photo_embed,
                    file=winner_file
                )
        except discord.HTTPException:
            await interaction.followup.send(
                "❌ One or more winning photos could not be archived. "
                "The contest was NOT closed.",
                ephemeral=True
            )
            return

    contest_phase = "closed"

    if len(first_place_ids) == 1:
        admin_winner_text = (
            "\n\n🏆 Winner: Photo #" + str(first_place_ids[0])
            + " with " + str(first_place_group["votes"]) + " vote(s)!"
        )
    else:
        admin_winner_text = (
            "\n\n🏆 Tie for 1st: Photos "
            + ", ".join("#" + str(x) for x in first_place_ids)
            + " with " + str(first_place_group["votes"]) + " vote(s) each!"
        )

    await interaction.followup.send(
        results_text + admin_winner_text
        + "\n\n✅ Winning photo"
        + ("s were" if len(first_place_ids) > 1 else " was")
        + " copied permanently to the winners channel.",
        ephemeral=True
    )


@bot.tree.command(name="newcontest", description="Start a new photo contest")
@discord.app_commands.describe(theme="Theme for the new photo contest")
async def newcontest(interaction: discord.Interaction, theme: str):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ Only administrators can start a new contest.", ephemeral=True
        )
        return

    theme = theme.strip()
    if not theme:
        await interaction.response.send_message(
            "❌ Please enter a contest theme.", ephemeral=True
        )
        return

    warning = (
        "⚠️ START A NEW PHOTO CONTEST?\n\n"
        "🎨 Theme: **" + theme + "**\n\n"
        "This will delete all photo posts and old contest announcements "
        "from the previous contest. The rules post will stay in the channel.\n\n"
        "Photo numbers, votes, and the submitter list will also be reset.\n\n"
        "🏆 Winning photos already copied to the winners channel will stay there.\n\n"
        "📸 The new contest will begin in the SUBMISSIONS phase.\n"
        "⏰ Submissions will run for 5 days.\n"
        "🗳️ Voting will then run for 2 days.\n"
        "🗳️ Voting must still be opened manually with /startvoting.\n"
        "🏆 The contest must still be closed manually with /closecontest.\n\n"
        "🗑️ Deleted contest posts cannot be restored."
    )

    await interaction.response.send_message(
        warning,
        view=NewContestConfirmView(interaction.user.id, theme),
        ephemeral=True
    )


TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("DISCORD_TOKEN is not set")

bot.run(TOKEN)
