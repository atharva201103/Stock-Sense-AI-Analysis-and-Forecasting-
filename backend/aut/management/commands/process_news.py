from django.core.management.base import BaseCommand
from aut.mongodb_client import get_db
from aut.sentiment_utils import analyze_sentiment

class Command(BaseCommand):
    help = 'Process raw news and store in processed_news collection'

    def handle(self, *args, **options):
        db = get_db()
        raw_news_collection = db['raw_news']
        processed_news_collection = db['processed_news']

        # Get all raw news
        raw_news = list(raw_news_collection.find())

        for news in raw_news:
            # Analyze sentiment
            text_to_analyze = f"{news.get('title', '')} {news.get('content', '')}".strip()
            try:
                sentiment_score, sentiment_label, sentiment_confidence = analyze_sentiment(text_to_analyze)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to analyze sentiment for news {news["_id"]}: {e}'))
                sentiment_score, sentiment_label, sentiment_confidence = 0.0, 'neutral', 0.0

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
                # Add processing attributes (these will be enhanced by AI analysis in scrape_news)
                'nature_of_news': 'Neutral',  # Default, will be updated by AI
                'sector_of_company': 'General',  # Default, will be updated by AI
                'impact_level': 'Medium',  # Default, will be updated by AI
                'stock_mentioned': 'General',  # Default, will be updated by AI
                'news_type': [],  # Default, will be updated by AI
                'keywords': [],  # Default, will be updated by AI
                'volatility_indicator': 'Medium',  # Default, will be updated by AI
                'relevance_score': 5,  # Default, will be updated by AI
                'competitor_impact': 'No',  # Default, will be updated by AI
                'market_trend_alignment': 'Neutral',  # Default, will be updated by AI
                'regulatory_impact': 'No',  # Default, will be updated by AI
                'social_media_buzz': 'No',  # Default, will be updated by AI
                'financial_metrics_mentioned': [],  # Default, will be updated by AI
                'Sentiment Score': sentiment_score,
                'sentiment_label': sentiment_label,
                'sentiment_confidence': sentiment_confidence,
            }

            # Upsert to processed_news
            processed_news_collection.replace_one(
                {'_id': news['_id']},
                processed_news,
                upsert=True
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully processed {len(raw_news)} news items'))
