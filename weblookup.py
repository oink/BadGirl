#!/usr/bin/env python

# Copyright (c) 2002 Daniel DiPaolo, et. al.
# Copyright (C) 2005 by baa
# Copyright (C) 2005 by FKtPp
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

import httplib
from moobot_module import MooBotModule
handler_list = ["slashdot", "google", "kernelStatus", "dict", "acronym",
		"babelfish", "debpackage", "debfile", "foldoc", "pgpkey",
		"geekquote"]

class slashdot(MooBotModule):
	def __init__(self):
		self.regex = "^slashdot$"

	def handler(self, **args):
		"Gets headlines from slashdot.org"
		from irclib import Event
		target = self.return_to_sender(args)

		connect = httplib.HTTPConnection('slashdot.org', 80)
		connect.request("GET", "/slashdot.rdf")
		response = connect.getresponse()
		if response.status != 200:
			msg = "%d: %s" % (response.status, response.reason)
			self.debug(msg)
			return Event("privmsg", "", target, [msg])
		else:
			import re
			# Do the parsing here
			listing = response.read()
			listing = listing.split("\n")
			regex = re.compile("^<title>.*</title>$", re.IGNORECASE)
			match_count = 0
			articles = []
			for item in listing:
				if regex.match(item):
					match_count += 1
					# ignore the first two
					if match_count != 1 and match_count != 2:
						item = re.sub("</*title>", "", item)
						articles.append(item)
			# Drop the last one as well
			articles = articles[:len(articles)-1]
			match_count -= 3
			# now lets make it into a big string
			string = "Slashdot Headlines (" + str(match_count) + " shown): "
			for article in articles:
				string += article + " ;; "
			# and send it back
			string = string[:len(string)-4] + "."
			string = string.replace("amp;", "")
			connect.close()
			return Event("privmsg", "", target, [string])

class google(MooBotModule):
	"Does a search on google and returns the first 5 hits"
	def __init__(self):
		self.regex = "^google for .+"

	def handler(self, **args):
		from irclib import Event
		import string
		self.return_to_sender(args)

		search_terms = args["text"].split(" ")[3:]
		search_request = "/ie?hl=zh-CN&oe=UTF-8&ie=UTF-8&q="
		# the resulting output so much nicer
		search_request += string.join(search_terms, "+").encode("UTF-8", 'replace')
		connect = httplib.HTTPConnection('www.google.com', 80)
		headers = {"User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0)"}
		connect.request("GET", search_request, None, headers)

		try:
			response = connect.getresponse()
		except:
			msg = "error"
			return Event("privmsg", "", target, [msg])

		if response.status != 200:
			msg = str(response.status) + ": " + response.reason
			self.debug(msg)
			return Event("privmsg", "", target, [msg])
		else:
			listing = response.read().decode("UTF-8", 'replace')
		urls=[]
		for i in listing.split():
			if string.find(i, "href=http://") >= 0:
				url = i[:string.find(i, ">")]
				url = url[5:]
				urls.append(url)
		line = "Google says \"" + string.join(search_terms) + "\" is at: "
		count=0
		for url in urls:
			count += 1
			if count <= 5:
				line += url + " "
		return Event("privmsg", "", self.return_to_sender(args), [ line ])

class kernelStatus(MooBotModule):
	def __init__(self):
		self.regex = "^kernel$"

	def handler(self, **args):
		"""
		gets kernel status
		"""
		# self.debug("kernelStatus")
		import string
		connect=httplib.HTTPConnection("www.kernel.org", 80)
		connect.request('GET', '/kdist/finger_banner')
		response = connect.getresponse()
		if response.status != 200:
			msg = '%d: %s' % (response.status, response.reason)
			self.debug(msg)
			return Event("privmsg", "", target, [msg])
		text = response.read()

		# Extract just the version numbers, instead of flooding
		# the channel with everything.
		result = ""
		for line in text.split("\n"):
			if len(line.split(":")) > 1:
				line = line.split(" ", 2)[2]
				version = '%s ;; ' % line.split(":")[1].strip()
				line = line.split("of", 2)[0]
				line = line.split("for", 2)[0]
				line = line.split("to", 2)[0]
				result += '%s: %s' % (line.strip(), version)

		from irclib import Event
		target = self.return_to_sender(args)
		return Event("privmsg", "", target, [ result ])


