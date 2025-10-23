# TODO: Integrate Real-Time News Scraper with Dashboard

## Tasks
- [x] Move scraper command to main backend: Copy scrape_news.py from temp_repo to backend/aut/management/commands/
- [x] Update scraper to fetch detailed news data and store in processed_news collection in trada_db
- [x] Update MongoDB schemas for processed_news collection
- [x] Update frontend API to fetch from processed_news collection in trada_db
- [x] Test the scraper and API integration
- [x] Fix database locking issues by implementing file locking and reducing scheduler frequency
- [x] Configure scheduler to run news scraping every 15 minutes and stock prices every 10 minutes
