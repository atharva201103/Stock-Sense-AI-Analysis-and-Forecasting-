from django.core.management.base import BaseCommand
from aut.mongodb_client import get_db

class Command(BaseCommand):
    help = 'Process raw news and store in processed_news collection'

    def handle(self, *args, **options):
        db = get_db()
        raw_news_collection = db['raw_news']
        processed_news_collection = db['processed_news']

        # Get all raw news
        raw_news = list(raw_news_collection.find())

        for news in raw_news:
            # Process the news - add attributes
            processed_news = {
                '_id': news['_id'],  # Keep same id
                'title': news['title'],
                'content': news['content'],
                'summary': news['summary'],
                'source': news['source'],
                'date': news['date'],
                'url': news['url'],
                'category': news['category'],
                'tags': news['tags'],
                # Add processing attributes
                'nature_of_news': 'Positive',  # Example
                'sector_of_company': 'Business Software',  # Example
                'impact_level': 'High',  # Example
                'stock_mentioned': 'TCS',  # Example
                'news_type': ['Financial', 'Market'],  # Example
                'keywords': ['technology', 'earnings', 'growth'],  # Example
                'volatility_indicator': 'Low',  # Example
                'relevance_score': 7,  # Example
                'competitor_impact': 'Yes',  # Example
                'market_trend_alignment': 'Positive',  # Example
                'regulatory_impact': '',  # Example
                'social_media_buzz': '',  # Example
                'financial_metrics_mentioned': [],  # Example
                'sentiment_score': 2.5,  # Example
            }

            # Upsert to processed_news
            processed_news_collection.replace_one(
                {'_id': news['_id']},
                processed_news,
                upsert=True
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully processed {len(raw_news)} news items'))