class dict(MooBotModule):
	cache = {}
	cache_old = {}
	def __init__(self):
		import re
		# have problem filtering out `|' character
		self.regex = "^(dict |~)[^~\+\*/\\<>-]+"
		self.rStrip = re.compile("(<.*?>)+")
		self.rWord = re.compile("^<!-- WORD", re.I)
		self.rGif = re.compile("/gif/([\\w_]+)\\.gif", re.I)
		self.rBody = re.compile("^<!-- BODY", re.I)
		self.ymap = {"slash": "/", "quote": "'", "_e_": "2", "_a": "a:", "int": "S"}
		self.cmap = {"\\\\": "\\", "5": "'", "E": "2"}
		# �μ��ļ�ͷ coding
		# �°汾�ſ����� u"GBK"
		self.rNx = re.compile("�Ҳ���������ѯ��".decode("gbk"))
		self.rCtoE = re.compile("������Ӣ�ʵ�(.*)".decode("gbk"), re.M)
		self.rBlue = re.compile("<font color=blue>", re.I)
		self.rEtoC = re.compile("����Ӣ���ʵ�</div>(.*?)</div>".decode("gbk"), re.S)
		self.rSpell = re.compile("str2img\('([^']+)", re.I)
		self.rExpl = re.compile(u'class="explain_(?:attr|item)">(.*)', re.I)
		self.ciba_failed = 1
		self.rSearch = re.compile(u'^[^*?_%]{2,}[*?_%]')

 	def handler(self, **args):
 		from irclib import Event
		import dict
 		target = self.return_to_sender(args)
		if args["text"].split()[1][0][0] == '~':
			word = " ".join(args["text"].split()[1:])[1:]
		else:
			word = " ".join(args["text"].split()[2:])

		# simple yet powerful garbage collection
		# better not use time
		if len(self.cache) > 500:
			self.cache_old = self.cache
			self.cache = {}

		if self.rSearch.match(word):
			words = dict.search(word)
			self.Debug(words)
			if not words:
				result = False
			elif len(words) == 1:
				result = words[0] + ', ' + dict.lookup(words[0])
			else:
				result = "Found %d" % len(words)
				if len(words) >= dict.maxsearch:
					result += " or more"
				result += ": " + ", ".join(words)

			if not result:
				result = "not found"
		else:
			result = dict.lookup(word)

		if result:
			result = word + ": " + result
		elif self.cache.has_key(word):
			result = self.cache[word]
		elif self.cache_old.has_key(word):
			self.cache[word] = self.cache_old[word]
			result = self.cache[word]
		else:
			if self.ciba_failed <= 0:
 				result = self.lookup_ciba(word)
				if result == "error":
					self.ciba_failed = 5
 					result = self.lookup_yahoo(word)
			else:
 				result = self.lookup_yahoo(word)
				self.ciba_failed = self.ciba_failed - 1
			result = result.replace("&lt;","<").replace("&gt;",">")
 			if len(result) == 0:
 				result = "Could not find definition for " + word
			elif result == "error":
				pass
			else:
				self.cache[word] = result

 		return Event("privmsg", "", target, [ result ])

	def lookup_ciba(self, word):
		connect = httplib.HTTPConnection('cb.kingsoft.com', 80)
		connect.request("GET", "/search?s=%s&t=word&lang=utf-8" % (word.encode("UTF-8"), ))
		response = connect.getresponse()
		if response.status != 200:
			msg = "%d:%s" % (response.status, response.reason)
			loc = response.getheader("location")
			self.debug("dict word(%s) err(%s) loc(%s)" % (word, msg, loc))
			return "error"
		else:
			# Do the parsing here
			html = response.read().decode("UTF-8", "ignore")
			if self.rNx.search(html):
				return ""
	
			m = self.rCtoE.search(html)
			if m:
				m = self.rBlue.split(m.group(1))[1:]
				words = []
				for i in m:
					words.append(i[:i.find("<")])
				return word + ": " + ", ".join(words)
	
			m = self.rEtoC.search(html)
			if m:
				html = m.group(1)
				result = word + ":"
				m = self.rSpell.search(html)
				if m:
					spell = m.group(1)
					for k in self.cmap:
						spell = spell.replace(k, self.cmap[k])
					result += " /" + spell + "/"
				m = self.rExpl.search(html)
				if m:
					html = m.group(1)
					html = self.rStrip.sub(" ", html)
					result += " "
					result += html
				return result
				
			return ""

	def lookup_yahoo(self, word):
		connect = httplib.HTTPConnection('cn.yahoo.com', 80)
		w = word.encode("GBK") # better than error
		connect.request("GET", "/dictionary/result/%s/%s.html" % (w[0], w))
		response = connect.getresponse()
		if response.status != 200:
			msg = "%d:%s" % (response.status, response.reason)
			loc = response.getheader("location")
			import re
			if re.compile("/error").match(loc):
				return ""
			else:
				self.debug("dict word(%s) err(%s) loc(%s)" % (word, msg, loc))
				return ""
		else:
			# Do the parsing here
			listing = response.read().decode("GBK")
			listing = listing.split("\n")
			ibody = 0
			str = word + " "
			for item in listing:
				if self.rWord.match(item):
					for m in self.rGif.finditer(item):
						m = m.group(1)
						if self.ymap.has_key(m):
							m = self.ymap[m]
						str += m
				elif self.rBody.match(item):
					str += self.rStrip.sub("", item) + " "
					ibody += 1
			return str



