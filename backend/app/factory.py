import os

from dotenv import load_dotenv
from flask import Flask

from backend.app.extensions import db

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def create_backend_app():
    app = Flask(__name__)
    app.config.from_object("backend.config.Config")
    db.init_app(app)
    return app
