"""Sign-in session rules shared by the pages (web) and the API (api).

Both write and check the same Flask-Login session, so the rules live here
rather than in either of them. Like core, this package imports neither
web nor api.
"""
