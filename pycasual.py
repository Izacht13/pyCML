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


SERIALIZATION_OUTPUTS = {
	"html": {
		"before": __soutf_html_before__,
		"content_text": lambda s, d: ''.join(s) if isinstance(s, list) else s,
		"content": lambda s, d: ''.join(s),
		"attribute": lambda s, d: "%s=\"%s\"" % s,
		"attributes": lambda s, d: ''.join(s) if s else '',
		"child": lambda s, d: s._serialize(SERIALIZATION_OUTPUTS["html"]),
		"children": lambda s, d: ''.join(s),
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
		self.attributes = attributes or {}
		self.parent = parent

	def get_child(self, tag):
		for child in self.children:
			if child == tag:
				return child
		return None

	def add_child(self, tag, content=None, attributes=None, children=None):
		self.children.append(Element(tag, self, content, attributes, children))
		return self.children[-1]

	def __getitem__(self, key):
		return self.attributes[''.join(key) if isinstance(key, list) else key]

	def __setitem__(self, key, value):
		self.attributes[''.join(key) if isinstance(key, list) else key] = value

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
		if callable(handlers.get("before")):
			data.update(handlers["before"](self, data) or {})
		containers = {
			"tag": "tag_text",
			"content": "content_text",
			"attributes": "attribute",
			"children": "child"
		}
		for container_name, contained_name in containers.items():
			container_handler = handlers.get(container_name)
			contained_handler = handlers.get(contained_name)
			attr = getattr(self, container_name)
			contained_list = attr.items() if isinstance(attr, dict) else attr
			items = None
			if callable(contained_handler):
				items = [contained_handler(i, data) for i in contained_list]
			elif isinstance(contained_handler, str):
				items = [contained_handler.format(source=i, **data) for i in contained_list]
			new_container = None
			if callable(container_handler):
				new_container = container_handler(items, data)
			elif isinstance(container_handler, str):
				new_container = contained_handler.format(source=items, **data)
			data[container_name] = new_container or data.get(container_name) or ''
		handler = handlers.get("element")
		if callable(handler):
			out = handler(self, data)
		elif isinstance(handler, str):
			out = handler.format(source=self, **data)
		else:
			out = ""
		if callable(handlers.get("after")):
			data.update(handlers["after"](self, data) or {})

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
		TAG = 1
		ELEMENT = 2
		ATTRIBUTE = 3
		TEXT_LIST = 4
		ATTRIBUTE_LIST = 5

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

		state = Parser.States.TAG
		substate = Parser.Substates.TEST_DEPTH
		state_data = None

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
					if state == Parser.States.ATTRIBUTE and state_data:
						context.element[state_data] = buffer.use()
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
							context.element[buffer.use()] = None
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
							context.element[buffer.use()] = None
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
						if token[1] == ':' and state != Parser.States.ELEMENT:
							if substate == Parser.Substates.INDENT:
								context.push(context.element.add_child(buffer.use()), depth)
							else:
								context.element = context.parent.add_child(buffer.use())
						elif substate == Parser.Substates.INDENT:
							state_data = buffer.use()
							context.element[state_data] = None
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