class babelfish(MooBotModule):
	"Does a search on babelfish.altavista.com and returns the translation"
	# the languages babelfish can do
	languages = {"english" : "en", "chinese" : "zh",
		     "french" : "fr", "german" : "de",
		     "italian" : "it", "japanese" : "ja",
		     "korean" : "ko", "portuguese" : "pt",
		     "russian" : "ru", "spanish" : "es"}
	# the combinations (from_to) that babelfish can translate
	translations =["en_zh", "en_fr", "en_de" , "en_it", "en_ja", "en_ko",
		       "en_pt", "en_es" , "zh_en", "fr_en" , "fr_de", "de_en",
		       "de_fr" , "it_en", "ja_en", "ko_en", "pt_en", "ru_en",
		       "es_en"]

	def __init__(self):
		# the languages babelfish can do
		self.languages = {"english" : "en",
				  "chinese" : "zh",
				  "schinese" : "zh",
				  "tchinese" : "zt",
				  "dutch": "nl",
				  "french" : "fr",
				  "german" : "de",
				  "italian" : "it",
				  "japanese" : "ja",
				  "korean" : "ko",
				  "portuguese" : "pt",
				  "russian" : "ru",
				  "spanish" : "es",
				  "greek": "el"}

		# the combinations (from_to) that babelfish can
		self.translations =["zh_en", "zt_en", "en_zh",
		"en_zt", "en_nl", "en_fr", "en_de", "en_el", "en_it",
		"en_ja", "en_ko", "en_pt", "en_ru", "en_es", "nl_en",
		"nl_fr", "fr_en", "fr_de", "fr_el", "fr_it", "fr_pt",
		"fr_nl", "fr_es", "de_en", "de_fr", "el_en", "el_fr",
		"it_en", "it_fr", "ja_en", "ko_en", "pt_en", "pt_fr",
		"ru_en", "es_en", "es_fr"]
		self.shortcuts = {
			"ec": "en_zh",
			"ce": "zh_en"
			}

		self.regex = "^((babelfish|translate) \w+ to \w+|(%s)\s+.+|babelfish$|translate$)" % ("|".join(self.translations + self.shortcuts.keys()))


	def help(self, args):
		from irclib import Event
		langs = " ".join(self.languages.keys())
		trans = " ".join(self.languages.values())
 		return Event("privmsg", "", self.return_to_sender(args), [
			"Usage: translate <FROM_LANGUAGE> to <TO_LANGUAGE> TEXT\r\nAvailable LANGUAGES are \"%s\"" % (langs)
			+ "\r\nSynonyms: {LN_LN} TEXT\r\nWhere LNs are \"%s\"" % (trans)
			])

	def handler(self, **args):
		from irclib import Event
		import string, re, urllib
		
		tmp = args["text"].split(" ", 2)
		translation_key = tmp[1].lower()
		if len(tmp) != 3:
			return self.help(args)
		request = tmp[2] # chop off the "moobot: babelfish"

		if self.shortcuts.has_key(translation_key):
			if request.find(' ') == -1 and re.compile('^[a-z]+$', re.I).search(request):
				return Event("privmsg", "", self.return_to_sender(args), 
					[ "use: dict " + request + " or ~~" + request])
			translation_key = self.shortcuts[translation_key]
			translation_text = request
		elif translation_key in self.translations:
			translation_text = request
		else:
			froml = request.split()[0].lower() # the source language
							# to get something like "english to spanish foo"
			tol = request.split()[2].lower() # the destination language
			translation_text = " ".join(request.split()[3:]) 
			# The string to translate, it's length wont't be ZERO
			if re.compile("^\s*$").match(translation_text):
				return self.help(args)

			# check if we know the languages they want to use
			if froml not in self.languages.keys() :
				return Event("privmsg", "", self.return_to_sender(args), 
					[ "unknown language: " + froml ])
			if tol not in self.languages.keys():
				return Event("privmsg", "", self.return_to_sender(args), 
					[ "unknown language: " + tol ])

			# the value for the lp= field for the cgi arguments
			translation_key = "%s_%s" % (self.languages[froml], 
				self.languages[tol])

			# make sure the translation_key is one we can use
			if translation_key not in self.translations:
				return Event("privmsg", "", self.return_to_sender(args), 
					[ "Babelfish doesn't know how to do %s to %s" % 
					(froml, tol)])

		translation_text = translation_text.replace("'", "��".decode("gbk"));

		# create the POST body
		params = {"doit": "done", "intl": "1", "tt": "urltext", "trtext": translation_text.encode("UTF-8"), "lp": translation_key}
		headers = {"Content-type": "application/x-www-form-urlencoded",
			   "User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0)",
			   "Accept-Encoding": ""}
		# connect, make the reauest
		connect = httplib.HTTPConnection('babelfish.altavista.com', 80)
		connect.request("POST", "/tr", urllib.urlencode(params), headers)
		response = connect.getresponse()
		if response.status != 200: # check for errors
			msg = response.status + ": " + response.reason
			return Event("privmsg", "", self.return_to_sender(args), [msg])
		else:
			listing = response.read().decode("UTF-8", "ignore")
			listing = listing.replace('\n', '') # get rid of newlines
		searchRegex2 = re.compile("<td bgcolor=white class=s><div style=padding:10px;>(.*?)</div></td>")
		match = searchRegex2.search(listing)
		result = match.group(1)
		return Event("privmsg", "", self.return_to_sender(args), 
			[ "Translation: " + result ])

