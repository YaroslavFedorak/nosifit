from flask import g
from backend.app.utils.profile_options import (
    ACTIVITIES,
    EXPERIENCES,
    GENDERS,
    GOALS,
    WORKOUTS_PER_WEEK,
    normalize_activity,
    normalize_experience,
    normalize_goal,
)


from .locale import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    get_translation,
    resolve_locale,
)


def init_i18n(app):
    @app.before_request
    def set_locale():
        g.locale = resolve_locale()

    @app.context_processor
    def inject_i18n():
        locale = getattr(
            g,
            "locale",
            DEFAULT_LOCALE,
        )

        def translate(
            namespace: str,
            key: str,
            **params,
        ) -> str:
            value = get_translation(
                locale,
                namespace,
                key,
            )

            for name, replacement in params.items():
                value = value.replace(
                    f"{{{name}}}",
                    str(replacement),
                )

            return value

        def common_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "common",
                key,
                **params,
            )

        def auth_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "auth",
                key,
                **params,
            )

        def public_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "public",
                key,
                **params,
            )

        def app_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "app",
                key,
                **params,
            )

        def training_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "training",
                key,
                **params,
            )

        def nutrition_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "nutrition",
                key,
                **params,
            )

        def profile_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "profile",
                key,
                **params,
            )

        def dashboard_t(
            key: str,
            **params,
        ) -> str:
            return translate(
                "dashboard",
                key,
                **params,
            )

        return {
            "locale": locale,
            "supported_locales": SUPPORTED_LOCALES,
            "t": common_t,
            "translate": translate,
            "common_t": common_t,
            "auth_t": auth_t,
            "public_t": public_t,
            "app_t": app_t,
            "training_t": training_t,
            "nutrition_t": nutrition_t,
            "profile_t": profile_t,
            "dashboard_t": dashboard_t,
            "goal_options": GOALS,
            "activity_options": ACTIVITIES,
            "gender_options": GENDERS,
            "experience_options": EXPERIENCES,
            "workout_options": WORKOUTS_PER_WEEK,
            "normalize_goal": normalize_goal,
            "normalize_experience": normalize_experience,
            "normalize_activity": normalize_activity,
        }
