from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore, register_events

from app.utils.pipeline import run_hansard_pipeline


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        run_hansard_pipeline,
        trigger="interval",
        hours=25,
        id="hansard_pipeline_job",
        replace_existing=True,
        max_instances=1,
    )

    register_events(scheduler)
    scheduler.start()

    print("⏰ Hansard pipeline scheduler started (every 25 hours)")
