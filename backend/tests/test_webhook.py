"""DB-free tests for the Telegram webhook secret check."""

import pytest

from app import main


@pytest.mark.parametrize("header", ["", None, "anything"])
def test_webhook_refuses_everything_without_a_secret(monkeypatch, header):
    """Polling mode has no secret: an empty header must not equal the empty secret."""
    monkeypatch.setattr(main, "_webhook_secret", "")
    assert main._webhook_authorized(header) is False


@pytest.mark.parametrize(
    ("header", "expected"),
    [("s3cret", True), ("S3CRET", False), ("", False), (None, False), ("s3cret ", False)],
)
def test_webhook_matches_the_configured_secret(monkeypatch, header, expected):
    monkeypatch.setattr(main, "_webhook_secret", "s3cret")
    assert main._webhook_authorized(header) is expected