import HTMLParser2 
class debpackage(MooBotModule, HTMLParser2.HTMLParser):
	"""
	Does a package search on http://packages.debian.org and returns top 10 result
	"""
	def __init__(self):
		self.regex="^debpackage .+"
		self.package = ""
		HTMLParser2.HTMLParser.__init__(self)

	def reset(self):
		HTMLParser2.HTMLParser.reset(self)
		self.__max_hit = 10
		self.inner_div = False
		self.in_ul = False
		self.list = "%s:" % self.package
		self.li = 0
		self.li_over = False
		self.after_br = False
		self.block_size = 400
		self.block = 400

	def handler(self, **args):
		import httplib
		from irclib import Event

		target = self.return_to_sender(args)

		## Parse the request
		# A branch can be specified as the first argument, and multiple
		# packages can be requested.
		branches = ['stable', 'testing', 'unstable']

		request = args["text"].split()[2:]
		if request[0] in branches:
			branch = request[0]
			del request[0]
		else:
			branch = None

		# Now, they may have forgotten to specify a package if
		# they provided a branch (the regex will still match)
		if len(request) != 1:
			msg = "Usage: debpackage [stable|testing|unstable] PackageName"
			return Event("privmsg", "", target, [msg])
		else:
			self.package = request[0]

		# Otherwise, request should now contain a list of
		# packages We'll step through them one by one and
		# display them all at once at the end.
		host = "packages.debian.org"
		page = "/cgi-bin/search_packages.pl"
		msg = ""
		# build the request
		cgi_params = \
			"?keywords=%s&searchon=names&version=%s&release=all" % (
				self.package, branch or "all")
		conn = httplib.HTTPConnection(host)
		# self.debug(page + cgi_params)
		conn.request("GET", page + cgi_params)
		response = conn.getresponse()
		if response.status != 200:
			msg = "Bad response from packages.debian.org: %d" % \
				response.status
			return Event("privmsg", "", target, [msg])
		else:
			self.reset()
			self.feed(response.read())
		return Event("privmsg", "", target, [self.list])

	def handle_starttag(self, tag, attrs):
		if tag == "div":
			for a_name, a_value in attrs:
				if a_name == "id" and a_value == "inner":
					self.inner_div = True
		elif tag == "ul" and self.inner_div:
			self.in_ul = True
		elif tag == "li" and self.in_ul:
			self.li += 1
			self.after_br = False
			if self.li <= self.__max_hit:
				if len(self.list) >= self.block:
					self.list += "\n%s:" % self.package
					self.block += self.block_size
				self.list += " =%d=> " % self.li
			else:
				self.li_over = True
		elif tag == "a" and self.in_ul and not self.li_over:
			for a_name, a_value in attrs:
				if a_name == "href":
					self.list += "http://packages.debian.org%s " % a_value
					self.in_a = True
		elif tag == "br" and self.in_ul:
			self.after_br = True

	def handle_endtag(self, tag):
		if tag == "ul":
			self.in_ul = False
		elif tag == "a":
			self.in_a = False

	def handle_data(self, data):
		if self.in_ul:
			if not self.li_over:
				if not self.in_a:
					if not self.after_br:
						self.list += data.strip()

