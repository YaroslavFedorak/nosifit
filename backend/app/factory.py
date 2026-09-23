from flask import Flask

from backend.app.extensions import db


def create_backend_app():
    app = Flask(__name__)
    app.config.from_object("backend.config.Config")
    db.init_app(app)
    return app