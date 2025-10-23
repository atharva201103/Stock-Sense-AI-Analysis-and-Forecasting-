from django.core.management.base import BaseCommand
from django_apscheduler import util
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler.jobstores import DjangoJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

@util.close_old_connections
def scrape_news_job():
    try:
        logger.info("Running scheduled news scrape")
        call_command('scrape_news')
        logger.info("News scrape completed")
    except Exception as e:
        logger.error(f"Error in scheduled news scrape: {e}")

@util.close_old_connections
def scrape_stock_prices_job():
    try:
        logger.info("Running scheduled stock prices scrape")
        call_command('scrape_stock_prices')
        logger.info("Stock prices scrape completed")
    except Exception as e:
        logger.error(f"Error in scheduled stock prices scrape: {e}")

@util.close_old_connections
def analyze_portfolio_alerts_job():
    try:
        logger.info("Running scheduled portfolio alerts analysis")
        call_command('analyze_portfolio_alerts')
        logger.info("Portfolio alerts analysis completed")
    except Exception as e:
        logger.error(f"Error in scheduled portfolio alerts analysis: {e}")

class Command(BaseCommand):
    help = 'Schedule the news scraper to run periodically'

    def handle(self, *args, **options):
        scheduler = BackgroundScheduler(timezone='UTC')
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Add job to run news scrape every 15 minutes
        scheduler.add_job(
            scrape_news_job,
            trigger=CronTrigger(minute="*/15"),  # Every 15 minutes
            id="scrape_news_15min",
            max_instances=1,
            replace_existing=True,
        )

        # Add job to run stock prices scrape every 10 minutes
        scheduler.add_job(
            scrape_stock_prices_job,
            trigger=CronTrigger(minute="*/10"),  # Every 10 minutes
            id="scrape_stock_prices_10min",
            max_instances=1,
            replace_existing=True,
        )

        # Add job to run portfolio alerts analysis every 2 hours
        scheduler.add_job(
            analyze_portfolio_alerts_job,
            trigger=CronTrigger(hour="*/2"),  # Every 2 hours
            id="analyze_portfolio_alerts_2h",
            max_instances=1,
            replace_existing=True,
        )

        logger.info("Added scrape_news and scrape_stock_prices jobs to scheduler")

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
            self.stdout.write(self.style.SUCCESS('Scheduler started. Press Ctrl+C to exit.'))
            # Keep the command running
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS('Scheduler stopped.'))
