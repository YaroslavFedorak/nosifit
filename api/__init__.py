"""The JSON API: every route under /api/.

The route modules live in api/routes/. For now the blueprints are
registered on the web app (one process, the same URLs); see
docs/architecture.md.
"""


def api_blueprints():
    # Imported on call, after the app and its extensions exist.
    from api.routes.dashboard import dashboard_api_bp
    from api.routes.dashboard_training import training_dashboard_api_bp
    from api.routes.equipment import equipment_api
    from api.routes.i18n import i18n_bp
    from api.routes.injuries import injury_api
    from api.routes.nutrition import nutrition_api
    from api.routes.onboarding import onboarding_api
    from api.routes.recovery import recovery_bp
    from api.routes.telegram import telegram_api_bp
    from api.routes.training import training_api_bp

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
