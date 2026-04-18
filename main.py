import asyncio
from io import BytesIO
from printer import open_printer
import discord
from PIL import Image, ImageDraw, ImageText, ImageFont
from PIL.BdfFontFile import BdfFontFile
import config
from dotenv import load_dotenv
import os
import logging
from renderer import Renderer

asyncio.set_event_loop(asyncio.new_event_loop())

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
	logger.info(f'ready as {bot.user}')

last_message: discord.Message | None = None

@bot.event
async def on_message(message: discord.Message):
	global last_message
	chain = last_message is not None and message.author == last_message.author
	await renderer.render_message(message, chain)
	last_message = message

if __name__ == '__main__':
	os.chdir(os.path.dirname(__file__))

	logging.basicConfig(format='[%(asctime)s] %(name)s: [%(levelname)s] %(message)s', level='INFO')
	logger = logging.getLogger(__name__)

	load_dotenv()

	with open_printer() as printer:
		renderer = Renderer(printer)
		bot.run(os.getenv('TOKEN') or '')