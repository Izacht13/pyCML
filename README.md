# pyCML

*A CML parser, and serializer, written in python.*

The parser outputs a DOM-like object tree that closly mirrors the structure of the script.


## The Script

CML, or *Casual Markup Language* is a very simple alternative to static HTML, with planned dynamic features. It's bracket-less syntax barrows from the likes of YAML and Python, and it's design is Keskern flavored.


## The Parser

CML is a side project I started because I was annoyed with the verbosity of HTML. The first working parser turned CML into HTML on the fifth of January 2017, since then it has been rewritten two times before finally being posted here on Github, where it will now live and continue to grow.

The parser can now successfully turn this CML:

```cml
!DOCTYPE/: [html]
html:
	head:
		title: CML Example
	body:
		h1: Hello World
```

Into this HTML:

```html
<!DOCTYPE html>
<html>
	<head>
		<title>HTML Example</title>
	</head>
	<body>
		<h1>Hello World</h1>
	</body>
</html>
```

(*Well almost, the actual output is unformatted.*)


## Special Features:

CasualML also has some special features that transform the output to make document markup even easier.

**Currently Implemented:**

- Iterative child element creation, using the text of the parent.
- Iterative sibling creation, using the children of the original element.
- Shortcuts for `id` and `class` attributes, similar to CSS.


## Pluggable/Hackable

- New "Tag Functions" can be added easily to a global dictionary.
- The script's tokens can be easily accessed from the main parser class, via a generator.
- ~~New serialiation schemes can be added, using a global dict.~~
  ^^^ Removed because the implentation was buggy and messy, will hopefully return again soon.
	
	
## Planned Features
- [ ] Attribute/element shortcuts to be defined in-script as root attributes.
- [ ] Scripting.
- [ ] File Imports (CSS, JS, HTML, CML etc.)
- [ ] Re-add pluggable serialization.
