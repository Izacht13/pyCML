import re
import os
import html


##############################
#/                          \#
#|  Serialization Outputs   |#
#\                          /#
##############################


def __soutf_html_before__(source, data):
	data["tag"] = ''.join(source.tag).strip() or "div"
	if data["tag"][-1] == '/':
		data["tag"] = data["tag"][:-1]
		data["single"] = True
	else:
		data["single"] = False

def __soutf_html_content_text(source, data):
	if isinstance(source, list):
		return ''.join([__soutf_html_content_text(text, data) for text in source])
	else:
		if source == '\n':
			return "<br>"
		return source


SERIALIZATION_OUTPUTS = {
	"html": {
		"before": __soutf_html_before__, 
		"content_text": __soutf_html_content_text,
		"attribute": "{source[0]}=\"{source[1]}\"",
		"attributes": lambda s, d: ' ' + ' '.join(s) if s else '',
		"element": lambda s, d: (
			"<{tag}{attributes}>" + ("{content}{children}</{tag}>" if not d["single"] else '')
		).format(**d)
	},
	"json": {
		"tag": lambda s, d: "\"tag\":\"%s\"" % ''.join(s),
		"content_text": lambda s, d: ''.join(s) if isinstance(s, list) else s,
		"content": lambda s, d: "\"content\":\"%s\"" % ''.join(s),
		"attribute": "\"{source[0]}\":\"{source[1]}\"",
		"attributes": lambda s, d: "\"attributes\":{" + ','.join(s) + "}",
		"children": lambda s, d: "\"children\":[" + ','.join(s) + "]",
		"element": "{{{tag},{content},{attributes},{children}}}"
	}
}


##############################
#/                          \#
#|      Tag Functions       |#
#\                          /#
##############################


def __tfunc_shortcut__(element, tag, args):
	pass


##############################
#/                          \#
#|       Tree Objects       |#
#\                          /#
##############################


class Element(object):

	def __init__(self, tag=None, parent=None, content=None, attributes=None, children=None):
		self.tag = tag or []
		self.content = content or []
		self.children = children or []
		if isinstance(attributes, dict):
			self.attributes = [[key, value] for key, value in attributes.items()]
		else:
			self.attributes = attributes or []
		self.parent = parent

	def get_child(self, tag):
		for child in self.children:
			if child == tag:
				return child
		return None

	def add_child(self, tag, content=None, attributes=None, children=None):
		self.children.append(Element(tag, self, content, attributes, children))
		return self.children[-1]

	def get_attribute(self, tag):
		for attribute in self.attributes:
			if attribute[0] == tag:
				return attribute
		return None

	def add_attribute(self, tag, content=None):
		self.attributes.append([tag, content or []])
		return self.attributes[-1]

	def __getitem__(self, key):
		return self.get_attribute(key) 

	def __setitem__(self, key, value):
		self.set_attribute(key, value)

	def __eq__(self, x):
		if isinstance(x, Element):
			return self.tag == x.tag
		return self.tag == x

	def __iter__(self):
		yield from self.children

	def __str__(self):
		return self.serialize()

	def __getattr__(self, key):
		if key in SERIALIZATION_OUTPUTS:
			return self.serialize(key)
		else: raise AttributeError

	def serialize(self, output="html", skiproot=True, *, handlers=None, **kwargs):
		handlers = handlers or SERIALIZATION_OUTPUTS.get(output)
		if not handlers: return ''
		return ''.join([
			c._serialize(handlers, **kwargs) for c in self.children
		]) if skiproot else self._serialize(handlers, **kwargs)

	def _serialize(self, handlers, **kwargs):
		data = kwargs or {}

		def handle(handler_name, source, container=False, allow_str=True, default="{source}"):
			handler = handlers.get(handler_name) or default
			if callable(handler):
				return [
					handler(i, data) for i in source
				] if container else handler(source, data)
			elif allow_str and isinstance(handler, str):
				return [
					handler.format(source=i, **data) for i in source
				] if container else handler.format(source=source, **data)

		data.update(handle("before", self, False, False, None) or {})

		items = handle("tag_text", self.tag, True)
		data["tag"] = handle("tag", items, default=lambda s, d: ''.join(s)) or data.get("tag") or ''

		items = handle("content_text", self.content, True)
		data["content"] = handle("content", items, default=lambda s, d: ''.join(s)) or data.get("content") or ''

		items = [
			handle("attribute", (
				handle(
					"attribute_tag",
					handle("attribute_tag_text", a[0], True),
					default=lambda s, d: ''.join(s)
				) or '',
				handle(
					"attribute_content",
					handle("attribute_content_text", a[1], True),
					default=lambda s, d: ''.join(s)
				) or ''
			)) for a in self.attributes
		]
		data["attributes"] = handle("attributes", items, default=lambda s, d: ''.join(s)) or data.get("attributes") or ''

		items = handle("child", self.children, True, default=lambda s, d: s._serialize(handlers, **kwargs))
		data["children"] = handle("children", items, default=lambda s, d: ''.join(s)) or data.get("children") or ''

		output = handle("element", self) or ''
		handle("after", self, False, False, None)
		return output

		return out


