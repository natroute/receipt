from io import BytesIO
from typing import Iterable, cast
from PIL import Image, ImageFont, ImageText, ImageDraw
import discord
import config
from printer import BasePrinter
from common import Singleton
from md_renderer import FontFamily, MdText, md_text
import aiohttp

class Renderer(metaclass=Singleton):
	_printer: BasePrinter
	_width: int

	_font_family: FontFamily

	_avatar_pos: tuple[int, int]
	_body_pos: tuple[int, int]
	_body_width: int

	def __init__(self, printer: BasePrinter):
		self._printer = printer
		self._width = printer.printable_size[0]

		self._font_family = FontFamily(
			regular=ImageFont.truetype('fonts/DejaVuSans.ttf', config.font_size),
			bold=ImageFont.truetype('fonts/DejaVuSans-Bold.ttf', config.font_size),
			italic=ImageFont.truetype('fonts/DejaVuSans-Oblique.ttf', config.font_size),
			bold_italic=ImageFont.truetype('fonts/DejaVuSans-BoldOblique.ttf', config.font_size),
			emoji=ImageFont.truetype('fonts/TwitterColorEmoji-SVGinOT.ttf', config.emoji_font_size),
		)

		self._avatar_pos = config.padding_x, config.avatar_y
		self._body_pos = config.padding_x + config.avatar_size + config.avatar_body_gap, 0
		self._body_width = self._width - config.padding_x * 2 - config.avatar_size - config.avatar_body_gap

	def _get_attachments_height(self, attachments: Iterable[discord.Attachment]):
		height = 0
		for attachment in attachments:
			size = self._get_attachment_size(attachment)
			if size is None: continue
			height += config.body_items_gap + size[1]
		return height

	def _get_attachment_size(self, attachment: discord.Attachment):
		content_type = attachment.content_type
		assert content_type is not None
		if not content_type.startswith('image/'):
			return

		width = attachment.width
		height = attachment.height
		assert width is not None and height is not None

		ratio = width / height

		if ratio < 1:
			return int(width * (self._body_width / height)), self._body_width
		else:
			return self._body_width, int(height * (self._body_width / width))

	async def render_message(self, message: discord.Message, *, chain: bool):
		if not chain:
			avatar_data = await message.author.display_avatar.with_format('png').with_size(64).read()
			avatar_im = Image.open(BytesIO(avatar_data)).convert('1')  # pyright: ignore[reportArgumentType]

			name_text = ImageText.Text(message.author.display_name, font=self._font_family.bold, mode='1')
			name_height = int(name_text.get_bbox((0, 0))[3])
		else:
			name_height = 0

		content_text = md_text(message.content, font_family=self._font_family, width=self._body_width)
		content_height = content_text.size[1]

		attachments_height = self._get_attachments_height(message.attachments)

		if not chain:
			content_y = name_height + config.body_items_gap
		else:
			content_y = 0

		attachments_y = content_y + content_height
		body_height = attachments_y + attachments_height
		if not chain:
			height = max(config.avatar_y + config.avatar_size, body_height) + config.gap_y
		else:
			height = body_height + config.gap_y

		content_pos = self._body_pos[0], (
			name_height + config.body_items_gap
			if not chain
			else 0
		)

		size = self._width, height
		im = Image.new('1', size, 255)
		draw = ImageDraw.Draw(im)
		
		if not chain:
			im.paste(avatar_im, self._avatar_pos)  # pyright: ignore[reportPossiblyUnboundVariable]

		if not chain:
			draw.text(self._body_pos, name_text, fill=0)  # pyright: ignore[reportPossiblyUnboundVariable]

		content_text.draw(draw, content_pos, fill=0)

		attachment_y = attachments_y
		for attachment in message.attachments:
			content_type = attachment.content_type
			assert content_type is not None
			if not content_type.startswith('image/'):
				continue

			size = self._get_attachment_size(attachment)
			assert size is not None

			attachment_im = Image.open(BytesIO(await attachment.read())).resize(size)
			im.paste(attachment_im, (self._body_pos[0], attachment_y))

			attachment_y += config.body_items_gap + size[1]

		# dot to prevent printer cropping
		draw.point((size[0] - 1, size[1] - 1), 0)

		self._printer.print_page_image(im)