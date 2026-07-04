"""Holds the running PTB Application so API routes can talk to Telegram."""

from telegram.ext import Application

_application: Application | None = None


def set_application(application: Application | None) -> None:
    global _application
    _application = application


def get_application() -> Application | None:
    return _application
