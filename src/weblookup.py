#!/usr/bin/env python
# -*- coding:gb2312 -*-

# Copyright (C) 2005, 2006, 2007 by FKtPp, moo
# Copyright (c) 2002 Daniel DiPaolo, et. al.
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

import re, httplib, urllib, urllib2, HTMLParser, weather
import htmlentitydefs
from moobot_module import MooBotModule
from irclib import Event, IrcStringIO
import json

handler_list = ["google", "kernelStatus", "Dict",
		"debpackage", "debfile", "genpackage", "foldoc", "pgpkey",
		"translate", "geekquote", "lunarCal", "ohloh", "radioOnline"]

# Without this, the HTMLParser won't accept Chinese attribute values
HTMLParser.attrfind=re.compile(
               r'\s*([a-zA-Z_][-.:a-zA-Z_0-9]*)(\s*=\s*'
               r'(\'[^\']*\'|"[^"]*"|[^ <>]*))?')

class IEURLopener(urllib.FancyURLopener):
	version = "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"

urllib._urlopener = IEURLopener()
urllib2._opener = urllib2.build_opener()
urllib2._opener.addheaders = [('User-agent', IEURLopener.version)]

def unescape(text):
	def fixup(m):
		text = m.group(0)
		if text[:2] == "&#":
			# character reference
			try:
				if text[:3] == "&#x":
					return unichr(int(text[3:-1], 16))
				else:
					return unichr(int(text[2:-1]))
			except ValueError:
				pass
		else:
			# named entity
			try:
				text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
			except KeyError:
				pass
		return text # leave as is
	return re.sub("&#?\w+;", fixup, text)

