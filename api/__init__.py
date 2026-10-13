"""The JSON API: every route under /api/.

The route modules live in api/routes/. For now the blueprints are
registered on the web app (one process); see docs/architecture.md and, for
the versions and the error format, docs/api.md.
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


V1_SUFFIX = "_v1"


def register_api(app):
    """Each blueprint twice: under /api/... and under /api/v1/....

    Both registrations share the views, hooks and services, so the two
    prefixes cannot drift apart (docs/api.md, versioning policy).
    """
    from api.errors import init_api_errors
    from shared.api_paths import v1_url_prefix

    # Set by LoginManager.init_app; the app factory runs it first.
    login_manager = app.login_manager

    for blueprint in api_blueprints():
        app.register_blueprint(blueprint)
        app.register_blueprint(
            blueprint,
            name=blueprint.name + V1_SUFFIX,
            url_prefix=v1_url_prefix(blueprint.url_prefix),
        )
        # A request without a session gets 401 JSON, not the sign-in page:
        # Flask-Login aborts with 401 for a blueprint without a login view.
        # Pages keep redirecting to the sign-in form.
        login_manager.blueprint_login_views[blueprint.name] = None
        login_manager.blueprint_login_views[blueprint.name + V1_SUFFIX] = None

    init_api_errors(app)
