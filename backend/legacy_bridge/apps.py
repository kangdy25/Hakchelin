from django.apps import AppConfig


class LegacyBridgeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "legacy_bridge"

    def ready(self) -> None:
        from . import schema  # noqa: F401
