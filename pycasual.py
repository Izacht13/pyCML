import re
import os


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
	pass


SERIALIZATION_OUTPUTS = {
	"html": {
		"before": __soutf_html_before__, 
		"content_text": lambda s, d: ''.join(s) if isinstance(s, list) else s,
		"attribute": lambda s, d: "%s=\"%s\"" % s,
		"attributes": lambda s, d: ' ' + ''.join(s) if s else '',
		"element": lambda s, d: (
			"<{tag}{attributes}>" + ("{content}{children}</{tag}>" if not d["single"] else '')
		).format(**d)
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
		self.attributes.append([tag, content])
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
	pass

class IndentMismatch(ParseError):
	pass

class UnknownToken(ParseError):
	pass


##############################
#/                          \#
#|     CasualML Parser      |#
#\                          /#
##############################

class Parser(object):

	class Context(list):

		def push(self, element, depth=None):
			self.append((element, depth or (self[-1][1] + 1)))

		def __getattr__(self, name):
			if name == "element":
				return self[-1][0]
			elif name == "parent":
				return self[-2][0]
			elif name == "depth":
				return self[-1][1]
			return AttributeError

		def __setattr__(self, name, value):
			if name == "element":
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

	class States:
		UNKNOWN = 0
		ELEMENT = 1
		ATTRIBUTE = 2
		TEXT_LIST = 3
		ATTRIBUTE_LIST = 4

	class Substates:
		NONE = 0
		TEST_DEPTH = 1
		INDENT = 2

	__lexemes__ = [(re.compile(x[1]), x[0]) for x in [
		(Tokens.ESCAPE, r"\\(.)"),
		(Tokens.COMMENT, r"\/{2,}\s*(([^\/\n\r])*)(\/{2,})*"),
		(Tokens.RAWSTRING, r"\"(([^\"\\]|\\.)*)\""),
		(Tokens.STRING, r"'(([^'\\\n\r]|\\.)*)'"),
		(Tokens.BRACKET, r"([\[\{])"),
		(Tokens.ENDBRACKET, r"([\]\}])"),
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
			with open(os.path.join(self.import_directory, path)) as file:
				return re.search(regex, file.read()).group(0) if regex else file.read()
		return ''

	def __init__(self, script=None, import_directory=None):
		self.script = script
		self.import_directory = import_directory or '.'

	def tokens(self, script=None):
		"""Returns a generator of tokens matched in the script."""
		self.script = script or self.script
		if not self.script:
			return

		index = 0
		script_length = len(self.script)

		while True:
			for lexeme in Parser.__lexemes__:
				match = lexeme[0].match(self.script[index:])
				if match:
					index += match.span()[1] - 1
					yield (lexeme[1], match.group(1), index)
					break

			if index < script_length:
				index += 1
			else:
				break

	def parse(self, script=None, preprocess=True, *, import_directory=None, tokens=None):
		self.script = script or self.script
		self.import_directory = import_directory or self.import_directory
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
		buffer = Parser.TokenBuffer()
		depth = 0

		state = Parser.States.ELEMENT
		substate = Parser.Substates.TEST_DEPTH

		last_break = None
		last_indent = None

		context = Parser.Context()
		context.push(root, -1)

		while token:
			if substate == Parser.Substates.TEST_DEPTH:
				if token[0] == Parser.Tokens.SPACE:
					if last_indent and token[1] != last_indent[1]:
						raise IndentMismatch
					depth += 1
					last_indent = token
				else:
					substate = Parser.Substates.NONE
					if state != Parser.States.TEXT_LIST:
						while depth < context.depth:
							context.pop()
						if depth > context.depth:
							substate = Parser.Substates.INDENT
					continue
			else:
				if token[0] in [Parser.Tokens.LINEBREAK, Parser.Tokens.BREAK]:
					if state == Parser.States.ATTRIBUTE:
						context.element.attributes[-1][1] = buffer.use()
						state = Parser.States.ELEMENT
						state_data = None

					if state == Parser.States.TEXT_LIST:
						if token[0] == Parser.Tokens.LINEBREAK:
							if buffer[-1][0] != Parser.Tokens.BREAK:
								buffer.push(last_break)
						else:
							buffer.push(token)
							last_break = token
					else:
						if token[0] == Parser.Tokens.LINEBREAK:
							depth = 0
							substate = Parser.Substates.TEST_DEPTH
						elif token[1] == ',' and state == Parser.States.ATTRIBUTE_LIST:
							context.element.add_attribute(buffer.use())
					if buffer:
						context.element.content.append(buffer.use())
				elif token[0] == Parser.Tokens.BRACKET:
					if buffer:
						context.element.content.append(buffer.use())
					if state == Parser.States.ELEMENT:
						if token[1] == '[':
							states = Parser.States.ATTRIBUTE_LIST
						else:
							states = Parser.States.TEXT_LIST
					else:
						buffer.push(token)
				elif token[0] == Parser.Tokens.ENDBRACKET:
					if token[1] == ']' and state == Parser.States.ATTRIBUTE_LIST:
						if buffer:
							context.element.add_attribute(buffer.use())
						state = Parser.States.ELEMENT
					elif state == Parser.States.TEXT_LIST:
						if buffer:
							context.element.content.append(buffer.use())
						state = Parser.States.ELEMENT
						last_break = None
				elif token[0] == Parser.Tokens.TAG:
					if state == Parser.States.TEXT_LIST:
						buffer.push(token)
					else:
						if token[1] == ':' and state == Parser.States.ELEMENT:
							if substate == Parser.Substates.INDENT:
								context.push(context.element.add_child(buffer.use()), depth)
							else:
								context.element = context.parent.add_child(buffer.use())
							state = Parser.States.ELEMENT
						elif state in [Parser.States.ELEMENT, Parser.States.ATTRIBUTE_LIST]:
							context.element.add_attribute(buffer.use())
							state = Parser.States.ATTRIBUTE
				elif token[0] == Parser.Tokens.COMMENT:
					pass
				elif token[0] == Parser.Tokens.UNKNOWN:
					raise UnknownToken
				else:
					buffer.push(token)

			token = next(tokens, None)

		return root


def parse(script=None):
	return Parser(script).parse()
