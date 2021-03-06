#!/usr/bin/env python

from irclib import Event
from moobot_module import MooBotModule
from handler import Handler
handler_list = ["decodeUtf8"]

# auto decode utf-8
class decodeUtf8(MooBotModule):
	def __init__(self):
		self.regex = ""
		import re
		utf8char = "(?:[\xE0-\xEF][\x80-\xBF]{2})"
		utfregex = re.compile("%s%s" % (utf8char, utf8char))
		gbkchar = "(?:[\x7F-\xFE][\x7F-\xFE])"
		gb2312regex = re.compile("(?:^|[\x01-\x7E])%s%s" % (gbkchar, gbkchar))

		self.translations = {
		                    # for GB* connections
		                    "GBK":      (False, utfregex, "UTF8"),
		                    "GB18030":  (False, utfregex, "UTF8"),
		                    "GB2312":   (False, utfregex, "UTF8"),
		                    # for UTF8 connections
		                    "UTF8":     (True,  gb2312regex, "GB2312"),
		                    }

		self.type = Handler.GLOBAL
		self.priority = 100

	def handler(self, **args):
		encoding = args['encoding'].replace('-', '')
		if not self.translations.has_key(encoding):
			return Event("continue", "", "")
		(skipmatch, regex, fromencoding) = self.translations[encoding];

		rawmsg = args['event'].rawdata()
		if len(rawmsg) > 100:
			return Event("continue", "", "")
		if not regex.search(rawmsg):
			return Event("continue", "", "")

		if skipmatch:
			# skip if it match
			try:
				msg = rawmsg.decode(encoding)
				# well, no translation
				return Event("continue", "", "")
			except:
				pass

		try:
			msg = rawmsg.decode(fromencoding)
		except Exception, e:
			self.Debug(e)
			return Event("continue", "", "")

		from irclib import nm_to_n
		msg = "%s said \"%s\" in %s, but we speak %s here" % (nm_to_n(args['source']), msg, fromencoding, args['encoding'])
		return Event("privmsg", "", self.return_to_sender(args), [ msg ])
