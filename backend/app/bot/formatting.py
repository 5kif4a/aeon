"""Model Markdown to Telegram HTML.

Gemini answers in Markdown, Telegram renders only a small HTML subset, and its
parser rejects the whole message on the first stray tag - which during streaming
happens constantly, because the text is cut mid-word. So the conversion escapes
everything first, emits only tags Telegram documents, and balances markers that
are still open, letting a half-finished answer render as valid HTML.

Supported: fenced and inline code, bold, italic, strike, links, headings (as
bold lines), bullets, blockquotes. Everything else degrades to plain text.
"""

import html
import re

# Telegram's own list: b, i, u, s, a, code, pre, blockquote, tg-spoiler.
_CODE_BLOCK = re.compile(r"```([\w+-]*)\n?(.*?)```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`\n]+?)`")
_BOLD = re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*", re.DOTALL)
_BOLD_UNDERSCORE = re.compile(r"(?<![\w_])__(?!\s)(.+?)(?<!\s)__(?![\w_])", re.DOTALL)
_ITALIC_STAR = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])")
_ITALIC_UNDERSCORE = re.compile(r"(?<![\w_])_(?!\s)([^_\n]+?)(?<!\s)_(?![\w_])")
_STRIKE = re.compile(r"~~(?!\s)(.+?)(?<!\s)~~", re.DOTALL)
_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
_BULLET = re.compile(r"^(\s*)[-*+•]\s+(?=\S)")
_RULE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_QUOTE = re.compile(r"^\s*>\s?")

_BLANK_LINES = re.compile(r"\n{3,}")

_PLACEHOLDER = "\x00{}\x00"


def to_telegram_html(text: str) -> str:
    """Render model Markdown as Telegram-safe HTML."""
    source = _balance_markers(str(text or ""))
    blocks: list[str] = []

    def _stash_code_block(match: re.Match) -> str:
        language, body = match.group(1), match.group(2)
        attribute = f' class="language-{html.escape(language)}"' if language else ""
        blocks.append(f"<pre><code{attribute}>{html.escape(body.strip('\n'))}</code></pre>")
        return _PLACEHOLDER.format(len(blocks) - 1)

    def _stash_inline_code(match: re.Match) -> str:
        blocks.append(f"<code>{html.escape(match.group(1))}</code>")
        return _PLACEHOLDER.format(len(blocks) - 1)

    # Code is taken out first: nothing inside it may be read as Markdown.
    source = _CODE_BLOCK.sub(_stash_code_block, source)
    source = _INLINE_CODE.sub(_stash_inline_code, source)

    # Escaping is per line, after quote grouping, so `>` is still readable as Markdown.
    # Placeholders are NUL-delimited digits, so escaping leaves them intact.
    rendered = "\n".join(_render_group(quoted, group) for quoted, group in _group_quotes(source))
    for index, block in enumerate(blocks):
        rendered = rendered.replace(_PLACEHOLDER.format(index), block)
    # Dropped rules and heading marks leave holes; one blank line is enough anywhere.
    return _BLANK_LINES.sub("\n\n", rendered).strip()


def _balance_markers(text: str) -> str:
    """Close markers a streaming chunk left open, so the partial text still parses."""
    if text.count("```") % 2:
        text = f"{text}\n```"
    if text.count("`") % 2:
        text = f"{text}`"
    if text.count("**") % 2:
        text = f"{text}**"
    return text


def _group_quotes(text: str) -> list[tuple[bool, list[str]]]:
    """Consecutive `> ` lines become one quoted group; every other line stands alone."""
    groups: list[tuple[bool, list[str]]] = []
    quoted: list[str] = []
    for line in text.split("\n"):
        if _QUOTE.match(line):
            quoted.append(_QUOTE.sub("", line))
            continue
        if quoted:
            groups.append((True, quoted))
            quoted = []
        groups.append((False, [line]))
    if quoted:
        groups.append((True, quoted))
    return groups


def _render_group(quoted: bool, lines: list[str]) -> str:
    body = "\n".join(_render_line(html.escape(line)) for line in lines)
    return f"<blockquote>{body}</blockquote>" if quoted else body


def _render_line(line: str) -> str:
    if _RULE.match(line):
        return ""
    heading = _HEADING.match(line)
    if heading:
        # Telegram has no headings; a bold line is the closest honest equivalent.
        return f"<b>{_inline(heading.group(1))}</b>" if heading.group(1) else ""
    line = _BULLET.sub(r"\1• ", line)
    return _inline(line)


def _inline(text: str) -> str:
    text = _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', text)
    text = _BOLD.sub(r"<b>\1</b>", text)
    text = _BOLD_UNDERSCORE.sub(r"<b>\1</b>", text)
    text = _STRIKE.sub(r"<s>\1</s>", text)
    text = _ITALIC_STAR.sub(r"<i>\1</i>", text)
    text = _ITALIC_UNDERSCORE.sub(r"<i>\1</i>", text)
    return text
