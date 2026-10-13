"""Pure helpers shared by the web app, the API and the Telegram bot.

Standard library only: importing this package must never load Flask,
SQLAlchemy or the models, so the bot can use it without the backend.
"""
