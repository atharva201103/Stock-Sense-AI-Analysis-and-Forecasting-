from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

def scrape_news_job():
    from django.core.management import call_command
    try:
        logger.info("Running scheduled news scrape")
        call_command('scrape_news')
        logger.info("News scrape completed")
    except Exception as e:
        logger.error(f"Error in scheduled news scrape: {e}")

class AutConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aut'

    def ready(self):
        # Import APScheduler modules here to avoid AppRegistryNotReady
        try:
            from django_apscheduler.jobstores import DjangoJobStore
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
            from django_apscheduler import util

            # Start the scheduler when the app is ready
            if not hasattr(self, 'scheduler_started'):
                self.scheduler_started = True
                scheduler = BackgroundScheduler(timezone='UTC')
                scheduler.add_jobstore(DjangoJobStore(), "default")

                # Add job to run every 10 minutes
                scheduler.add_job(
                    scrape_news_job,
                    trigger=CronTrigger(minute="*/10"),  # Every 10 minutes
                    id="scrape_news_10min",
                    max_instances=1,
                    replace_existing=True,
                )

                logger.info("Starting scheduler in app ready...")
                scheduler.start()
                logger.info("Scheduler started successfully.")
        except ImportError:
            logger.warning("django_apscheduler not available, skipping scheduler setup")
