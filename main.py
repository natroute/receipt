import asyncio
from io import BytesIO
from printer import Printer
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
	logger.info(f'Ready as {bot.user}')

@bot.event
async def on_message(message: discord.Message):
	printer.print_page(await renderer.render_message(message))

if __name__ == '__main__':
	logging.basicConfig(format='[%(asctime)s] %(name)s: [%(levelname)s] %(message)s', level='INFO')
	logger = logging.getLogger(__name__)

	load_dotenv()
	os.chdir(os.path.dirname(__file__))

	printer = Printer()
	renderer = Renderer(printer.printable_size[0])

	with printer.print_doc():
		bot.run(os.getenv('TOKEN') or '')