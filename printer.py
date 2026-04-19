from typing import TYPE_CHECKING, ContextManager, Generator, cast, Any

if TYPE_CHECKING:
	from _win32typing import PyCDC, PyDEVMODEW, PyPrinterHANDLE  # pyright: ignore[reportMissingModuleSource]

import os
from types import TracebackType
import logging
import win32print
import win32ui
import win32con
from contextlib import contextmanager
from PIL import Image, ImageWin
from abc import ABC, abstractmethod

HORZRES = 8
VERTRES = 10

logger = logging.getLogger(__name__)
	
def open_printer(*args, **kwargs) -> BasePrinter:
	'''Returns a :cls:`TestPrinter` if the `USE_TEST_PRINTER` environment variable is set to 1 and a :cls:`Printer` otherwise.'''
	return (
		TestPrinter(*args, **kwargs)
		if int(os.getenv('USE_TEST_PRINTER') or False) == 1
		else Printer(*args, **kwargs)
	)

class BasePrinter(ContextManager['BasePrinter'], ABC):
	printable_size: tuple[int, int]

	@abstractmethod
	def __init__(self) -> None: ...

	@abstractmethod
	def print_doc(self) -> ContextManager[None]: ...

	@abstractmethod
	def print_page_empty(self) -> None: ...

	@abstractmethod
	def print_page_image(self, im: Image.Image) -> None: ...

class TestPrinter(BasePrinter):
	'''A mock printer for testing purposes.'''

	printable_size = 500, 500

	def __init__(self):
		pass

	def __enter__(self):
		logger.info('TestPrinter: open')
		return self

	def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None):
		logger.info('TestPrinter: close')
		return False

	@contextmanager
	def print_doc(self):
		logger.info('TestPrinter: start doc')
		try:
			yield
		finally:
			logger.info('TestPrinter: end doc')

	def print_page_image(self, im: Image.Image):
		logger.info('TestPrinter: print page')
		im.show()

	def print_page_empty(self):
		logger.info('TestPrinter: print empty page')

class Printer(BasePrinter):
	'''Abstracts a Windows printer.'''

	name: str
	'''The name of the underlying printer.'''

	printable_size: tuple[int, int]
	'''The printable area of a page.'''

	_dc: PyCDC
	_printer: PyPrinterHANDLE
	_devmode: PyDEVMODEW
	_printing_doc: bool

	def __init__(self, name: str | None = None):
		self.name = name or self.get_default()

	def __enter__(self):
		logger.info(f'Printing on {self.name!r}')
		self._dc = cast(Any, win32ui.CreateDC())
		self._dc.CreatePrinterDC(self.name)

		self._printer = win32print.OpenPrinter(self.name)
		properties = win32print.GetPrinter(self._printer, 2)
		self._devmode = properties['pDevMode']

		self.printable_size = self._dc.GetDeviceCaps(win32con.HORZRES), self._dc.GetDeviceCaps(win32con.VERTRES)
		
		self._printing_doc = False

		return self

	def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None):
		self._dc.DeleteDC()
		win32print.ClosePrinter(self._printer)
		return False

	@staticmethod
	def get_default():
		'''Returns the name of the default printer.'''
		return win32print.GetDefaultPrinterW()

	@contextmanager
	def print_doc(self):
		'''Context manager wrapping StartDoc and EndDoc.'''

		logger.info('StartDoc')
		self._dc.StartDoc('', '')
		self._printing_doc = True
		try:
			yield
		finally:
			logger.info('EndDoc')
			self._dc.EndDoc()
			self._printing_doc = False

	def print_page_empty(self):
		'''Print an empty page. Must be called within :py:meth:`print_doc`.'''
		assert self._printing_doc

		logger.info('StartPage')
		self._dc.StartPage()
		logger.info('EndPage')
		self._dc.EndPage()

	def print_page_image(self, im: Image.Image):
		'''Print a page and draw an image. Must be called within :py:meth:`print_doc`.'''

		assert self._printing_doc

		logger.info('StartPage')
		self._dc.StartPage()
		try:
			logger.info(f'draw: {im!r}')
			dib = ImageWin.Dib(im)
			dib.expose(self._dc.GetHandleOutput())
		finally:
			logger.info('EndPage')
			self._dc.EndPage()