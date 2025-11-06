import os
import requests
import asyncio
from dotenv import load_dotenv
from gofile import upload_file
from telethon import TelegramClient, events, Button

load_dotenv()

API_ID = int(os.environ.get("API_ID", ""))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

Bot = TelegramClient("gofile-bot", API_ID, API_HASH)

INSTRUCTIONS = """
I am a gofile uploader telegram bot. \
You can upload files to gofile.io with command.

With media:
    Normal:
        `/upload`
    With token:
        `/upload token`
    With folder id:
        `/upload token folderid`

Using Link:
    Normal:
        `/upload url`
    With token:
        `/upload url token`
    With folder id:
        `/upload url token folderid`
"""


@Bot.on(events.NewMessage(pattern=r"^/start(?:$|\s)"))
async def start_handler(event):
    if not event.is_private:
        return
    await event.reply(
        f"Hello {event.sender.first_name}," + INSTRUCTIONS,
        link_preview=False,
        parse_mode="md",
        buttons=[
            [Button.url("Source Code", "https://github.com/fayasnoushad/gofile-bot")]
        ],
    )


@Bot.on(events.NewMessage(pattern=r"^/upload(?:$|\s).*"))
async def upload_handler(event):
    if not event.is_private:
        return

    status = await event.reply("`Processing...`", parse_mode="md", link_preview=False)

    raw = event.raw_text or ""
    text = raw.replace("\n", " ").strip()
    url = None
    token = None
    folderId = None

    # If there are args after /upload
    if " " in text:
        # remove the command itself
        text = text.split(" ", 1)[1].strip()
        # If the user replied to a message, then args are token and/or folderId
        if event.is_reply:
            if " " in text:
                token, folderId = text.split(" ", 1)
            else:
                token = text or None
        else:
            # Not a reply: first arg should be url (then optional token, folderId)
            parts = text.split()
            if len(parts) == 1:
                url = parts[0]
            elif len(parts) == 2:
                url, token = parts
            else:
                url, token, folderId = parts[0], parts[1], parts[2]

            if url and not (url.startswith("http://") or url.startswith("https://")):
                await status.edit("Error :- `url is wrong`")
                return
    elif not event.is_reply:
        await status.edit("Error :- `downloadable media or url not found`")
        return

    try:
        await status.edit("`Downloading...`")

        if url:
            response = requests.get(url, timeout=60)
            # try to derive filename from URL (fallback to 'downloaded_file')
            file_name = url.split("/")[-1] or "downloaded_file"
            # if query params present, remove them
            file_name = file_name.split("?")[0]
            with open(file_name, "wb") as file:
                file.write(response.content)
            media = file_name
        else:
            # reply message download
            reply_msg = await event.get_reply_message()
            if not reply_msg:
                await status.edit("Error :- `no replied message found to download`")
                return
            media = await Bot.download_media(reply_msg)
            if not media:
                await status.edit("Error :- `failed to download media`")
                return

        await status.edit("`Downloaded Successfully`")

        await status.edit("`Uploading...`")
        # call gofile upload library (same signature you used)
        response = upload_file(file_path=str(media), token=token, folderId=folderId)
        await status.edit("`Uploading Successfully`")

        # try to remove local file
        try:
            os.remove(media)
        except:
            pass

    except Exception as error:
        await status.edit(f"Error :- `{error}`", parse_mode="md", link_preview=False)
        return

    # Build result text
    text = f"**File Name:** `{response.get('name')}`\n"
    text += f"**File ID:** `{response.get('id')}`\n"
    text += f"**Parent Folder Code:** `{response.get('parentFolderCode')}`\n"
    text += f"**Guest Token:** `{response.get('guestToken')}`\n"
    text += f"**md5:** `{response.get('md5')}`\n"
    text += f"**Download Page:** `{response.get('downloadPage')}`"

    link = response.get("downloadPage")
    buttons = [
        [
            Button.url("Open Link", link),
            Button.url("Share Link", f"https://telegram.me/share/url?url={link}"),
        ],
        [
            Button.url("Feedback", "https://telegram.me/FayasNoushad"),
        ],
    ]

    await status.edit(text, buttons=buttons)


async def main():
    print("Starting bot...")
    await Bot.start(bot_token=BOT_TOKEN)  # type: ignore
    print("Bot is now running!")
    await Bot.run_until_disconnected()  # type: ignore


if __name__ == "__main__":
    asyncio.run(main())
