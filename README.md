# pyCML

A CML parser, and serializer.

## CML: Casual Markup Language

CML is a very simple script for defining document markup, it is designed to be 100% convertable to HTML.
CasualML shares it's syntax with the likes of YAML and Python, but in design, it is a Keskern flavored language.
(*More on Keskern later.*)


Example:

```cml
!DOCTYPE/: [html]
html:
	head:
		title: CML Example
	body:
		h1: Hello World
```

Serializes to this HTML:

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

Documentation for CML will happen *eventually*, but right now, I have to leave for work.
