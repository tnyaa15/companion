import logging
from pathlib import Path

import discord

log = logging.getLogger("companion.discord")
MEDIA_DIR = Path(__file__).resolve().parent.parent / "media"
MEDIA_EXTENSIONS = {
    ".gif",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp4",
    ".png",
    ".webm",
    ".webp",
}
DISCORD_MESSAGE_LIMIT = 1900


def split_message(text: str) -> list[str]:
    chunks = []
    remaining = text.strip()
    while len(remaining) > DISCORD_MESSAGE_LIMIT:
        split_at = remaining.rfind(" ", 0, DISCORD_MESSAGE_LIMIT)
        if split_at < DISCORD_MESSAGE_LIMIT // 2:
            split_at = DISCORD_MESSAGE_LIMIT
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


class DiscordCompanionClient(discord.Client):
    def __init__(self, companion, owner_id: int):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.companion = companion
        self.owner_id = owner_id

    async def on_ready(self):
        log.info("Discord companion connected as %s", self.user)

    async def send_to_owner(self, text: str) -> None:
        user = self.get_user(self.owner_id)
        if user is None:
            user = await self.fetch_user(self.owner_id)
        for chunk in split_message(text):
            await user.send(chunk)

    async def on_message(self, message: discord.Message):
        if message.author.bot or message.author.id != self.owner_id:
            return

        content = (message.content or "").strip()
        if content.startswith("!sendmedia"):
            await self.send_media_command(message, content)
            return
        if content == "!help":
            await message.channel.send(
                "just message me normally. use !sendmedia <filename> to send a "
                "file from the local media folder."
            )
            return

        if message.attachments:
            filenames = ", ".join(attachment.filename for attachment in message.attachments)
            if not content:
                await message.channel.send(
                    f"i got {filenames}, but image/video understanding isn't connected yet."
                )
                return
            content += f"\n[Attached files: {filenames}. Their contents aren't available to you.]"
        if not content:
            return

        async with message.channel.typing():
            reply = await self.companion.generate_reply(content)
        if not reply:
            await message.channel.send("my brain lagged for a sec, say that again?")
            return
        for chunk in split_message(reply):
            await message.channel.send(chunk)

    async def send_media_command(self, message: discord.Message, content: str) -> None:
        parts = content.split(maxsplit=1)
        if len(parts) != 2:
            await message.channel.send("use !sendmedia followed by a filename.")
            return
        filename = parts[1].strip()
        media_root = MEDIA_DIR.resolve()
        path = (media_root / filename).resolve()
        if path.parent != media_root or path.suffix.lower() not in MEDIA_EXTENSIONS:
            await message.channel.send("use an image or video filename from the media folder.")
            return
        if not path.is_file():
            await message.channel.send("i couldn't find that file in the media folder.")
            return
        try:
            await message.channel.send(file=discord.File(path, filename=path.name))
        except discord.HTTPException:
            log.exception("Discord media upload failed")
            await message.channel.send("discord couldn't upload that file just now.")