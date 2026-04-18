from io import BytesIO
from typing import Iterable, cast
from PIL import Image, ImageFont, ImageText, ImageDraw
import discord
import config
from printer import BasePrinter
from common import Singleton

class Renderer(metaclass=Singleton):
	def __init__(self, printer: BasePrinter):
		self.printer = printer
		self.width = printer.printable_size[0]

		self.font_regular = ImageFont.truetype('fonts/tahoma.ttf', config.font_size)
		self.font_bold = ImageFont.truetype('fonts/tahomabd.ttf', config.font_size)

		self.avatar_pos = config.padding_x, config.avatar_y
		self.body_pos = config.padding_x + config.avatar_size + config.body_items_gap, 0
		self.body_width = self.width - config.padding_x * 2 - config.avatar_size - config.body_items_gap

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
			return int(width * (self.body_width / height)), self.body_width
		else:
			return self.body_width, int(height * (self.body_width / width))

	async def render_message(self, message: discord.Message, chain: bool):
		if not chain:
			avatar_data = await message.author.display_avatar.with_format('png').with_size(64).read()
			avatar_im = Image.open(BytesIO(avatar_data)).convert('1')  # pyright: ignore[reportArgumentType]

			name_text = ImageText.Text(message.author.display_name, font=self.font_bold, mode='1')
			name_height = int(name_text.get_bbox((0, 0))[3])
		else:
			name_height = 0

		content_text = ImageText.Text(message.content, font=self.font_regular, mode='1')
		content_text.wrap(self.body_width)
		content_height = int(content_text.get_bbox((0, 0))[3])

		attachments_height = self._get_attachments_height(message.attachments)

		if not chain:
			content_y = name_height + config.name_content_gap
		else:
			content_y = 0

		attachments_y = content_y + content_height
		body_height = attachments_y + attachments_height + config.gap_y
		if not chain:
			height = max(config.avatar_y + config.avatar_size, body_height)
		else:
			height = body_height

		content_pos = self.body_pos[0], (
			name_height + config.name_content_gap
			if not chain
			else 0
		)

		size = self.width, height
		im = Image.new('1', size, 255)
		draw = ImageDraw.Draw(im)
		
		if not chain:
			im.paste(avatar_im, self.avatar_pos)  # pyright: ignore[reportPossiblyUnboundVariable]

		if not chain:
			draw.text(self.body_pos, name_text, fill=0)  # pyright: ignore[reportPossiblyUnboundVariable]
		draw.text(content_pos, content_text, fill=0)

		attachment_y = attachments_y
		for attachment in message.attachments:
			content_type = attachment.content_type
			assert content_type is not None
			if not content_type.startswith('image/'):
				continue

			size = self._get_attachment_size(attachment)
			assert size is not None

			attachment_im = Image.open(BytesIO(await attachment.read())).resize(size)
			im.paste(attachment_im, (self.body_pos[0], attachment_y))

			attachment_y += config.body_items_gap + size[1]

		# dot to prevent printer cropping
		draw.point((size[0] - 1, size[1] - 1), 0)

		self.printer.print_page_image(im)
		for _ in range(config.filler_page_count): self.printer.print_page_empty()