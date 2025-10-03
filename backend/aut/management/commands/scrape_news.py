from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from aut.mongodb_client import get_mongo_client

class Command(BaseCommand):
    help = 'Scrape stock news from Moneycontrol'

    def handle(self, *args, **options):
        url = 'https://www.moneycontrol.com/news/business/stocks/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'lxml')

        # Assuming the news items are in li or div with specific class
        # This is a placeholder; inspect the actual page for correct selectors
        news_items = soup.find_all('li', class_='clearfix')  # Example selector

        client = get_mongo_client()
        db = client['stock_db']
        news_collection = db['news']

        for item in news_items[:10]:  # Limit to 10 for example
            title_tag = item.find('h2') or item.find('a')
            if title_tag:
                title = title_tag.text.strip()
                link = title_tag['href'] if 'href' in title_tag.attrs else ''
                # Clean the title: remove extra spaces, etc.
                title = ' '.join(title.split())
                if title and link:
                    news_collection.insert_one({
                        'title': title,
                        'link': 'https://www.moneycontrol.com' + link if link.startswith('/') else link,
                        'scraped_at': datetime.now()
                    })

        self.stdout.write(self.style.SUCCESS('Successfully scraped news'))
