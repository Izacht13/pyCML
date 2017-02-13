# pyCasual

*A CasualML parser, and serializer, for Python 3.5+.*

The parser outputs a DOM-like object tree that closly mirrors the structure of the script.


## The Script

CasualML, or *Casual Markup Language* is a very simple alternative to static HTML, with planned dynamic features. Its bracket-less syntax barrows from the likes of YAML and Python.


## The Parser

CasualML is a side project I started because I was annoyed with the verbosity of HTML. The first working parser turned CasualML into HTML on the fifth of January 2017, since then it has been rewritten two times before finally being posted here on Github, where it will now live and continue to grow.

The parser can now successfully turn this CML:

```cml
!DOCTYPE/: [html]
html:
	head:
		title: Casual Example
	body:
		h1: Hello World
```

Into this HTML:

```html
<!DOCTYPE html>
<html>
	<head>
		<title>Casual Example</title>
	</head>
	<body>
		<h1>Hello World</h1>
	</body>
</html>
```

(*Well almost, the actual output is unformatted.*)


## Pluggable/Hackable

- ~~New "Tag Functions" can be added easily to a global dictionary.~~
- The script's tokens can be easily accessed from the main parser class, via a generator.
- New serialiation schemes can be added, using a global dict.
	
	
## Planned Features
- [ ] Attribute/element shortcuts to be defined in-script as root attributes.
- [ ] Scripting.
- [x] File Imports (CSS, JS, HTML, CML etc.)
- [x] Re-add pluggable serialization.
