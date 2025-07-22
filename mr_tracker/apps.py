from django.apps import AppConfig


class MrTrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mr_tracker'

    def ready(self):
        import mr_tracker.signals  # noqa
