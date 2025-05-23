# Don't Remove Credit @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot @Tech_VJ
# Ask Doubt on telegram @KingVJ01

import sys
import glob
import importlib
import logging
import logging.config
import pytz
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Load and validate environment variables
load_dotenv()

def validate_env():
    """Validate required environment variables"""
    required_vars = {
        'TELEGRAM_TOKEN': (str, "Telegram bot token"),
        'LOG_CHANNEL': (int, "Log channel ID"),
        'AUTH_CHANNEL': (int, "Auth channel ID")
    }
    
    missing = []
    invalid = []
    
    for var, (var_type, desc) in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing.append(f"{var} ({desc})")
            continue
            
        try:
            if var_type is int:
                int(value)
        except ValueError:
            invalid.append(f"{var} must be {var_type.__name__}")
    
    if missing or invalid:
        error_msg = []
        if missing:
            error_msg.append("Missing required variables:\n- " + "\n- ".join(missing))
        if invalid:
            error_msg.append("Invalid variables:\n- " + "\n- ".join(invalid))
        logging.critical("\n".join(error_msg))
        sys.exit(1)

validate_env()

# Configure logging with sanitized error messages
logging.config.fileConfig('logging.conf')
logging.getLogger().addFilter(lambda record: not any(
    s in str(record.msg).lower() 
    for s in ['token', 'api_key', 'secret']
))
# Logger levels were already set in logging.conf, no need to set again

# Environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
LOG_CHANNEL = int(os.getenv('LOG_CHANNEL'))
AUTH_CHANNEL = int(os.getenv('AUTH_CHANNEL'))
CHANNELS = [int(ch) for ch in os.getenv('CHANNELS', '').split()] if os.getenv('CHANNELS') else []
ON_HEROKU = os.getenv('ON_HEROKU', 'False').lower() == 'true'
CLONE_MODE = os.getenv('CLONE_MODE', 'False').lower() == 'true'
PORT = int(os.getenv('PORT', 8000))

from pyrogram import Client, idle
from database.users_chats_db import db
from utils import temp
from typing import Union, Optional, AsyncGenerator
from Script import script
from datetime import date, datetime
from aiohttp import web
from plugins import web_server
from plugins.clone import restart_bots
from TechVJ.bot import TechVJBot
from TechVJ.util.keepalive import ping_server
from TechVJ.bot.clients import initialize_clients

ppath = "plugins/*.py"
files = glob.glob(ppath)
TechVJBot.start()
loop = asyncio.get_event_loop()

async def start():
    print('\nInitializing Your Bot')
    
    # Rate limiting setup
    from pyrogram.errors import FloodWait
    
    
    async def rate_limited_send(chat_id, text, max_retries=3):
        """Send message with rate limiting"""
        for attempt in range(max_retries):
            try:
                return await TechVJBot.send_message(chat_id=chat_id, text=text)
            except FloodWait as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = e.value + 5
                logging.warning(f"Rate limited. Waiting {wait_time} seconds...")
                await asyncio.sleep(wait_time)
    
    try:
        bot_info = await TechVJBot.get_me()
        await initialize_clients()
        
        # Load plugins
        for name in files:
            try:
                with open(name) as a:
                    patt = Path(a.name)
                    plugin_name = patt.stem.replace(".py", "")
                    plugins_dir = Path(f"plugins/{plugin_name}.py")
                    import_path = f"plugins.{plugin_name}"
                    spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
                    load = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(load)
                    sys.modules[import_path] = load
                    print(f"Tech VJ Imported => {plugin_name}")
            except Exception as e:
                logging.error(f"Failed to load plugin {name}: {str(e)}")

        if ON_HEROKU:
            asyncio.create_task(ping_server())

        # Initialize banned users/chats
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        
        # Bot metadata
        me = await TechVJBot.get_me()
        temp.BOT = TechVJBot
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        
        logging.info(script.LOGO)
        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        time = now.strftime("%H:%M:%S %p")

        # Send startup notifications
        try:
            await rate_limited_send(
                chat_id=LOG_CHANNEL,
                text=script.RESTART_TXT.format(today, time)
            )
        except Exception as e:
            logging.error(f"Failed to send log channel message: {str(e)}")

        for ch in CHANNELS:
            try:
                msg = await rate_limited_send(chat_id=ch, text="**Bot Restarted**")
                await msg.delete()
            except Exception as e:
                logging.error(f"Failed to send channel message to {ch}: {str(e)}")

        try:
            msg = await rate_limited_send(chat_id=AUTH_CHANNEL, text="**Bot Restarted**")
            await msg.delete()
        except Exception as e:
            logging.error(f"Failed to send auth channel message: {str(e)}")

        if CLONE_MODE:
            logging.info("Restarting All Clone Bots...")
            await restart_bots()
            logging.info("Restarted All Clone Bots")

        # Start web server
        app = web.AppRunner(await web_server())
        await app.setup()
        await web.TCPSite(app, "0.0.0.0", PORT).start()
        await idle()

    except Exception as e:
        logging.critical(f"Bot startup failed: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
