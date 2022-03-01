from markdown import markdown


base_markdown = open('content/base.md').read()
base_html = open('base.html').read()

sources = {
  'content/index.md': 'index.html',
}

for markdown_source, html_target in sources.items():
  content_markdown = open(markdown_source).read()
  rendered_markdown = markdown(content_markdown) % {'content': markdown(markdown_source)}
  with open(html_target, 'w') as f:
    f.write(base_html % {'content': rendered_markdown})
