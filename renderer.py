import asyncio
from io import BytesIO
from typing import cast
from PIL import Image, ImageFont, ImageText, ImageDraw
import discord
import config
from printer import Printer
from common import Singleton

class Renderer(metaclass=Singleton):
	def __init__(self, width: int):
		self.width = width

		self.font_regular = ImageFont.truetype('fonts/tahoma.ttf', config.font_size)
		self.font_bold = ImageFont.truetype('fonts/tahomabd.ttf', config.font_size)

		self.avatar_pos = config.padding_x, 0
		self.body_pos = config.padding_x + config.avatar_size + config.avatar_body_gap, 0
		self.body_width = self.width - config.padding_x * 2 - config.avatar_size - config.avatar_body_gap

	async def render_message(self, printer: Printer, message: discord.Message, chain: bool):
		if not chain:
			avatar_data = await message.author.display_avatar.with_format('png').with_size(64).read()
			avatar_im = Image.open(BytesIO(avatar_data)).convert('1')  # pyright: ignore[reportArgumentType]

			name_text = ImageText.Text(message.author.display_name, font=self.font_bold, mode='RGB')
			name_height = int(name_text.get_bbox((0, 0))[3])
		else:
			name_height = 0

		content_text = ImageText.Text(message.content, font=self.font_regular, mode='RGB')
		content_text.wrap(self.body_width)
		content_height = int(content_text.get_bbox((0, 0))[3])

		body_height = name_height + config.name_content_gap + content_height
		height = max(config.avatar_size, body_height)

		content_pos = self.body_pos[0], name_height + config.name_content_gap

		size = self.width, height + config.gap_y
		im = Image.new('1', size, 255)
		
		if not chain:
			im.paste(avatar_im, self.avatar_pos)  # pyright: ignore[reportPossiblyUnboundVariable]

		draw = ImageDraw.Draw(im)
		if not chain:
			draw.text(self.body_pos, name_text, fill=0)  # pyright: ignore[reportPossiblyUnboundVariable]
		draw.text(content_pos, content_text, fill=0)

		# dot to prevent printer cropping
		draw.point((0, height - 1), 20)

		printer.print_page_image(im)
		for _ in range(config.filler_page_count):
			printer.print_page_empty()