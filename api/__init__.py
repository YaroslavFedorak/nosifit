"""The JSON API: every route under /api/.

For now its blueprints are registered on the web app (one process, the same
URLs) and still live under web/app/routes/. They move into this package one
module at a time; see docs/architecture.md.
"""


def api_blueprints():
    # Imported on call, after the app and its extensions exist.
    from api.routes.equipment import equipment_api
    from api.routes.injuries import injury_api
    from web.app.routes import (
        dashboard_api_bp,
        i18n_bp,
        nutrition_api,
        onboarding_api,
        recovery_bp,
        telegram_api_bp,
        training_api_bp,
        training_dashboard_api_bp,
    )

    return (
        telegram_api_bp,
        i18n_bp,
        dashboard_api_bp,
        training_dashboard_api_bp,
        training_api_bp,
        nutrition_api,
        recovery_bp,
        equipment_api,
        onboarding_api,
        injury_api,
    )


def register_api(app):
    for blueprint in api_blueprints():
        app.register_blueprint(blueprint)
