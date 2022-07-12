#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position

"""
This Bot uses the Application class to handle the bot and the JobQueue to send
timed messages.

First, a few handler functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""
import json
import os
import logging
import asyncio
import random
from asyncio.subprocess import Process

from telegram import __version__ as TG_VER

from parser import BASE_URL

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from dotenv import load_dotenv

load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

API_TOKEN = os.getenv("API_TOKEN")
PORT = int(os.environ.get('PORT', 5000))
RESERVED_CHARS = ['.', '!', '-', '(', ')']

thunderstorm = u'\U0001F4A8'  # Code: 200's, 900, 901, 902, 905
drizzle = u'\U0001F4A7'  # Code: 300's
rain = u'\U00002614'  # Code: 500's
snowflake = u'\U00002744'  # Code: 600's snowflake
snowman = u'\U000026C4'  # Code: 600's snowman, 903, 906
atmosphere = u'\U0001F301'  # Code: 700's foogy
clearSky = u'\U00002600'  # Code: 800 clear sky
fewClouds = u'\U000026C5'  # Code: 801 sun behind clouds
clouds = u'\U00002601'  # Code: 802-803-804 clouds general
hot = u'\U0001F525'  # Code: 904
defaultEmoji = u'\U0001F300'  # default emojis

emojis = [
    thunderstorm,
    drizzle,
    rain,
    snowflake,
    snowman,
    atmosphere,
    clearSky,
    fewClouds,
    clouds,
    hot,
    defaultEmoji,
]


# Define a few command handlers. These usually take the two arguments update and
# context.
# Best practice would be to replace context with an underscore,
# since context is an unused local variable.
# This being an example and not having context present confusing beginners,
# we decided to have it present as context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    text = f'''
    Hi!
    This bot parses news from {BASE_URL} for current month.
    Use /parse 
    '''
    await update.message.reply_text(text)


async def parse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id

    try:
        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_once(done, 0, chat_id=chat_id, name=str(chat_id))

        text = ""

        if job_removed:
            text = "Old one was removed.\n\n"

        text += "Start parsing... Please wait..."

        await update.effective_message.reply_text(text)

    except Exception:
        await update.effective_message.reply_text("Usage: /parse")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Task successfully cancelled!" if job_removed else "You have no active parsing."
    await update.message.reply_text(text)


def _replace_reserved_chars(text: str) -> str:
    for char in RESERVED_CHARS:
        text = text.replace(char, fr'\{char}')
    return text


def _to_item(data: dict) -> str:
    date = _replace_reserved_chars(data.get('date', ''))
    title = _replace_reserved_chars(data.get('title', ''))
    url = data.get('url', '')
    return f'{date} [{title}]({url})'


async def show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    try:
        with open("data.json", "rt", encoding="utf-8") as file:
            text = '\n'.join(map(_to_item, json.load(file)))
            await update.message.reply_text(text, parse_mode='MarkdownV2')
    except FileNotFoundError:
        await update.effective_message.reply_text("No data found! First you need to run the '/parse' command.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    text = update.message.text
    await update.message.reply_text('echo: ' + text.upper())


async def emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    emoji = random.choice(emojis)
    await update.message.reply_text(emoji)


async def done(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    job = context.job

    try:
        process: Process = await asyncio.create_subprocess_exec('python', 'parser.py')
        print(f'Process pid is: {process.pid}')

        try:
            status_code = await asyncio.wait_for(process.wait(), timeout=30)
            print(f'Status code: {status_code}')
        except asyncio.TimeoutError:
            print('Timed out waiting to finish, terminating...')
            process.terminate()
            status_code = await process.wait()
            print(f'Status code: {status_code}')
        else:
            with open("data.json", "rb") as file:
                await context.bot.send_document(job.chat_id, document=file)
                await context.bot.send_message(job.chat_id, text=f"Done! Use '/show' to see news.")
    except Exception:
        await context.bot.send_message(job.chat_id, text=f"Something went wrong!")


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(API_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler(["start", "help"], start))
    application.add_handler(CommandHandler("parse", parse))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("show", show))
    application.add_handler(MessageHandler(filters.Sticker.ALL, emoji))
    application.add_handler(MessageHandler(filters.TEXT, echo))

    # Run the bot until the user presses Ctrl-C
    # application.run_polling()

    webhook_url = f'https://learn-python-telegram-bot.herokuapp.com/{API_TOKEN}'
    application.run_webhook(listen='0.0.0.0', port=PORT, url_path=API_TOKEN, webhook_url=webhook_url)


if __name__ == "__main__":
    main()
