import html
import re

ANSI_SGR_COLORS = {
        30: "black", 31: "red", 32: "green", 33: "orange", 34: "blue",
        35: "magenta", 36: "cyan", 37: "lightgray", 90: "gray",
        91: "lightcoral", 92: "lightgreen", 93: "yellow", 94: "lightskyblue",
        95: "plum", 96: "paleturquoise", 97: "white"
    }

def ansi_to_html(text: str) -> str:
    """
    Very small ANSI SGR -> HTML converter.
    Handles sequences like \x1b[31m (red) and \x1b[0m (reset) and bold (1).
    Other sequences are removed.
    """
    text = html.escape(text)
    sgr_re = re.compile(r'\\x1B\\[([0-9;]*)m')
    parts = []
    last_pos = 0
    open_spans = []

    for m in sgr_re.finditer(text):
        start, end = m.span()
        params = m.group(1)
        parts.append(text[last_pos:start])
        last_pos = end

        if params == '' or params == '0':
            while open_spans:
                parts.append("</span>")
                open_spans.pop()
        else:
            attrs = params.split(';')
            style_attrs = []
            for a in attrs:
                try:
                    ai = int(a)
                except:
                    continue
                if ai == 1:
                    style_attrs.append("font-weight:700")
                elif 30 <= ai <= 37 or 90 <= ai <= 97:
                    color = ANSI_SGR_COLORS.get(ai, None)
                    if color:
                        style_attrs.append(f"color:{color}")
                elif ai == 39:
                    pass
            if style_attrs:
                parts.append(f"<span style=\"{';'.join(style_attrs)}\">")
                open_spans.append(True)

    parts.append(text[last_pos:])
    while open_spans:
        parts.append("</span>")
        open_spans.pop()
    return ''.join(parts).replace('\\n', '<br/>').replace('  ', '&nbsp;&nbsp;')