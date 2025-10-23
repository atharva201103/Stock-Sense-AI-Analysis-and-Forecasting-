from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from aut.mongodb_client import get_db
import pickle
import numpy as np
from datetime import datetime, timedelta
import requests

class Command(BaseCommand):
    help = 'Analyze user portfolios and send alerts for negative sentiment or concerning fundamentals'

    def handle(self, *args, **options):
        # Load trained models
        try:
            with open('models/xgb_model.pkl', 'rb') as f:
                xgb_model = pickle.load(f)
            with open('models/label_encoder.pkl', 'rb') as f:
                le = pickle.load(f)
            self.stdout.write('Models loaded successfully')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading models: {e}'))
            return

        db = get_db()
        portfolio_collection = db.portfolio
        transactions_collection = db.transactions
        processed_collection = db['processed_news']
        alerts_collection = db['user_alerts']

        # Get all users
        users = User.objects.all()

        for user in users:
            self.stdout.write(f'Analyzing portfolio for user: {user.username}')

            # Get user portfolio
            user_id = user.id
            portfolio = portfolio_collection.find_one({"userId": user_id})
            holdings = []

            if portfolio:
                holdings = portfolio.get('holdings', [])
            else:
                # Calculate from transactions
                transactions = list(transactions_collection.find({"userId": user_id}).sort("date", 1))
                holdings_dict = {}

                for tx in transactions:
                    symbol = tx.get("symbol")
                    if not symbol:
                        continue

                    if tx.get("type") == "buy":
                        if symbol not in holdings_dict:
                            holdings_dict[symbol] = {"symbol": symbol, "shares": 0, "totalCost": 0}
                        holdings_dict[symbol]["shares"] += tx.get("shares", 0)
                        holdings_dict[symbol]["totalCost"] += tx.get("amount", 0)
                    elif tx.get("type") == "sell":
                        if symbol in holdings_dict:
                            holdings_dict[symbol]["shares"] -= tx.get("shares", 0)
                            holdings_dict[symbol]["totalCost"] -= tx.get("amount", 0)
                            if holdings_dict[symbol]["shares"] <= 0:
                                del holdings_dict[symbol]

                holdings = list(holdings_dict.values())

            if not holdings:
                self.stdout.write(f'No holdings found for user {user.username}')
                continue

            # Analyze each holding
            alerts = []
            for holding in holdings:
                stock = holding['symbol']
                self.stdout.write(f'Analyzing {stock} for user {user.username}')

                # Get recent news for this stock (last 7 days)
                seven_days_ago = datetime.now() - timedelta(days=7)
                news = list(processed_collection.find({
                    'stock': stock,
                    'date': {'$gte': seven_days_ago}
                }).sort('date', -1).limit(10))

                if not news:
                    self.stdout.write(f'No recent news for {stock}')
                    continue

                # Calculate sentiment metrics
                sentiments = [n.get('Sentiment Score', 0) for n in news]
                avg_sentiment = np.mean(sentiments)
                min_sentiment = np.min(sentiments)
                negative_count = sum(1 for s in sentiments if s < -0.3)

                # Get latest news attributes
                latest_news = news[0]
                volatility = latest_news.get('Volatility Indicator', 'Medium')
                impact = latest_news.get('Impact Level', 'Medium')
                relevance = latest_news.get('Relevance Score', 5)
                nature = latest_news.get('Nature of News', 'Neutral')

                # Model prediction
                vol_map = {'Low': 0, 'Medium': 1, 'High': 2}
                imp_map = {'Low': 0, 'Medium': 1, 'High': 2}
                features = [avg_sentiment, relevance, vol_map.get(volatility, 1), imp_map.get(impact, 1)]
                pred = xgb_model.predict([features])
                predicted_nature = le.inverse_transform(pred)[0]

                # Alert conditions for negative alerts
                negative_alert_reasons = []

                # Condition 1: Very negative sentiment (below -0.5)
                if avg_sentiment < -0.5:
                    negative_alert_reasons.append(f"Very negative sentiment (avg: {avg_sentiment:.2f})")

                # Condition 2: Multiple negative news items
                if negative_count >= 3:
                    negative_alert_reasons.append(f"Multiple negative news items ({negative_count} out of {len(news)})")

                # Condition 3: Model predicts negative nature
                if predicted_nature == 'Negative':
                    negative_alert_reasons.append(f"AI model predicts negative outlook")

                # Condition 4: High volatility + negative sentiment
                if volatility == 'High' and avg_sentiment < -0.2:
                    negative_alert_reasons.append("High volatility with negative sentiment")

                # Condition 5: High impact news
                if impact == 'High' and nature in ['Negative', 'Neutral']:
                    negative_alert_reasons.append("High impact concerning news")

                # Condition 6: Sudden sentiment drop
                if len(sentiments) >= 3:
                    recent_avg = np.mean(sentiments[:3])
                    older_avg = np.mean(sentiments[3:])
                    if recent_avg < older_avg - 0.3:
                        negative_alert_reasons.append("Sudden negative sentiment shift")

                # Alert conditions for positive alerts
                positive_alert_reasons = []

                # Condition 1: Very positive sentiment (above 0.5)
                if avg_sentiment > 0.5:
                    positive_alert_reasons.append(f"Very positive sentiment (avg: {avg_sentiment:.2f})")

                # Condition 2: Model predicts positive nature
                if predicted_nature == 'Positive':
                    positive_alert_reasons.append(f"AI model predicts positive outlook")

                # Condition 3: High impact positive news
                if impact == 'High' and nature == 'Positive':
                    positive_alert_reasons.append("High impact positive news")

                # Condition 4: Sudden sentiment increase
                if len(sentiments) >= 3:
                    recent_avg = np.mean(sentiments[:3])
                    older_avg = np.mean(sentiments[3:])
                    if recent_avg > older_avg + 0.3:
                        positive_alert_reasons.append("Sudden positive sentiment shift")

                # Create negative alert if any negative conditions met
                if negative_alert_reasons:
                    alert_message = f"Alert for {stock}: " + "; ".join(negative_alert_reasons)
                    alert_data = {
                        'user_id': user_id,
                        'stock': stock,
                        'alert_type': 'negative_sentiment',
                        'message': alert_message,
                        'sentiment_score': float(avg_sentiment),
                        'predicted_nature': predicted_nature,
                        'news_count': len(news),
                        'negative_news_count': negative_count,
                        'volatility': volatility,
                        'impact_level': impact,
                        'created_at': datetime.now(),
                        'is_read': False
                    }
                    # Check if similar alert already exists (avoid spam)
                    existing_alert = alerts_collection.find_one({
                        'user_id': user_id,
                        'stock': stock,
                        'alert_type': 'negative_sentiment',
                        'created_at': {'$gte': datetime.now() - timedelta(hours=24)}
                    })

                    if not existing_alert:
                        alerts_collection.insert_one(alert_data)
                        alerts.append(alert_data)
                        self.stdout.write(self.style.WARNING(f'Negative alert created for {user.username}: {stock}'))

                # Create positive alert if any positive conditions met
                if positive_alert_reasons:
                    alert_message = f"Good news for {stock}: " + "; ".join(positive_alert_reasons)
                    alert_data = {
                        'user_id': user_id,
                        'stock': stock,
                        'alert_type': 'positive_sentiment',
                        'message': alert_message,
                        'sentiment_score': float(avg_sentiment),
                        'predicted_nature': predicted_nature,
                        'news_count': len(news),
                        'negative_news_count': negative_count,
                        'volatility': volatility,
                        'impact_level': impact,
                        'created_at': datetime.now(),
                        'is_read': False
                    }
                    # Check if similar alert already exists (avoid spam)
                    existing_alert = alerts_collection.find_one({
                        'user_id': user_id,
                        'stock': stock,
                        'alert_type': 'positive_sentiment',
                        'created_at': {'$gte': datetime.now() - timedelta(hours=24)}
                    })

                    if not existing_alert:
                        alerts_collection.insert_one(alert_data)
                        alerts.append(alert_data)
                        self.stdout.write(self.style.SUCCESS(f'Positive alert created for {user.username}: {stock}'))

                    # Check if similar alert already exists (avoid spam)
                    existing_alert = alerts_collection.find_one({
                        'user_id': user_id,
                        'stock': stock,
                        'alert_type': 'negative_sentiment',
                        'created_at': {'$gte': datetime.now() - timedelta(hours=24)}
                    })

                    if not existing_alert:
                        alerts_collection.insert_one(alert_data)
                        alerts.append(alert_data)
                        self.stdout.write(self.style.WARNING(f'Alert created for {user.username}: {stock}'))

            if alerts:
                self.stdout.write(self.style.SUCCESS(f'Created {len(alerts)} alerts for user {user.username}'))
            else:
                self.stdout.write(f'No alerts needed for user {user.username}')

        self.stdout.write(self.style.SUCCESS('Portfolio analysis completed'))
