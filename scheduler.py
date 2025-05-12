from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from datetime import datetime
import asyncio
import logging
import main

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_task():
    logger.info(f"Scraping started at {datetime.now()}")
    
    # Burada main.py'deki veri çekme fonksiyonunu çağırıyoruz
    # Scraping işlemi uzun sürebileceğinden asyncio.run kullanıyoruz
    try:
        asyncio.run(main())
        logger.info(f"Scraping finished at {datetime.now()}")
    except Exception as e:
        logger.error(f"Error occurred while scraping: {e}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(scrape_task, 'interval', hours=1)  # Her 1 saatte bir scraping yapılacak
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.start()

def job_listener(event):
    if event.exception:
        logger.error(f"Job {event.job_id} failed")
    else:
        logger.info(f"Job {event.job_id} completed successfully")

if __name__ == '__main__':
    start_scheduler()
