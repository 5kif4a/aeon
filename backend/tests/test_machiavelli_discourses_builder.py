from scripts.build_machiavelli_discourses_en_rag import (
    clean_page_text,
    normalize_roman,
    overridden_page_sections,
    page_sections,
)


def test_normalize_roman_repairs_lowercase_l_ocr():
    assert normalize_roman("l") == "I"
    assert normalize_roman("XLIX") == "XLIX"


def test_clean_page_text_removes_running_header():
    raw = (
        "CH.  IV.]  TITUS  LIVIUS.  21\n"
        "The dissensions between the Senate and Commons made Rome free.\n"
    )

    assert clean_page_text(raw) == (
        "The dissensions between the Senate and Commons made Rome free."
    )


def test_page_sections_updates_chapter_and_keeps_prefix():
    text = "End of the preface. Chapter l.-Of the Beginnings of Cities. The argument."

    sections = page_sections(text, 1, "Book 1, Preface")

    assert sections == [
        ("Book 1, Preface", "End of the preface."),
        ("Book 1, Chapter I", "Chapter l.-Of the Beginnings of Cities. The argument."),
    ]


def test_page_sections_does_not_treat_prose_as_a_heading():
    text = "As shown in the previous chapter concerning liberty, the people understood this."

    assert page_sections(text, 1, "Book 1, Chapter IV") == [
        ("Book 1, Chapter IV", text)
    ]


def test_overridden_page_sections_repairs_ocr_heading_and_preserves_prefix():
    text = "End of Chapter X. Chapter XL-0/ the Religion of the Romans. New argument."

    assert overridden_page_sections(text, 1, "XI", "Book 1, Chapter X") == [
        ("Book 1, Chapter X", "End of Chapter X."),
        ("Book 1, Chapter XI", "Chapter XL-0/ the Religion of the Romans. New argument."),
    ]