class debfile(MooBotModule, HTMLParser2.HTMLParser):
	"""
	Does a file search on http://packages.debian.org and returns top 10 matched package names
	"""
	def __init__(self):
		self.regex = "^debfile .+"
		self.file = ""
		self.version = ""
		HTMLParser2.HTMLParser.__init__(self)

	def reset(self):
		HTMLParser2.HTMLParser.reset(self)
		self.list = "%s(%s): " % (self.file, self.version)
		self.inner_div = False
		self.after_hr = False
		self.is_result_table = False
		self.in_box = False
		self.hit = 0
		self.__max_hit = 10
		self.over = False
		self.block = 400
		self.block_size = 400

	def handler(self, **args):
		import urllib
		from irclib import Event
		target = self.return_to_sender(args)
		self.version = ['stable', 'testing', 'unstable']
		request = args["text"].split()[2:]
		if request[0] in self.version:
			self.version = request[0]
			del request[0]
		else:
			self.version = "testing"
		if len(request) != 1:
			msg = "Usage: debfile [stable|testing|unstable] filename"
			return Event("privmsg", "", target, [msg])
		self.file = request[0]
		form_action = "http://packages.debian.org/cgi-bin/search_contents.pl?%s"
		form_inputs = urllib.urlencode({"word": self.file,
						"searchmode": "searchfiles",
						"case": "insensitive",
						"version": self.version,
						"architecture": "i386"})
		try:
			result = urllib.urlopen(form_action % form_inputs)
		except Exception, e:
			self.Debug(e)
		self.reset()
		self.feed(result.read())
		return Event("privmsg", "", target, [self.list])

	def handle_starttag(self, tag, attrs):
		if tag == "div":
			for a_name, a_value in attrs:
				if a_name == "id" and a_value == "inner":
					self.inner_div = True
		elif tag == "hr" and self.inner_div:
			self.after_hr = True
		elif tag == "pre" and self.after_hr:
			self.is_result_table = True

	def handle_data(self, data):
		if not self.over:
			if self.is_result_table:
				if '\n' in data:
					data = data.strip()
					if len(self.list)+len(data) >= self.block:
						self.list += "\n%s(%s): " % (self.file, self.version)
						self.block += self.block_size
					self.hit += 1
					if self.hit == self.__max_hit:
						self.over = True
					elif not data == "":
						self.list += "=%d=> " % self.hit
						self.list += data
				else:
					self.list += data.strip()
				if '[' in data:
					self.in_box = True
				elif ']' in data:
					self.in_box = False
				if not self.in_box:
					self.list += " "

	def handle_endtag(self, tag):
		if tag == "pre" and self.after_hr:
			self.is_result_table = False

class acronym(MooBotModule):
	"""
	Does a search on www.acronymfinder.com and returns all definitions
	"""
	def __init__(self):
		self.regex = "^explain [a-zA-Z]+"

	def handler(self, **args):
		from irclib import Event
		import string, re
		target = self.return_to_sender(args)

		search_term = args["text"].split(" ")[2].upper()
		search_request = "/af-query.asp?String=exact&Acronym=%s&Find=Find" % search_term
		connect = httplib.HTTPConnection('www.acronymfinder.com', 80)
		headers = {"User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0)"}
		connect.request("GET", search_request, None, headers)
		response = connect.getresponse()
		if response.status != 200:
			msg = "%d: %s" % (response.status,response.reason)
			self.debug(msg)
			return Event("privmsg", "", target, [msg])
		else:
			listing = response.read().decode("latin1")


		search = re.compile("<td[^>]*><b>%s\s*</b></td>[^<]+<td[^>]*>((?:<b>)?[A-Za-z][^<\n\r]+(?:</b>)?)\s*</td>" % search_term)
		definitions = search.findall(listing)
		if len(definitions) == 0:
			line = "Could not find a definition for " + search_term
		elif len(definitions) == 1:
			line = search_term + " is " + definitions[0]
		else:
			line = search_term + " is one of the following: \"" + string.join(definitions,'", "') + "\""
		line = line.replace("<b>", "\002").replace("</b>", "\002")
		return Event("privmsg", "", self.return_to_sender(args), [ line ])


