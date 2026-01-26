from django.apps import AppConfig
import os  

class AppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'

    def ready(self):
        if os.environ.get("RUN_MAIN") != "true":
            return

        from app.scheduler.job import start
        start()