class weather(MooBotModule):
    def __init__(self):
        self.regex="^weather .+$"

    def handler(self, **args):
        """weather query from http://weather.com.cn/ ."""
        result = None
        target = self.return_to_sender(args)
        city_name = args["text"].split()[2]
        
        
        import subprocess
        """ query city4weather.txt for city id"""
        p = subprocess.Popen("""grep %s /path/to/city4weather.txt | awk '{print $2}' """ %\
                                             city_name , shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        city_id = '101020500'
        for city_id in p.stdout.readlines():
            if city_id[-1] == '\n':
                city_id = city_id[0:-1]

        weather_info = ""
        p = subprocess.Popen('curl http://m.weather.com.cn/data/%s.html' % city_id, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in p.stdout.readlines():
            weather_info = line

        import json
        s=json.loads(weather_info)
        ss = s["weatherinfo"]["city"] +',' + s["weatherinfo"]["date_y"] +',' + s["weatherinfo"]["week"] +',' + s["weatherinfo"]["temp1"] +',' + s["weatherinfo"]["weather1"] +',' + s["weatherinfo"]["wind1"] +',' +s["weatherinfo"]["index_d"]
        result = ss.encode("UTF-8")

        from irclib import Event
        return Event("privmsg", "", target, [result])

class weathercn(MooBotModule):
	"""weather module to get weather forecast infomation
	
	This module depends on weather.py, it use weather.py to
	parse the html page of weathercn.com. Note, we must ignore
	the HTMLParser.HTMLParseError because of the malformed
	html pages.
	"""
	def __init__(self):
		"""
		>>> import re
		>>> from weblookup import weathercn
		>>> a = weathercn()
		>>> r = re.compile(a.regex)
		>>> r.match("w") and True or False
		True
		>>> r.match("weather") and True or False
		True
		>>> r.match("w 0335") and True or False
		True
		>>> r.match("weather 0335") and True or False
		True
		>>> r.match("wo03335") and True or False
		False
		>>> r.match("w 10086") and True or False
		True
		>>> r.match(u"w 通化") and True or False
		True
		>>> r.match(u"weather 通辽") and True or False
		True
		>>> r.match(u"w 北京") and True or False
		True
		>>> r.match(u"w 通化 8") and True or False
		True
		>>> r.match(u"weather 通辽 9") and True or False
		True
		>>> r.match(u"w 北京 37") and True or False
		True
		>>> r.match("who") and True or False
		False
		"""
		self.regex = "^(weather|w)($|( [^ ]+){1,2})"

	def handler(self, **args):
		"""Parse the received commandline arguments
		
		case length of the real arguments:
		
		zero, check database to see if the user already
		      have a record. y: use it to get the forcast
		      and setting change tips; n: print help 
		      message.
		   1, get and print the citylist.
		   2, get the citylist, and then get the forecast
		      accroding the second argument. print the
		      result, save settings to database.

		and any any any better throughts ;) --save to control
		database operation?
		"""
 
		# TODO: ... save settings to database
		# TODO: ... get settings from database

		self.result = {'notice': '',
			       'msg': ''}

		tmp_args_list = args["text"].strip().split(" ")
		del(tmp_args_list[0])

		lenlist = len(tmp_args_list)
		
		if lenlist in (2, 3):
			len1 = len(tmp_args_list[1])
				
			if lenlist == 3\
					and not tmp_args_list[2].isdigit():
				self.result['notice'] = u"区域索引”n“必须是数字，"\
					u"请重新输入"
			
			elif len1 < 2:
				self.result['notice'] = u"“城市名称”不可少于两个字符，"\
				u"请重新输入"
			elif tmp_args_list[1].isdigit():
				if len1 not in (3, 4, 6) or tmp_args_list[1][:2] == '00':
					self.result['notice'] = u"非法的区号或邮政编码，"\
							u"请重新输入"
				elif len1 == 6 and tmp_args_list[1][3:] != '000':
					self.result['notice'] = u"请使用市级以上邮政编码，"\
							u"TIP：将您的邮编后三位改为“000”"
				elif len1 in (3, 4) \
						and tmp_args_list[1][0] != '0':
					self.result['notice'] = u"非法的电话区号, "\
							u"请重新输入"
				else: 
					self.gogetit(tmp_args_list)
					
			elif tmp_args_list[1].isalpha() and len1 > 4:
				self.result['notice'] = u"请给我一个“城市名或拼音缩写”多于"\
				u" 4 个字符的理由"
			else:
				self.gogetit(tmp_args_list)
				
		else:
			self.result['notice'] = self._help()
		
# 		print self.result['notice'].encode('utf8')
# 		print self.result['msg'].encode('utf8')

		if self.result['notice'] and not self.result['msg']:
			target = self.return_to_sender(args, 'nick')
			return Event("notice", "", target, [self.result['notice']])

		if self.result['msg']:
			target = self.return_to_sender(args)
			return Event("privmsg", "", target, [self.result['msg']])

	def gogetit(self, l):
		"""get back the citylist or recursively invoke getforecast
		
		get the citylist, setup notice message it if there is
		no 3rd arg.  check length against the 3rd arg, invoke
		getforcast if valid.
		""" 
		
		citykeyword = l[1].lower()
		search_parm = urllib.urlencode({"searchname": citykeyword.encode("gbk")})
		print search_parm
		try:
			response = urllib.urlopen("http://www.weathercn.com/search/search.jsp",
									  search_parm)
		except IOError, e:
			print e
		
		rp = weather.WeatherCNCITYParser()
		try:
			rp.feed(response.read().decode("gbk"))
			print response.read()
		except HTMLParser.HTMLParseError:
			pass
		
		response.close()
		
		regionlist = rp.o()
		
		if len(l) < 3:
			if len(regionlist) == 1:
				c, u = regionlist[0]
				self.getforcast(u)
			else:
				i = 1
				result = IrcStringIO('%s: ' % citykeyword, 200)
				for c, u in regionlist:
					result.write("".join(("=", str(i),"=>", c)))
					i += 1
				self.result['notice'] = result.getvalue()

		elif len(regionlist) < int(l[2]):
			self.result['notice'] = u"地区索引”n”大于地区总个数"
		else:
			c, u = regionlist[int(l[2])-1]
			self.getforcast(u)

	def getforcast(self, url):
		"""Get the weather forcast from the given url
		
		get and then parse the weather forcast, setup the
		result message
		"""
		try:
			response = urllib.urlopen("http://www.weathercn.com%s" % url)
		except IOError, e:
			print e
		
		fp = weather.WeatherCNParser()
		
		try:
			fp.feed(response.read().decode("gbk"))
		except HTMLParser.HTMLParseError:
			pass
		
		response.close()
		
		self.result['msg'] = " ".join(fp.o())

	def _help(self, a="help"):
		"""return help messages
		"""
		myhelpmsg = u"BadGirl 天气预报员模块！使用 <weather 你的城市> 获\
取详细城市列表，使用 <weather 你的城市 n> 获取对应城市的天气信息。“你的\
城市”可以是“城市的中文名，城市拼音缩写，城市的邮政编码，城市的长途区号”；地区索引“n”是\
<weather 你的城市> 返回的地区列表中区域对应的数字。"
		mytipmsg = u"您可以重新执行 <weather 您想要查看的城市> 和\
 <weather 您想要查看的城市 n> 来修改自己的首选城市。"
		if a == "help":
			msg = myhelpmsg
		else:
			msg = mytipmsg

		return msg

class google(MooBotModule):
	"Does a search on google and returns the first 5 hits"
	def __init__(self):
		self.regex = "^google for .+"

	def handler(self, **args):
		self.return_to_sender(args)

		keyword = " ".join(args["text"].split(" ")[3:])

		target = self.return_to_sender(args)
		try:
			response = self.search(keyword)
		except:
			msg = "error"
			return Event("privmsg", "", target, [ msg ])
		return Event("privmsg", "", target, [ response ])

	rResult = re.compile('<h3 class="?r(?: [^>"]*)?"?>(.*?)</h3>', re.S)
	rA = re.compile('<a href="?([^ "]*)"?[^>]*>(.*?)</a>', re.S)
	rCalc = re.compile('<img[^>]*src=/images/calc[^>]*>(.*?)</h2>', re.S)
	rB = re.compile('<b>(.*?)</b>', re.S)
	def search(self, keyword):
		url = "http://www.google.com/search?hl=en&btnG=Search&aq=f&aqi=&aql=&oq=&gs_rfai=&"
		url += urllib.urlencode({"q" : keyword.encode("UTF-8", 'replace')})
		result = urllib.urlopen(url).read().decode("UTF-8", 'replace')
		results = []
		m = self.rCalc.search(result)
		if m:
			m = self.rB.search(m.group(1))
			if m:
				results.append(unescape(m.group(1)))
		for i in self.rResult.findall(result.split('<ol>', 2)[1].split('</ol>', 2)[0]):
			m = self.rA.search(i)
			if not m:
				continue
			url = m.group(1)
			if url.startswith("/"):
				continue

			results.append(unescape(url))
			if len(results) >= 5:
				break

		line = "Google says \"" + keyword + "\" is: " + " ".join(results)
		return line

class kernelStatus(MooBotModule):
	def __init__(self):
		self.regex = "^kernel$"

	def handler(self, **args):
		"""
		gets kernel status
		"""
		# self.debug("kernelStatus")
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

		
		target = self.return_to_sender(args)
		return Event("privmsg", "", target, [ result ])


class Dict(MooBotModule):
	cache = {}
	cache_old = {}
	def __init__(self):
		
		# have problem filtering out `|' character
		self.regex = "^(dict |~)[^~\+\*/\\<>-]+"
		self.rStrip = re.compile("(<.*?>)+")
		self.rWord = re.compile("^<!-- WORD", re.I)
		self.rGif = re.compile("/gif/([\\w_]+)\\.gif", re.I)
		self.rBody = re.compile("^<!-- BODY", re.I)
		self.ymap = {"slash": "/", "quote": "'", "_e_": "2", "_a": "a:", "int": "S"}
		self.ciba_failed = 1
		self.rSearch = re.compile(u'^[^*?_%]{2,}[*?_%]')

	def handler(self, **args):
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
			# result = self.lookup_ciba(word)
			result = result.replace("&lt;","<").replace("&gt;",">")
			if len(result) == 0:
				result = "Could not find definition for " + word
			elif result == "error":
				pass
			else:
				self.cache[word] = result

		return Event("privmsg", "", target, [ result ])

	iciba_cmap = {"\\\\": "\\", "5": "'", "E": "2"}
	iciba_rNx = re.compile(u"添加这个词条")
	iciba_rCtoE = re.compile(u"词典释义")
	iciba_rRwWord = re.compile('rwWord\("([^"]+)"\)')

	iciba_rEtoC = re.compile(u'<div id="sentence_close')
	iciba_rExplain = re.compile('explain_item">(.*?)</div>', re.S)
	iciba_rSpell = re.compile("str2img\('([^']+)", re.I)
	def lookup_ciba(self, word):
		try:
			response = urllib.urlopen("http://www.iciba.com/%s/" % urllib.quote(word.encode("UTF-8")))
		except Exception, e:
			self.Debug(e)
			return "error"
		else:
			# Do the parsing here
			html = response.read().decode("UTF-8", "ignore")
			if self.iciba_rNx.search(html):
				return ""
	
			m = self.iciba_rCtoE.search(html)
			if m:
				m = self.iciba_rRwWord.findall(html)
				if m:
					result = word + ':'
					for i in m:
						result += ' ' + i
					return result

			m = self.iciba_rEtoC.search(html)
			if m:
				result = word + ":"

				m = self.iciba_rSpell.search(html)
				if m:
					spell = m.group(1)
					for k in self.iciba_cmap:
						spell = spell.replace(k, self.iciba_cmap[k])
					result += " /" + spell + "/"

				m = self.iciba_rExplain.search(html)
				if m:
					result += ' ' + m.group(1).strip()
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

			self.Debug(loc)
			if loc and re.compile("/error").match(loc):
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

class Translator:
	commonHeader = {
		"Content-type": "application/x-www-form-urlencoded",
		"User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)",
		"Accept-Encoding": ""
	}

	langMap = {}

	def mapLanguage(self, lang):
		if lang in self.langMap:
			return self.langMap[lang]
		else:
			return lang

	def translate(self, text, fromLang, toLang, fromLanguage, toLanguage):
		pass

class TranslatorExcite(Translator):
	name = "Excite"
	command = "excite"

	langMap = {
		'zh': 'ch',
		'zt': 'ch',
		}

	supportedTranslations = {
		'jaen': '/world/english/',
		'enja': '/world/english/',

		'jach': '/world/chinese/',
		'chja': '/world/chinese/',

		'koen': '/world/korean/',
		'enko': '/world/korean/',

		'frja': '/world/french/',
		'jafr': '/world/french/',
		'fren': '/world/french/',
		'enfr': '/world/french/',

		'deja': '/world/german/',
		'jade': '/world/german/',
		'deen': '/world/german/',
		'ende': '/world/german/',

		'itja': '/world/italian/',
		'jait': '/world/italian/',
		'iten': '/world/italian/',
		'enit': '/world/italian/',

		'esja': '/world/spanish/',
		'jaes': '/world/spanish/',
		'esen': '/world/spanish/',
		'enes': '/world/spanish/',

		'ptja': '/world/portugupte/',
		'japt': '/world/portugupte/',
		'pten': '/world/portugupte/',
		'enpt': '/world/portugupte/',
	}
	encodings = {
		'jaen': 'Shift_JIS',
		'enja': 'Shift_JIS'
	}

	rResult = re.compile('<textarea[^>]+id="after"[^>]*>(.*?)</textarea>')

	def translate(self, text, fromLang, toLang, fromLanguage, toLanguage):
		if fromLanguage == 'cht' or toLanguage == 'cht':
			big5 = 'yes'
		else:
			big5 = 'no'
		translation = fromLang + toLang
		import irclib
		if translation not in self.supportedTranslations:
			irclib.DebugErr(translation)
			return
		if translation in self.encodings:
			encoding = self.encodings[translation]
		else:
			encoding = "UTF-8"
		# create the POST body
		params = {
			'before': text.encode(encoding, 'ignore'),
			'wb_lp':  translation.upper(),
			'start':  '',
			'big5':   big5,
		}
		# connect, make the reauest
		url = self.supportedTranslations[translation]
		connect = httplib.HTTPConnection('www.excite.co.jp', 80)
		connect.request("POST", url, urllib.urlencode(params), self.commonHeader)
		response = connect.getresponse()
		if response.status != 200: # check for errors
			irclib.DebugErr(response)
			return

		html = response.read().decode(encoding, "ignore")
		import HTMLParser
		html = HTMLParser.HTMLParser().unescape(html).replace('\n', '') # get rid of newlines
		match = self.rResult.search(html)
		if match:
			return match.group(1)

class TranslatorGoogle(Translator):
	name = "google"
	command = "google"

	langMap = {
		'zh': 'zh-CN',
		'zt': 'zh-TW',
		}

	supportedTranslations = [
		"sq",
		"ar",
		"bg",
		"ca",
		"zh-CN",
		"zh-TW",
		"hr",
		"cs",
		"da",
		"nl",
		"en",
		"et",
		"tl",
		"fi",
		"fr",
		"gl",
		"de",
		"el",
		"iw",
		"hi",
		"hu",
		"id",
		"it",
		"ja",
		"ko",
		"lv",
		"lt",
		"mt",
		"no",
		"pl",
		"pt",
		"ro",
		"ru",
		"sr",
		"sk",
		"sl",
		"es",
		"sv",
		"th",
		"tr",
		"uk",
		"vi",
		]

	def translate(self, text, fromLang, toLang, fromLanguage, toLanguage):
		if fromLang not in self.supportedTranslations or toLang not in self.supportedTranslations:
			return

		# create the POST body
		params = {
			'client': 't',
			"text":   text.encode("UTF-8"),
			"sl":     fromLang,
			"tl":     toLang,
		}
		# connect, make the reauest
		connect = httplib.HTTPConnection('translate.google.com', 80)
		connect.request("GET", '/translate_a/t?' + urllib.urlencode(params), '', self.commonHeader)
		response = connect.getresponse()
		if response.status != 200: # check for errors
			return

		result = response.read().decode("UTF-8", "ignore")
		result = result.replace('[,', '[[],').replace(',]', ',[]]')
		while ',,' in result:
			result = result.replace(',,', ',[],')
		translated = json.loads(result)
		result = translated[0][0]
		return result[0].replace(',[],', ',,') + ' ' + result[2].replace(',[],', ',,')

class TranslatorBabelFish(Translator):
	name = "babelfish"
	command = "babelfish"

	supportedTranslations = [
		"zh_en",
		"zh_zt",

		"zt_en",
		"zt_zh",
		"en_zh",
		"en_zt",
		"en_nl",
		"en_fr",
		"en_de",
		"en_el",
		"en_it",

		"en_ja",
		"en_ko",
		"en_pt",
		"en_ru",
		"en_es",
		"nl_en",
		"nl_fr",
		"fr_nl",
		"fr_en",

		"fr_de",
		"fr_el",
		"fr_it",
		"fr_pt",
		"fr_es",
		"de_en",
		"de_fr",
		"el_en",
		"el_fr",

		"it_en",
		"it_fr",
		"ja_en",
		"ko_en",
		"pt_en",
		"pt_fr",
		"ru_en",
		"es_en",
		"es_fr"
		]

	rResult = re.compile('<div id="result"><div style="padding:0.6em;">(.*?)</div></div>')

	def translate(self, text, fromLang, toLang, fromLanguage, toLanguage):
		translateMode = "%s_%s" % (fromLang, toLang)
		if translateMode not in self.supportedTranslations:
			return

		text = text.replace("'", u"’");

		# create the POST body
		params = {"ei": "UTF-8", "doit": "done", "fr": "bf-res", "intl": "1", "tt": "urltext", "trtext": text.encode("UTF-8"), "lp": translateMode}
		# connect, make the reauest
		connect = httplib.HTTPConnection('babelfish.yahoo.com', 80)
		connect.request("POST", "/translate_txt", urllib.urlencode(params), self.commonHeader)
		response = connect.getresponse()
		if response.status != 200: # check for errors
			return

		html = response.read().decode("UTF-8", "ignore")
		html = html.replace('\n', '') # get rid of newlines
		match = self.rResult.search(html)
		if match:
			return match.group(1)

class translate(MooBotModule):
	"Does a search on web and returns the translation"
	languageToLangs = {
		"arabic":    "ar",
		"bulgarian": "bg",
		"catalan":   "ca",
		"czech":     "cs",
		"danish":    "da",
		"german":    "de",
		"greek":     "el",
		"english":   "en",
		"spanish":   "es",
		"estonian":  "et",
		"finnish":   "fi",
		"french":    "fr",
		"galician":  "gl",
		"hindi":     "hi",
		"croatian":  "hr",
		"hungarian": "hu",
		"indonesian":"id",
		"italian":   "it",
		"hebrew":    "iw",
		"japanese":  "ja",
		"korean":    "ko",
		"lithuanian":"lt",
		"latvian":   "lv",
		"maltese":   "mt",
		"dutch":     "nl",
		"norwegian": "no",
		"polish":    "pl",
		"portuguese":"pt",
		"romanian":  "ro",
		"russian":   "ru",
		"slovak":    "sk",
		"slovenian": "sl",
		"albanian":  "sq",
		"serbian":   "sr",
		"swedish":   "sv",
		"thai":      "th",
		"filipino":  "tl",
		"turkish":   "tr",
		"ukrainian": "uk",
		"vietnamese":"vi",
		"chinese":   "zh",
		"chs":       "zh",
		"cht":       "zt",
	}

	langToLanguages = dict([(v, k) for (k, v) in languageToLangs.iteritems()])

	shortcuts = {
		"ec": "en_zh",
		"ce": "zh_en"
	}

	def __init__(self):
		"""
		>>> t = translate()
		>>> re.compile(t.rTranslation).search("zh_en").group(1)
		'zh'
		>>> re.compile(t.rTranslation).search("zh_en").group(2)
		'en'
		>>> t.re.match("translate").group(0)
		'translate'
		>>> t.re.match("translate zh_en test").group(2)
		'zh'
		>>> t.re.match("translate zh_en test").group(1)
		'translate'
		>>> t.re.match("google zh_en test").group(1)
		'google'
		>>> t.re.match("babelfish zh_en test").group(1)
		'babelfish'
		>>> t.re.match("translate chinese to english test").group(2)
		'chinese'
		>>> t.re.match("zh_en test").group(2)
		'zh'
		>>> t.re.match("zh_en").group(0)
		'zh_en'
		"""

		self.translators = (TranslatorExcite(), TranslatorGoogle(), TranslatorBabelFish())

		rLanguage = "|".join(self.languageToLangs.keys() + self.languageToLangs.values())
		self.rTranslators = 'translate|' + "|".join(translator.command for translator in self.translators)
		self.rShortcuts = '|'.join(self.shortcuts.keys())
		self.rTranslation = "(%s)(?:[-_]| +to +)(%s)|(%s)" % (rLanguage, rLanguage, self.rShortcuts)
		self.regex = "(?i)^(?:(%s) +|)(?:%s) +(.*)|^(?:(?:%s)|(?:%s))(?:$| +)|^languages$" % (self.rTranslators, self.rTranslation, self.rTranslators, self.rTranslation)
		self.re = re.compile(self.regex)
		self.reWord = re.compile('^[a-z]+$', re.I)

	def help(self, args):
		return Event("privmsg", "", self.return_to_sender(args), [
			"Usage: [%s] <from> to <to> TEXT, OR: <%s> TEXT. See also: Languages\r\n" % (self.rTranslators, self.rShortcuts)
			])

	def helpLanguages(self, args):
		langs = []
		i = 0
		for (language, lang) in self.languageToLangs.iteritems():
			langs.append(language + ':' + lang)
			i = i + len(language) + len(lang) + 2
			if i > 400:
				langs.append("\r\n")
				i = 0

		return Event("privmsg", "", self.return_to_sender(args), [
			"Languages: %s" % " ".join(langs)
			])

	def handler(self, **args):
		text = " ".join(args["text"].split(" ", 2)[1:])
		if text == 'languages':
			return self.helpLanguages(args)
		# get parameter
		match = self.re.match(text)
		text = match.group(5)
		if text is None:
			return self.help(args)

		type = match.group(1)
		if type:
			type = type.lower()
		if match.group(2) is not None:
			fromLang, toLang = (match.group(2).lower(), match.group(3).lower())
		elif match.group(4):
			fromLang, toLang = self.shortcuts[match.group(4)].lower().split("_", 2)

		# language
		if fromLang in self.languageToLangs:
			fromLang = self.languageToLangs[fromLang]
		if toLang in self.languageToLangs:
			toLang = self.languageToLangs[toLang]
		fromLanguage = self.langToLanguages[fromLang]
		toLanguage = self.langToLanguages[toLang]

		# redirect stupid query
		if text.find(' ') == -1 and self.reWord.search(text):
			return Event("privmsg", "", self.return_to_sender(args), 
				[ "use: dict " + text + " or ~~" + text])

		# which translator(s)?
		translators = None
		for translator in self.translators:
			if translator.command == type:
				translators = (translator, )
		if not translators:
			translators = self.translators

		# dispatch it
		for translator in translators:
			result = translator.translate(text, translator.mapLanguage(fromLang), translator.mapLanguage(toLang), fromLanguage, toLanguage)
			if result:
				return Event("privmsg", "", self.return_to_sender(args), 
					[ "%s translation: %s" % (translator.name.capitalize(), result) ])

		# check if we know the languages they want to use
		return Event("privmsg", "", self.return_to_sender(args), 
			[ "translating from %s to %s is not supported" % (fromLanguage, toLanguage) ])

class debpackage(MooBotModule, HTMLParser.HTMLParser):
	"""
	Does a package search on http://packages.debian.org and returns top 10 result
	"""
	def __init__(self):
		self.regex="^debpackage .+"
		self.package = ""
		self.branch = ""
		HTMLParser.HTMLParser.__init__(self)

	def reset(self):
		HTMLParser.HTMLParser.reset(self)
		self.__max_hit = 10
		self.inner_div = False
		self.in_ul = False

		self.o = IrcStringIO("%s(%s):" % (self.package, self.branch))

		self.li = 0
		self.li_over = False
		self.after_br = False

	def handler(self, **args):

		target = self.return_to_sender(args)

		## Parse the request
		# A branch can be specified as the first argument, and multiple
		# packages can be requested.
		branches = ['oldstable',
			    'stable',
			    'testing',
			    'unstable',
			    'experimental',
			    'all']

		request = args["text"].split()[2:]
		if request[0] in branches:
			self.branch = request[0]
			del request[0]
		else:
			self.branch = 'testing'

		# Now, they may have forgotten to specify a package if
		# they provided a branch (the regex will still match)
		if len(request) != 1:
			msg = "Usage: debpackage [oldstable|stable|testing|unstable|experimental|all] PackageName"
			return Event("privmsg", "", target, [msg])
		else:
			self.package = request[0]

		# Otherwise, request should now contain a list of
		# packages We'll step through them one by one and
		# display them all at once at the end.
		form_action = "http://packages.debian.org/search?%s"
		form_inputs = urllib.urlencode ({"keywords": self.package,
						 "searchon": "names",
						 "exact": 1,
						 "suite": self.branch,
						 "section": "all"})
		# build the request
		try:
			response = urllib.urlopen(form_action % form_inputs)
		except Exception, e:
			self.Debug(e)
		else:
			self.reset()
			self.feed(response.read())
		response.close()
		return Event("privmsg", "", target, [self.o.getvalue()])

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
				self.o.write(" =%d=> " % self.li)
			else:
				self.li_over = True
		elif tag == "a" and self.in_ul and not self.li_over:
			for a_name, a_value in attrs:
				if a_name == "href":
					self.o.write("http://packages.debian.org%s " % a_value)
					self.in_a = True
		elif tag == "br" and self.in_ul:
			self.after_br = True

	def handle_endtag(self, tag):
		if tag == "ul":
			self.in_ul = False
		elif tag == "a":
			self.in_a = False

	def handle_data(self, data):
		if self.in_ul and \
			    not self.li_over and \
			    not self.in_a and \
			    not self.after_br:
			self.o.write(data.strip())

class debfile(MooBotModule, HTMLParser.HTMLParser):
	"""
	Does a file search on http://packages.debian.org and returns
	top 10 matched package names
	"""

	def __init__(self):
		self.regex = "^debfile .+"
		self.file = ""
		self.version = ""
		HTMLParser.HTMLParser.__init__(self)

	def reset(self):
		HTMLParser.HTMLParser.reset(self)
		self.o = IrcStringIO("%s(%s):" % (self.file, self.version))
		
		# s stands for stats, True means inside that tag
		# p stands for parent
		# c stands for children
		self.tag_structs = {'div': {'s': False,
					    'p': None,
					    'c': ('table',),
					    'id': 'pcontentsres'},
				    'table': {'s': False,
					      'p': 'div',
					      'c': ('tr',)},
				    'tr': {'s': False,
					   'p': 'table',
					   'c': ('td',)},
				    'td': {'s': False,
					   'p': 'tr',
					   'c': ('span', 'a')},
				    'span': {'s': False,
					     'p': 'td',
					     'c': None,
					     'class': 'keyword'},
				    'a': {'s': False,
					  'p': 'td',
					  'c': None}}


		# first raw is table header <th>
		self.hit = -1
		self.__max_hit = 10
		
		self.in_file_td_head = False
		self.file_td_head = ''
		self.in_file_td_tail = False
		self.file_td_tail = ''

		self.file_keyword = ''

	def handler(self, **args):
		
		target = self.return_to_sender(args)
		self.version = ['oldstable', 'stable', 'testing', 'unstable']
		request = args["text"].split()[2:]
		if request[0] in self.version:
			self.version = request[0]
			del request[0]
		else:
			self.version = "testing"
		if len(request) != 1:
			msg = "Usage: debfile [oldstable|stable|testing|unstable] filename"
			return Event("privmsg", "", target, [msg])
		self.file = request[0]
		form_action = "http://packages.debian.org/search?%s"
		form_inputs = urllib.urlencode({"searchon": "contents",
						"keywords": self.file,
						"mode": "path",
						"suite": self.version,
						"arch": "i386"})
		try:
			result = urllib.urlopen(form_action % form_inputs)
		except Exception, e:
			self.Debug(e)
		else:
			self.reset()
			self.feed(result.read())
			result.close()
			return Event("privmsg", "",
				     target,
				     [self.found_or_not()])

	def found_or_not(self):
		return self.o.getvalue().strip() or \
		    "%s(%s): Not Found!" % (self.file, self.version)

	def _check_stat(self, tag):
		"""To see if we can change tag's inside/outside stat

		return True if we can change it, or return False.
		"""
		# out of parent tag, we do nothing
		if self.tag_structs[tag]['p'] and \
		   not self.tag_structs[self.tag_structs[tag]['p']]['s']:
			return False

		# must be out of all chilren tags or we do nothing
		elif self.tag_structs[tag]['c']:
			for c in self.tag_structs[tag]['c']:
				if self.tag_structs[c]['s']:
					return False

		return True

	def handle_starttag(self, tag, attrs):
		if self.tag_structs.has_key(tag):
			if attrs:
				for a, v in attrs:
					if self.tag_structs[tag].has_key(a) and \
						    self.tag_structs[tag][a] != v:
						return

			if self._check_stat(tag) and \
				    not self.tag_structs[tag]['s']:
				self.tag_structs[tag]['s'] = True

				for a, v in attrs:
					if tag == 'td' and \
						    a == 'class' and\
						    v == 'file':
						self.in_file_td_head = True
					elif tag == 'span' and \
						    a == 'class' and \
						    v == 'keyword':
						self.in_file_td_head = False



	def handle_endtag(self, tag):
		if self.tag_structs.has_key(tag):
			if self._check_stat(tag) and \
				    self.tag_structs[tag]['s']:
				self.tag_structs[tag]['s'] = False

				if tag == 'tr':
					self.hit += 1

				elif tag == 'span':
					# YES, it's unreliable. But if
					# there's no 'span' there
					# would be no
					# file_td_head/tail either,
					# there would be only one
					# file_td
					self.in_file_td_tail = True

				elif tag == 'td' and \
					    (self.in_file_td_head or \
						     self.in_file_td_tail):
					# span is unreliable
					self.in_file_td_head = False
					self.in_file_td_tail = False
					

	def handle_data(self, data):
		if self.hit < self.__max_hit:
			if self.tag_structs['td']['s']:
				if self.in_file_td_head:
					self.file_td_head = data
				elif self.in_file_td_tail:
					self.file_td_tail = data

			if self.tag_structs['span']['s']:
				self.file_keyword = data

			if self.tag_structs['a']['s']:
				self.o.write(' =%d=> ' % (self.hit + 1))
				if self.file_td_head:
					self.o.write(self.file_td_head)
				if self.file_keyword:
					self.o.write(self.file_keyword)
				if self.file_td_tail:
					self.o.write(self.file_td_tail)
				
				self.o.write(' ')
				self.o.write(data)

class genpackage(MooBotModule):
	"""
	Does a package or file search on http://www.portagefilelist.de/index.php/Special:PFLQuery2 and returns top 10 result
	"""
	re_tag = re.compile("<[^>]+>")
	re_td = re.compile("<td[^>]*>,? *(.*?) *,?</td>", re.S)
	def __init__(self):
		self.regex="^(genpackage|genfile)( .+)?$"

	def handler(self, **args):
		target = self.return_to_sender(args)

		request = args["text"].split()[1:]

		if len(request) == 2:
			all = False
			cmd, param = request
		elif len(request) == 3 and request[1] == 'all':
			all = True
			cmd, dummy, param = request
		else:
			msg = "Usage: <genpackage|genfile> [all] [$dir/]$packagename, OR genfile [all] $path"
			return Event("privmsg", "", target, [msg])
		form_action = "http://www.portagefilelist.de/site/query"
		if cmd == 'genpackage':
			form_action += "listPackageFiles?do"
			package = param
			if package.find('/') != -1:
				dir, package = package.split('/', 1)
			else:
				dir = ''

			params = {
				"dir": dir,
				"package": package,
				"searchpackage": "lookup",
				"lookup": "package"}
			if not all:
				params["unique_packages"] = "on"
		else:
			form_action += "/file/?do"
			file = param

			params = {
				"file": file.replace('*', '%'),
				}
			if not all:
				params["unique_packages"] = "on"

		form_inputs = urllib.urlencode(params)
		# build the request
		try:
			response = urllib.urlopen(form_action, form_inputs)
		except Exception, e:
			return Event("privmsg", "", target, [str(e)])
		msg_notfound = Event("privmsg", "", target, ["not found"])
		html = response.read().decode("UTF-8")
		self.Debug(html)
		if html.find("search result") == -1:
			return msg_notfound
		dummy, html = html.split("search result", 1)
		if html.find("</table") == -1:
			return msg_notfound
		html, dummy = html.split("</table", 1)
		results = []
		rows = html.split("</tr")[:-1]
		for row in rows:
			tds = self.re_td.findall(row)
			# genpackage
			if len(tds) == 2:
				results.append(self.re_tag.sub("", "%s/%s" % (tds[0], tds[1])))
			elif len(tds) == 3:
				results.append(self.re_tag.sub("", "%s/%s-%s" % (tds[0], tds[1], tds[2])))
			# genfile
			elif len(tds) == 5:
				results.append(self.re_tag.sub("", "%s %s @%s - %s USE %s" % (tds[2], tds[1], tds[0], tds[3], tds[4])))
			elif len(tds) == 6:
				results.append(self.re_tag.sub("", "%s/%s @%s/%s-%s" % (tds[2], tds[3], tds[0], tds[1], tds[5])))
			#else:
			#	return msg_notfound
		results.sort(lambda x,y: cmp(y.lower(), x.lower()))
		result = ", ".join(results[0:10])
		return Event("privmsg", "", target, [result])

class foldoc(MooBotModule):
	"""
	Free On-line Dicitionary Of Computing
	"""
	def __init__(self):
		self.regex = "^explain .+"
		self.rDescr = re.compile("<P>(.*?)<font ", re.I | re.S)

	# Returns the position of the nth element in lst.
	def index(self, lst, element, n=1):
		m = 0
		for i in xrange(len(lst)):
			if lst[i] == element:
				m += 1
				if m == n:
					return i

	def handler(self, **args):
		result = None
		target = self.return_to_sender(args)

		word = args["text"].split()[2]
		url = "http://foldoc.org/" + urllib.urlencode({'': word})[1:]
		try:
			html = urllib.urlopen(url).read()
		except IOError, e:
			result = "error connecting to foldoc"

		if not result:
			match = self.rDescr.search(html)
			if not match:
				result = "error parsing foldoc"
			elif match.group(1).find("Missing definition") != -1:
				result = "not found"
			else:
				descr = match.group(1) # Get the base description
				descr = descr.split("Try this search on", 1)[0]
				descr = re.sub("[\r\n]", " ", descr) # Remove newlines
				descr = re.sub("<[^>]*>", "", descr) # Remove HTML tags
				descr = descr.replace("&lt;", "<")
				descr = descr.replace("&gt;", ">")
				descr = re.sub("&.*?;", "", descr)
				descr = re.sub(" {2,}", " ", descr)
				descr = descr.strip()
				result = word + ": " + descr

		return Event("privmsg", "", target, [result])

class pgpkey(MooBotModule):
	""" Does a key search on pgp.mit.edu and returns the first 5 hits
	Author: jamessan """
	def __init__(self):
		self.regex = "^pgpkey .+$"

	def handler(self, **args):
		self.return_to_sender(args)

		
		search_terms = args["text"].split(" ")[2:]
		domain = "pgp.mit.edu"
		port=11371
		search_request = "/pks/lookup?op=index&search="
		search_request += '+'.join(search_terms)
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
		line = "pgpkey matches for \"" + ' '.join(search_terms) + "\": "
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
		
		target = self.return_to_sender(args)

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


class lunarCal(MooBotModule):
	"""黄历查询 by Ian@linuxfire.com.cn
		Action: http://www.shpan.com/huangli/MyDetail.asp?currentDate=
		Method: GET
		Params: yyyy-mm-dd
	"""
	URL = "http://www.shpan.com/huangli/MyDetail.asp?currentDate="
	def __init__(self):
		self.regex = "^hl( +[^ ]*)?"
	
	def parse_date(self, strDate):
		from datetime import date
		if strDate.isdigit():
			d = date(int(strDate[0:-4]), int(strDate[-4:-2]), int(strDate[-2:]))
		else:
			tupDate = re.findall('(\d+)-(\d+)-(\d+)', strDate)
			if len(tupDate) == 1:
				d = date(int(tupDate[0][0]), int(tupDate[0][1]), int(tupDate[0][2]))
			else:
				raise ValueError, "输入格式不正确。";
		return d.isoformat()
	
	def fetch(self, date):
		#print date
		response = urllib.urlopen(lunarCal.URL+date)
		html = response.read().decode("GBK")
		response.close()
		return html
	
	def extract(self, text):
		date = re.compile("中华人民共和国\d{4}年\d+月\d+日黄历".decode("GBK"))
		hl = re.search(date, text)
		if hl:
			msg = ["\002" + hl.group(0) + "\002.  "]
			date = re.compile('<tr>[^<]*<td[^>]*class="TdShow"\s*>([^<]*)</td>\s*<td[^>]*class="TdShow"\s*>([^<]*)</td>\s*</tr>')
			for item in re.findall(date, text):
				msg.append("\002" + item[0].strip() + "\002 " + item[1].strip())
			return msg
		else:
			raise ValueError, "查询结果无效。";
	
	def handler(self, **args):
		qstr = args["text"].strip().split(" ")[1:]
		try:
			if len(qstr) == 1:
				from datetime import date
				theDate = date.today().isoformat()
			elif len(qstr) == 2:
				theDate = self.parse_date(qstr[1])
			else:
				raise ValueError, "输入格式不正确。";
			msg = ["\n".join(self.extract(self.fetch(theDate)))]
		except ValueError, e:
			desc = str(e).decode("GBK")
			msg = [desc]
		#for m in msg: print m
		return Event("notice",
			     "",
			     self.return_to_sender(args, select="nick"),
			     msg)

class ohloh(MooBotModule):
	urlAccount = "http://www.ohloh.net/accounts/{account_id}.xml"
	def __init__(self):
		self.regex = "^((ohloh|kudo)( +.+)?|(ohlohpk|kudopk) +[^ ]+( +[^ ]+)?|(ohloh|kudo)help)$"
	
	def getKey(self, bot):
		return bot.configs["ohloh"]["key"]

	def domNodeToObject(self, node):
		import xml.dom.minidom as dom
		obj = {}
		text = ''
		for node in node.childNodes:
			if node.nodeType == node.ELEMENT_NODE:
				obj[node.nodeName] = self.domNodeToObject(node)
			elif node.nodeType == node.TEXT_NODE:
				text += node.nodeValue
		if not obj:
			obj = text
		return obj

	def queryAccount(self, bot, account):
		if account.find("@") != -1:
			import md5
			m = md5.new()
			m.update(account)
			account = m.hexdigest()


		params = urllib.urlencode({ 'api_key': self.getKey(bot), 'v': 1 })
		url = self.urlAccount.replace('{account_id}', account) + "?" + params
		print url
		response = urllib.urlopen(url)
		html = response.read()
		response.close()

		import xml.dom.minidom as dom
		doc = self.domNodeToObject(dom.parseString(html).documentElement)
		if not doc or doc["status"] != "success":
			return None

		return doc["result"]["account"]
	
	def handler(self, **args):
		bot = args["ref"]()
		try:
			self.getKey(bot)
		except ValueError:
			return Event("privmsg", "", self.return_to_sender(args), [ u"ohloh key not configured" ])

		argv = args["text"].strip().split(" ")
		del argv[0]
		cmd = argv[0].replace("kudo", "ohloh")
		del argv[0]
		target = self.return_to_sender(args)

		while True:
			if cmd == "ohloh":
				if len(argv) == 1:
					name = argv[0]
				else:
					from irclib import nm_to_n
					name = nm_to_n(args['source'])

				account = self.queryAccount(bot, name)
				if not account:
					msg = [ u"%s not found on ohloh" % name ]
					break

				try:
					kudo_rank = int(account["kudo_score"]["kudo_rank"])
					kudo_position = int(account["kudo_score"]["position"])
				except KeyError:
					kudo_rank = 1
					kudo_position = 999999

				name = account["name"]
				msg = [ u"%s has kudo lv%d #%d on ohloh, located at %s %s" % (
						name,
						kudo_rank,
						kudo_position,
						account["location"],
						account["homepage_url"]
						) ]
			elif cmd == "ohlohpk" and len(argv) > 0:
				if len(argv) == 2:
					name1, name2 = argv
				else:
					from irclib import nm_to_n
					name1, name2 = (nm_to_n(args['source']), argv[0])
				if name1.lower() == name2.lower():
					msg = [ u"Cannot pk the same ppl" ]
					break;

				# getting info
				account1 = self.queryAccount(bot, name1)
				if not account1:
					msg = [ u"%s not found on ohloh" % name1 ]
					break

				account2 = self.queryAccount(bot, name2)
				if not account2:
					msg = [ u"%s not found on ohloh" % name2 ]
					break

				# compare
				try:
					pos1 = int(account1["kudo_score"]["position"])
				except KeyError:
					pos1 = 999999
				try:
					pos2 = int(account2["kudo_score"]["position"])
				except KeyError:
					pos2 = 999999

				# result
				name1 = account1["name"]
				name2 = account2["name"]
				result = pos1 - pos2
				if result == 0:
					msg = [ u"both %s and %s are just newbie on ohloh" % (name1, name2) ]
				elif result < 0:
					msg = [ u"%s#%d ROCKS and %s#%d is catching up" % (name1, pos1, name2, pos2)  ]
				else:
					msg = [ u"%s#%d is catching up and %s#%d ROCKS" % (name1, pos1, name2, pos2)  ]
			else:
				msg = [ u"Usage: ohloh OR ohloh help OR ohloh $nick OR ohlohpk $nick1 $nick2, see http://www.ohloh.net/" ]
			break

		return Event("privmsg", "", target, msg)

class radioStatus(MooBotModule):
	url = "http://www.ladio.me/statusjson.php"
	def status(self):
		response = urllib.urlopen(self.url)
		return json.loads(response.read())

class radioOnline(radioStatus):
	def __init__(self):
		self.regex = "^radioonline"
	
	def handler(self, **args):
		status = self.status()
		users = []
		for server in status:
			for user in server['users']:
				users.append(user['nick'])

		return Event("privmsg", "", self.return_to_sender(args), [" ".join(users)])

def _test():
	import doctest
	doctest.testmod()

if __name__ == "__main__":
	_test()


# vim:set shiftwidth=4 softtabstop=4