class foldoc(MooBotModule):
	"""
	Free On-line Dicitionary Of Computing
	"""
	def __init__(self):
		self.regex = "^foldoc .+"

	# Returns the position of the nth element in lst.
	def index(self, lst, element, n=1):
		m = 0
		for i in xrange(len(lst)):
			if lst[i] == element:
				m += 1
				if m == n:
					return i

	def handler(self, **args):
		from irclib import Event
		import urllib2
		import re
		target = self.return_to_sender(args)

		try:
			url = "http://foldoc.doc.ic.ac.uk/foldoc/foldoc.cgi?query=" + args["text"].split()[2]
		except urllib2.URLError:
			return "error connecting to foldoc"
		fd = urllib2.urlopen(url).readlines()
		start = self.index(fd, "<P>\n", 1)
		stop = self.index(fd, "<P>\n", 2)
		descr = " ".join(fd[start:stop])   # Get the base description
		descr = re.sub("\n", "", descr)	# Remove newlines
		descr = re.sub("<.*?>", "", descr) # Remove HTML tags
		descr = re.sub("&.*;", "", descr)  #   "	 "	"
		descr = descr.lstrip() # Remove leading white spaces

		return Event("privmsg", "", target, [descr])

class pgpkey(MooBotModule):
	""" Does a key search on pgp.mit.edu and returns the first 5 hits
	Author: jamessan """
	def __init__(self):
		self.regex = "^pgpkey .+$"

	def handler(self, **args):
		from irclib import Event
		import string
		self.return_to_sender(args)

		import re
		search_terms = args["text"].split(" ")[2:]
		domain = "pgp.mit.edu"
		port=11371
		search_request = "/pks/lookup?op=index&search="
		search_request += string.join(search_terms, "+")
		connect = httplib.HTTPConnection(domain, port)
		connect.request("GET", search_request)
		response = connect.getresponse()
		if response.status != 200:
			msg = str(response.status) + ": " + response.reason
			self.debug(msg)
			return Event("privmsg", "", target, [msg])
		else:
			listing = response.read()
		url="http://" + domain + ':' + `port`
		pgpkeys={}
		pgp = re.compile('pub\s+\d{4}\w/<a'\
			' href="([^"]+)">([^<]+)</a>[^>]+>([^<]+)</a>')
		for i in listing.split('\n'):
			info = pgp.search(i)
			try:
				path, keyid, email = info.groups()
				pgpkeys[keyid]=(email,'%s%s' % (url,path))
			except AttributeError:
				pass
		line = "pgpkey matches for \"" + string.join(search_terms) + "\": "
		count=0
		if len(pgpkeys.keys()) == 0:
			return Event("privmsg", "", self.return_to_sender(args), [ '%s'\
				' 0 matches found' % line ])
		for i in pgpkeys.keys():
			count += 1
			if count <= 5:
				line += pgpkeys[i][0] + " (" + pgpkeys[i][1] + ") :: "
		return Event("privmsg", "", self.return_to_sender(args), [ line[:-4] ])

class geekquote(MooBotModule):
	""" Grabs a one-liner from bash.org
	Author: jamessan """
	def __init__(self):
		self.regex = "^geekquote.*$"

	def handler(self, **args):
		from irclib import Event
		target = self.return_to_sender(args)

		import urllib2
		import re

		quoteurl = "http://bash.org/?random1"
		try:
			html = urllib2.urlopen(quoteurl).read()
		except urllib2.URLError:
			return "error connecting to bash.org"
		# Grab a one-line quote unless they specify multiline
		if args["text"].find("multiline") == -1:
			quote_text=re.search('<p class="qt">(.*?)</p>',html)
		else:
			quote_text=re.search('<p class="qt">(.*?)</p>',html,re.DOTALL)
		try:
			quote=quote_text.group(1)
		except AttributeError:
			return "No quote found"

		# This replaces various bits of html chars. If someone wants to replace
		# it with HTMLParser stuff, feel free
		quote=re.sub('&lt;','<',quote)
		quote=re.sub('&gt;','>',quote)
		quote=re.sub('&nbsp;',' ',quote)
		quote=re.sub('&quot;','"',quote)
		quote=re.sub('<br />','',quote)

		return Event("privmsg", "", target, [quote])

# vim:ts=4:sw=4
