import logging
import os
import sys
import json
from typing import Dict, Union, Optional, cast, Any

from ..parsers.json import JSON
try:
	import systemd.journal
	log_adapter :Optional[logging.Logger] = logging.getLogger('slimSMTP')
	if log_adapter:
		log_adapter.addHandler(systemd.journal.JournalHandler())
		log_adapter.setLevel(logging.INFO)
except ModuleNotFoundError:
	log_adapter = None

class Journald:
	@staticmethod
	def log(message :str, level :int = logging.DEBUG) -> bool:
		"""
		Logs a given message with a given level to ``systemd``'s ``journald``.
		"""
		if log_adapter:
			log_adapter.log(level, message)

			return True
		return False


# Found first reference here: https://stackoverflow.com/questions/7445658/how-to-detect-if-the-console-does-support-ansi-escape-codes-in-python
# And re-used this: https://github.com/django/django/blob/master/django/core/management/color.py#L12
def supports_color() -> bool:
	"""
	Return True if the running system's terminal supports color,
	and False otherwise.
	"""
	supported_platform = sys.platform != 'win32' or 'ANSICON' in os.environ

	# isatty is not always implemented, #6223.
	is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
	return supported_platform and is_a_tty


# Heavily influenced by: https://github.com/django/django/blob/ae8338daf34fd746771e0678081999b656177bae/django/utils/termcolors.py#L13
# Color options here: https://askubuntu.com/questions/528928/how-to-do-underline-bold-italic-strikethrough-color-background-and-size-i
def stylize_output(text: str, *opts :str, **kwargs :Union[str, int, Dict[str, Union[str, int]]]) -> str:
	"""
	Adds styling to a text given a set of color arguments.
	"""
	opt_dict = {'bold': '1', 'italic': '3', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}
	color_names = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white')
	foreground = {color_names[x]: '3%s' % x for x in range(8)}
	background = {color_names[x]: '4%s' % x for x in range(8)}
	reset = '0'

	code_list = []
	if text == '' and len(opts) == 1 and opts[0] == 'reset':
		return '\x1b[%sm' % reset

	for k, v in kwargs.items():
		if k == 'fg':
			code_list.append(foreground[str(v)])
		elif k == 'bg':
			code_list.append(background[str(v)])

	for o in opts:
		if o in opt_dict:
			code_list.append(opt_dict[o])

	if 'noreset' not in opts:
		text = '%s\x1b[%sm' % (text or '', reset)

	return '%s%s' % (('\x1b[%sm' % ';'.join(code_list)), text or '')


def log(*args :Any, **kwargs :Union[str, int, Dict[str, Union[str, int]]]) -> None:
	"""
	A wrapper for :class:`Journald`'s ``.log``, but adds color if supported.
	"""
	if len(args) and type(args[0]) == dict:
		args = cast(Any, [json.dumps(args[0], cls=JSON)])

	string = ' '.join([str(x) for x in args])

	# Attempt to colorize the output if supported
	# Insert default colors and override with **kwargs
	if supports_color():
		kwargs = {'fg': 'white', **kwargs}
		string = stylize_output(string, **kwargs)

	Journald.log(string, level=int(str(kwargs.get('level', logging.INFO))))
	
	if kwargs.get('hide_term_output', False) is False:
		sys.stdout.write(f"{string}\n")
		sys.stdout.flush()