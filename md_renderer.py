'''"Good enough" Markdown text renderer.'''

from argparse import BooleanOptionalAction
from contextlib import contextmanager
from copy import copy
from enum import Flag, auto
from dataclasses import dataclass, field
import emoji
import re
from typing import TYPE_CHECKING, Any, BinaryIO, Literal
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
	from PIL._typing import _Ink

# these are only meant to do an okayish job

_block_md_re_str = r'''
	(?P<block_format>
		^ (?P<block_format_token> \#\#\# | \#\# | \# | >>> | >) \s*
		(?P<block_format_text> .*?) $
	)
'''

_inline_md_re_str = r'''
	(?P<inline_format>
		(?P<inline_format_token> \*\*\* | ___ | \*\* | __ | \* | _ | ~~ | ` | \|\|)
		(?P<inline_format_text> .*?)
		(?P=inline_format_token)
	) |
	(?P<labelled_link>
		\[ (?P<labelled_link_label> .+?) \]
		\( (?P<labelled_link_url> https?://[a-zA-Z0-9\-_/.?&=]{1,}) \)
	) |
	(?P<direct_link> https?://[a-zA-Z0-9\-_/.?&=]{1,}) |
	(?P<text> .)
'''

_md_inline_re = re.compile(_inline_md_re_str, re.M | re.S | re.X)
_md_re = re.compile(f'{_block_md_re_str} | {_inline_md_re_str}', re.M | re.S | re.X)

@dataclass
class FontFamily:
	regular: ImageFont.FreeTypeFont
	bold: ImageFont.FreeTypeFont
	italic: ImageFont.FreeTypeFont
	bold_italic: ImageFont.FreeTypeFont
	emoji: ImageFont.FreeTypeFont

	def get(self, *, bold: bool, italic: bool, emoji: bool = False):
		match (bold, italic, emoji):
			case (False, False, False): return self.regular
			case (True, False, False): return self.bold
			case (False, True, False): return self.italic
			case (True, True, False): return self.bold_italic
			case (_, _, True): return self.emoji

class _GlyphFlag(Flag):
	STRIKETHROUGH = auto()
	UNDERLINE = auto()

@dataclass
class _Glyph:
	char: str
	flags: _GlyphFlag
	font: ImageFont.FreeTypeFont

@dataclass
class _Format:
	bold: bool = False
	italic: bool = False
	strikethrough: bool = False
	underline: bool = False

class _MdToGlyphs:
	glyphs: list[_Glyph]
	links: list[str]
	_font_family: FontFamily
	_format: _Format

	def __init__(self, *, font_family: FontFamily):
		self._font_family = font_family
		self.glyphs = []
		self.links = []
		self._format = _Format()

	def _add_text(self, text: str):
		emoji_starts: set[int] = set()
		emoji_ends: set[int] = set()

		emojis = emoji.analyze(text)
		for token in emojis:
			match = token.value
			assert isinstance(match, emoji.EmojiMatch)
			emoji_starts.add(match.start)
			emoji_ends.add(match.end)

		is_emoji = False
		for i, char in enumerate(text):
			if i in emoji_starts: is_emoji = True
			if i in emoji_ends: is_emoji = False

			flags = _GlyphFlag(0)
			if self._format.strikethrough: flags |= _GlyphFlag.STRIKETHROUGH
			if self._format.underline: flags |= _GlyphFlag.UNDERLINE

			font = self._font_family.get(
				bold=self._format.bold,
				italic=self._format.italic,
				emoji=is_emoji
			)

			self.glyphs.append(_Glyph(char, flags=flags, font=font))

	@contextmanager
	def _use_format(self, **kwargs: Any):
		'''Context manager to temporarily modify the :py:attr:`_format`.'''

		format = self._format
		self._format = copy(format)
		for name, value in kwargs.items():
			setattr(self._format, name, value)

		yield

		self._format = format

	def _add_md(self, md: str, *, inline: bool = False):
		for match in (_md_inline_re if inline else _md_re).finditer(md):
			if not inline and match['block_format'] is not None:
				block_format_text = match['block_format_text']

				match match['block_format_token']:
					case '#' | '##' | '###':
						# TODO: extend FontFamily so we can have multiple sizes here
						with self._use_format(bold=True):
							self._add_md(block_format_text, inline=True)

					case '>' | '>>>':
						self._add_md(block_format_text, inline=True)

			elif match['inline_format']:
				inline_format_text = match['inline_format_text']

				format: dict[str, Literal[True]] | None = None
				match match['inline_format_token']:
					case '***': format = {'bold': True, 'italic': True}
					case '___': format = {'underline': True, 'italic': True}
					case '**': format = {'bold': True}
					case '__': format = {'underline': True}
					case '*' | '_': format = {'italic': True}
					case '~~': format = {'strikethrough': True}
					case '`': self._add_text(inline_format_text)
					case '||': self._add_text('<spoiler>')

				if format is not None:
					with self._use_format(**format):
						self._add_md(inline_format_text, inline=True)

			elif match['labelled_link'] is not None:
				self.links.append(match['labelled_link_url'])
				with self._use_format(underline=True):
					self._add_md(match['labelled_link_label'], inline=True)

			elif match['direct_link'] is not None:
				self.links.append(match['direct_link'])
				self._add_text(match['direct_link'])

			elif match['text'] is not None:
				self._add_text(match['text'])

			else:
				assert False

