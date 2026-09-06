"""DB-free tests for the model-Markdown to Telegram-HTML conversion."""

from app.bot.formatting import to_telegram_html


def test_inline_marks_become_telegram_tags():
    rendered = to_telegram_html("**Хватит** ждать: *действуй* и ~~молчи~~ про `plan_b`.")

    assert (
        rendered == "<b>Хватит</b> ждать: <i>действуй</i> и <s>молчи</s> про <code>plan_b</code>."
    )


def test_headings_and_bullets_degrade_to_what_telegram_has():
    rendered = to_telegram_html("## Три шага\n- первый\n* второй\n\n---\n\nвсё")

    # The rule is dropped and the blank run collapses to a single empty line.
    assert rendered == "<b>Три шага</b>\n• первый\n• второй\n\nвсё"


def test_links_and_quotes():
    rendered = to_telegram_html(
        "> Ты имеешь власть над разумом\n\n[источник](https://example.com/a?b=1&c=2)"
    )

    assert "<blockquote>Ты имеешь власть над разумом</blockquote>" in rendered
    assert '<a href="https://example.com/a?b=1&amp;c=2">источник</a>' in rendered


def test_html_in_the_answer_is_escaped_not_executed():
    rendered = to_telegram_html("Сравни <b>это</b> и <script>alert(1)</script> с 5 < 7.")

    assert "<b>это</b>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "5 &lt; 7" in rendered


def test_code_block_keeps_its_content_verbatim():
    rendered = to_telegram_html("Вот:\n```python\nif a < b:\n    **not bold**\n```")

    assert (
        '<pre><code class="language-python">if a &lt; b:\n    **not bold**</code></pre>' in rendered
    )


def test_partial_stream_chunk_still_parses():
    # A stream cut mid-emphasis must not leave an unclosed tag behind.
    assert to_telegram_html("Слушай: **очень важ") == "Слушай: <b>очень важ</b>"
    assert to_telegram_html("Код: `pip inst") == "Код: <code>pip inst</code>"
    assert to_telegram_html("```py\nx = 1") == '<pre><code class="language-py">x = 1</code></pre>'


def test_underscores_inside_words_are_left_alone():
    rendered = to_telegram_html("Поле reminder_hour и файл my_file_name.py")

    assert rendered == "Поле reminder_hour и файл my_file_name.py"


def test_empty_input_is_empty_output():
    assert to_telegram_html("") == ""
    assert to_telegram_html(None) == ""
