from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import ClassNotFound, get_lexer_by_name


def highlight_code(code, name, attrs, markata=None):
    """Code highlighter for markdown-it-py."""

    try:
        lexer = get_lexer_by_name(name or "text")
    except ClassNotFound:
        lexer = get_lexer_by_name("text")

    import re

    pattern = r'(\w+)\s*=\s*(".*?"|\S+)'
    matches = re.findall(pattern, attrs)
    attrs = dict(matches)

    if attrs.get("hl_lines"):
        formatter = HtmlFormatter(hl_lines=attrs.get("hl_lines"))
    else:
        formatter = HtmlFormatter()

    copy_button = f"""<button class='copy' title='copy code to clipboard' onclick="navigator.clipboard.writeText(this.parentElement.parentElement.querySelector('pre').textContent)">{COPY_ICON}</button>"""


    if attrs.get("help"):
        help = f"""
        <a href={attrs.get('help').strip('<').strip('>').strip('"').strip("'")} title='help link' class='help'>{HELP_ICON}</a>
        """
    else:
        help = ""
    if attrs.get("title"):
        file = f"""
<div class='filepath'>
<div class='right'>
{help}
{copy_button}
</div>
</div>
"""
    else:
        file = f"""
<div class='copy-wrapper'>
{help}
{copy_button}
</div>
        """
    return f"""<pre class='wrapper'>
{file}
{highlight(code, lexer, formatter)}
</pre>
"""
