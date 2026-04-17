import logging
import win32print
import win32ui
import win32con
from typing import Any
from contextlib import contextmanager
from PIL import Image, ImageWin

HORZRES = 8
VERTRES = 10

logger = logging.getLogger(__name__)

class PrinterDeniedException(BaseException):
	pass

class Printer:
	'''Abstracts a Windows printer.'''

	'''The printable area of a page.'''
	printable_size: tuple[int, int]

	_dc: Any
	_devmode: Any

	def __init__(self, printer_name: str | None = None):
		printer_name = printer_name or self.get_default()
		if input(f'You are about to print on {printer_name!r}. Is that OK? (y/N) ').lower() != 'y':
			raise PrinterDeniedException()

		self._dc = win32ui.CreateDC()
		self._dc.CreatePrinterDC(printer_name)

		printer = win32print.OpenPrinter(printer_name, {'DesiredAccess': win32print.PRINTER_ACCESS_USE})
		properties = win32print.GetPrinter(printer, 2)
		self._devmode = properties['pDevMode']

		self.printable_size = self._dc.GetDeviceCaps(win32con.HORZRES), self._dc.GetDeviceCaps(win32con.VERTRES)

	@staticmethod
	def get_default():
		return win32print.GetDefaultPrinterW()

	@contextmanager
	def print_doc(self):
		logger.info('StartDoc')
		self._dc.StartDoc('', '')
		try:
			yield
		finally:
			logger.info('EndDoc')
			self._dc.EndDoc()

	def print_page(self, im: Image.Image):
		logger.info('StartPage')
		self._dc.StartPage()
		try:
			logger.info(f'Draw: {im!r}')
			dib = ImageWin.Dib(im)
			dib.expose(self._dc.GetHandleOutput())
		finally:
			logger.info('EndPage')
			self._dc.EndPage()