##############################
#/                          \#
#|       Exceptions         |#
#\                          /#
##############################


class ParseError(BaseException):
	"""Base exception for errors of the parser."""
	def __init__(self, message, *args):
		super().__init__(*args)
		self.message = message

class IndentMismatch(ParseError):
	"""Raised when both spaces and tabs are used in script indentation."""

class UnknownToken(ParseError):
	"""Raised when an unsupported character is found in the script."""

class ParseStateError(ParseError):
	"""Base exceptions for parser state related errors."""

class UnknownLineState(ParseStateError):
	"""Raised when the parser finds itself in an unknown line state."""

class UnexpectedContextTarget(ParseStateError):
	"""Raised when the current context target is of the wrong type."""
	def __init__(self, message=None, expected=None, got=None, *args):
		super().__init__(message or "Expected {expected}, got {got}.", *args)
		if isinstance(expected, list):
			if len(expected) > 2:
				expected = ', '.join(expected[:-1]) + " or " + expected[-1]
			else:
				expected = " or ".join(expected)
		self.message = self.message.format(expected=expected, got=got)


##############################
#/                          \#
#|     CasualML Parser      |#
#\                          /#
##############################

class Parser(object):

	class Context(list):

		class Type:
			UNKNOWN = 0
			ELEMENT = 1
			ATTRIBUTE = 2
			TEXT_LIST = 3
			ATTRIBUTE_LIST = 4

		def istype(self, *args):
			for type in args:
				if self[-1][2] != type:
					return False
			return True

		def swap(self, target, type=None):
			if not type:
				type = self.Type.ELEMENT if isinstance(target, Element) else self.Type.UNKNOWN
			self[-1] = (target, self[-1][1], type)

		def push(self, target=None, depth=None, type=None):
			if not type:
				type = self.Type.ELEMENT if isinstance(target, Element) else self.Type.UNKNOWN
			self.append((target, depth or (self[-1][1] + 1), type))

		def add_child(self, tag, content=None, attributes=None, children=None):
			if self.istype(self.Type.ELEMENT):
				return self.target.add_child(tag, content, attributes, children)
			raise UnexpectedContextTarget(expected=self.Type.ELEMENT, got=self.type)
		
		def add_attribute(self, tag, content=None):
			if self.istype(self.Type.ELEMENT):
				return self.target.add_attribute(tag, content)
			elif self.istype(self.Type.ATTRIBUTE_LIST):
				if self[-2][2] != self.Type.ELEMENT:
					raise UnexpectedContextTarget(expected=self.Type.ELEMENT, got=self[-2][2])
				return self[-2][0].add_attribute(tag, content)
			else:
				raise UnexpectedContextTarget(expected=[self.Type.ELEMENT, self.Type.ATTRIBUTE_LIST], got=self.type)
		
		def get_child(self, tag):
			if self.istype(self.Type.ELEMENT):
				return self.target.get_child(tag, content)
			raise UnexpectedContextTarget(expected=self.Type.ELEMENT, got=self.type)

		def get_attribute(self, tag):
			if self.istype(self.Type.ELEMENT):
				return self.target.get_attribute(tag, content)
			raise UnexpectedContextTarget(expected=self.Type.ELEMENT, got=self.type)

		def use_buffer(self, buffer):
			if self.istype(self.Type.ELEMENT):
				self.target.content.append(buffer.use())
			elif self.istype(self.Type.ATTRIBUTE):
				self.target[1] = buffer.use()
			elif self.istype(self.Type.ATTRIBUTE_LIST):
				if self[-2][2] != self.Type.ELEMENT:
					raise UnexpectedContextTarget
				self[-2][0].add_attribute(buffer.use())
			elif self.istype(self.Type.TEXT_LIST):
				if self[-2][2] not in [Type.ELEMENT, self.Type.ATTRIBUTE]:
					raise UnexpectedContextTarget
				self[-2][0].content.append(buffer.use())
			else:
				raise UnexpectedContextTarget(expected=[
					self.Type.ELEMENT,
					self.Type.ATTRIBUTE,
					self.Type.ATTRIBUTE_LIST,
					self.Type.TEXT_LIST
				], got=self.type)

		def __getattr__(self, name):
			if name == "target":
				return self[-1][0]
			elif name == "parent":
				if self[-2][2] == self.Type.ELEMENT:
					return self[-2][0]
				raise UnexpectedContextTarget(expected=self.Type.ELEMENT, got=self[-2][2])
			elif name == "depth":
				return self[-1][1]
			elif name == "type":
				return self[-1][2]
			raise AttributeError

		def __setattr__(self, name, value):
			if name == "target":
				self[-1] = (value, self[-1][1])
			else:
				super().__setattr__(name, value)

	class TokenBuffer(object):

		def __init__(self, stack=None):
			self.stack = stack or []

		def use(self):
			s = self.stack
			self.stack = []
			return [i[1] for i in s]

		def push(self, token):
			self.stack.append(token)

		def pop(self):
			return self.stack.pop()
		
		def __bool__(self):
			return bool(self.stack)

		def __str__(self):
			return self.stack.__str__()

	class Tokens:
		UNKNOWN = 0
		ESCAPE = 1
		COMMENT = 2
		RAWSTRING = 3
		STRING = 4
		BRACKET = 5
		ENDBRACKET = 6
		LINEBREAK = 7
		BREAK = 8
		TAG = 9
		SPACE = 10
		WORD = 11
		SYMBOL = 12

	class LineStates:
		UNKNOWN = 0
		TEST_DEPTH = 1
		INDENT = 2
		EQUAL = 3

	__lexemes__ = [(re.compile(x[1]), x[0]) for x in [
		(Tokens.ESCAPE, r"\\(.)"),
		(Tokens.COMMENT, r"\/{2,}\s*(([^\/\n\r])*)(\/{2,})*"),
		(Tokens.RAWSTRING, r"\"(([^\"\\]|\\.)*)\""),
		(Tokens.STRING, r"'(([^'\\\n\r]|\\.)*)'"),
		(Tokens.BRACKET, r"([\[\{])[ \t\f\v]*"),
		(Tokens.ENDBRACKET, r"([\]\}])[ \t\f\v]*"),
		(Tokens.LINEBREAK, r"([\n\r]+)"),
		(Tokens.BREAK, r"([,;])[ \t\f\v,;]*"),
		(Tokens.TAG, r"([:=])[ \t\f\v]*"),
		(Tokens.SPACE, r"([ \t\f\v])"),
		(Tokens.WORD, r"(\w+)"),
		(Tokens.SYMBOL, r"([\!\@\#\$\%\^\&\*\?\/\.\+\-\|\~\(\)\`<>])"),
		(Tokens.UNKNOWN, r"(.)")
	]]

	def __import(self, match):
		path = match.group(1)
		regex = match.group(2)
		if path:
			for directory in self.import_directories:
				try:
					with open(os.path.join(directory, path)) as file:
						return re.search(regex, file.read()).group(0) if regex else file.read()
				except Exception:
					continue
		return ""

	def __init__(self, script=None, import_directory=None):
		self.script = script
		self.import_directory = import_directory or ['.']

	def tokens(self, script=None):
		"""Returns a generator of tokens matched in the script."""
		self.script = script or self.script
		if not self.script:
			return

		index = 0
		script_length = len(self.script)

		while True:
			for lexeme in self.__lexemes__:
				match = lexeme[0].match(self.script[index:])
				if match:
					index += match.span()[1] - 1
					yield (lexeme[1], match.group(1), index)
					break

			if index < script_length:
				index += 1
			else:
				break

	def parse(self, script=None, preprocess=True, *, import_directories=None, tokens=None):
		self.script = script or self.script
		self.import_directories = import_directories or self.import_directories
		if not self.script:
			return
		else:
			self.script = re.sub(
				r"<<[ \t\f\v\.\/\\]*([^>\n\r~]+)~? *([^>\n\r]*)(>>)?"
				, self.__import, self.script
			)
			self.script += ';'

		tokens = tokens or self.tokens()
		if not tokens: return
		token = next(tokens, None)

		root = Element()
		buffer = self.TokenBuffer()
		depth = 0

		linestate = self.LineStates.TEST_DEPTH

		last_break = None
		last_indent = None

		context = self.Context()
		context.push(root, -1)

		while token:
			if linestate == self.LineStates.UNKNOWN:
				raise UnknownLineState
			elif linestate == self.LineStates.TEST_DEPTH:
				if token[0] == self.Tokens.SPACE:
					if last_indent and token[1] != last_indent[1]:
						raise IndentMismatch
					depth += 1
					last_indent = token
				elif depth > -1:
					if not context.istype(self.Context.Type.TEXT_LIST):
						while depth < context.depth:
							context.pop()
						if depth > context.depth:
							linestate = self.LineStates.INDENT
						elif depth == context.depth:
							linestate = self.LineStates.EQUAL
					continue
			else:
				if token[0] in [self.Tokens.LINEBREAK, self.Tokens.BREAK, self.Tokens.ENDBRACKET]:
					if context.istype(self.Context.Type.ATTRIBUTE):
						context.use_buffer(buffer)
						context.pop()

					if context.istype(self.Context.Type.TEXT_LIST):
						if token[0] == self.Tokens.LINEBREAK:
							if buffer[-1][0] != self.Tokens.BREAK:
								buffer.push(last_break)
						else:
							buffer.push(token)
							last_break = token
					elif token[0] == self.Tokens.LINEBREAK:
						depth = 0
						linestate = self.LineStates.TEST_DEPTH
					elif token[0] == self.Tokens.ENDBRACKET:
						if context.istype(self.Context.Type.TEXT_LIST, self.Context.Type.ATTRIBUTE_LIST):
							last_break = None
							context.pop()
					if buffer:
						context.use_buffer(buffer)
				elif token[0] == self.Tokens.BRACKET:
					if buffer:
						context.use_buffer(buffer)
					if context.istype(self.Context.Type.ELEMENT):
						if token[1] == '[':
							context.push(type=self.Context.Type.ATTRIBUTE_LIST)
						else:
							context.push(type=self.Context.Type.TEXT_LIST)
					else:
						buffer.push(token)
				elif token[0] == self.Tokens.TAG:
					if context.istype(self.Context.Type.TEXT_LIST):
						buffer.push(token)
					else:
						if token[1] == ':':
							if linestate == self.LineStates.INDENT:
								context.push(context.add_child(buffer.use()), depth, self.Context.Type.ELEMENT)
							else:
								context.swap(context.parent.add_child(buffer.use()), self.Context.Type.ELEMENT)
						else:
							if linestate == self.LineStates.INDENT:
								context.push(context.add_attribute(buffer.use()), depth, self.Context.Type.ATTRIBUTE)
							else:
								context.swap(context.parent.add_attribute(buffer.use()), self.Context.Type.ATTRIBUTE)
				elif token[0] == self.Tokens.COMMENT:
					pass
				elif token[0] == self.Tokens.UNKNOWN:
					raise UnknownToken
				elif token[0] == self.Tokens.ESCAPE:
					control = {
						'n': '\n',
						'f': '\f',
						'v': '\v',
						't': '\t'
					}.get(token[1])
					buffer.push((token[0], control or token[1], token[2]))
				else:
					buffer.push(token)

			token = next(tokens, None)

		return root


def parse(script=None, **kwargs):
	return Parser(script).parse(**kwargs)
