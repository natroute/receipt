from io import BytesIO
from PIL import Image, ImageFont, ImageText, ImageDraw
import discord
import config
from printer import Printer
from common import Singleton

class Renderer(metaclass=Singleton):
	def __init__(self, width: int):
		self.width = width

		self.font_regular = ImageFont.truetype('fonts/tahoma.ttf', 20)
		self.font_bold = ImageFont.truetype('fonts/tahomabd.ttf', 20)

		self.avatar_pos = config.padding_x, 0
		self.body_pos = config.padding_x + config.avatar_size + config.avatar_body_gap, 0
		self.body_width = self.width - config.padding_x * 2 - config.avatar_size - config.avatar_body_gap

	async def render_message(self, message: discord.Message):
		avatar_data = await message.author.display_avatar.with_format('png').with_size(64).read()
		avatar_im = Image.open(BytesIO(avatar_data))  # pyright: ignore[reportArgumentType]
		avatar_im = avatar_im.convert('L')

		name_text = ImageText.Text(message.author.display_name, font=self.font_bold, mode='RGB')
		name_height = int(name_text.get_bbox((0, 0))[3])

		content_text = ImageText.Text(message.content, font=self.font_regular, mode='RGB')
		content_text.wrap(self.body_width)
		content_height = int(content_text.get_bbox((0, 0))[3])

		body_height = name_height + config.name_content_gap + content_height
		height = max(config.avatar_size, body_height)

		content_pos = self.body_pos[0], name_height + config.name_content_gap

		size = self.width, height + config.gap_y
		im = Image.new('L', size, 255)
		im.paste(avatar_im, self.avatar_pos)

		draw = ImageDraw.Draw(im)

		draw.text(self.body_pos, name_text, fill=0)
		draw.text(content_pos, content_text, fill=0)

		return im