def _md_to_glyphs(text: str, *, font_family: FontFamily):
	obj = _MdToGlyphs(font_family=font_family)
	obj._add_md(text)
	return obj.glyphs, obj.links

@dataclass
class MdText:
	_glyphs_xys: list[tuple[_Glyph, tuple[int, int]]]
	size: tuple[int, int]
	links: list[str] = field(default_factory=list)

	def draw(self, draw: ImageDraw.ImageDraw, xy: tuple[int, int], fill: _Ink):
		x, y = xy

		for glyph, glyph_xy in self._glyphs_xys:
			glyph_x, glyph_y = glyph_xy
			glyph_x += x
			glyph_y += y

			def draw_line(offset: int):
				line_y = glyph_y + offset
				length = glyph.font.getlength(glyph.char)
				draw.line([(glyph_x, line_y), (glyph_x + length, line_y)], fill=fill, width=1)

			draw.text((glyph_x, glyph_y), glyph.char, fill=fill, font=glyph.font, anchor='la')

			if glyph.flags & _GlyphFlag.STRIKETHROUGH:
				draw_line(int(glyph.font.size * 0.7))
			if glyph.flags & _GlyphFlag.UNDERLINE:
				draw_line(int(glyph.font.size) + 2)

def _position_glyphs(glyphs: list[_Glyph], *, width: int, line_height_scale: float):
	'''Position a list of glyphs, wrapping to the given width.'''

	# this function is designed very badly. in fact, it probably shouldn't be one function
	# if you are willing to improve it and are able to succeed, i am open to pull requests
	# but i am neither of those two things

	# a word is the unit of wrapping
	# for the purposes of this system, whitespace characters are individual words

	# list of (start, end) ranges of words in `glyphs`
	word_spans: list[tuple[int, int]] = []

	word_start = 0
	for i, glyph in enumerate(glyphs):
		if i == 0: continue

		# for spaces, always start a new span
		if glyph.char.isspace():
			word_spans.append((word_start, i - 1))
			word_start = i

		# for non-spaces, start a new span if the glyph before this was a space
		else:
			if not glyphs[i - 1].char.isspace(): continue
			word_spans.append((word_start, i - 1))
			word_start = i

	# add the final span
	word_spans.append((word_start, len(glyphs) - 1))

	# list of (word_glyphs, word_width), each item in glyphs is (glyph, glyph_width)
	words: list[tuple[list[tuple[_Glyph, int]], int]] = []
	for start, end in word_spans:
		word_width = 0
		word: list[tuple[_Glyph, int]] = []

		word_glyphs = glyphs[start : end + 1]
		for i, glyph in enumerate(word_glyphs):
			# account for kerning, only if the next character exists and is in the same font
			next_char = ''
			if i != len(word_glyphs) - 1:
				next_glyph = word_glyphs[i + 1]
				if glyph.font is next_glyph.font:
					next_char = next_glyph.char

			glyph_width = int(
				glyph.font.getlength(glyph.char + next_char) -
				glyph.font.getlength(next_char)
			)

			word_width += glyph_width

			word.append((glyph, glyph_width))

		words.append((word, word_width))

	glyphs_xys: list[tuple[_Glyph, tuple[int, int]]] = []
	x = 0
	y = 0
	line_height = 0

	def new_line():
		nonlocal x, y, line_height
		x = 0
		y += line_height * line_height_scale
		line_height = 0

	for word_glyphs_offsets, word_width in words:
		if width != 0 and x + word_width > width:
			new_line()

		for glyph, glyph_width in word_glyphs_offsets:
			line_height = max(line_height, int(glyph.font.getbbox(glyph.char)[3]))

			# new line if this is a newline (wow) or if the word so far is too big to fit in the line
			if glyph.char == '\n' or width != 0 and x + glyph_width > width:
				new_line()

				# do not add the characters if this is a space
				if glyph.char.isspace(): continue
			
			glyphs_xys.append((glyph, (x, y)))
			x += glyph_width

	return MdText(_glyphs_xys=glyphs_xys, size=(width, y + line_height))

def md_text(text: str, *, font_family: FontFamily, width: int = 0, line_height_scale: float = 1):
	glyphs, links = _md_to_glyphs(text, font_family=font_family)
	obj = _position_glyphs(glyphs, width=width, line_height_scale=line_height_scale)
	obj.links = links
	return obj