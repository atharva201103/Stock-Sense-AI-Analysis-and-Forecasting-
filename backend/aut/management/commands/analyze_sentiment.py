from django.core.management.base import BaseCommand
import pickle
import numpy as np
import re
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from aut.mongodb_client import get_db

class Command(BaseCommand):
    help = 'Analyze sentiment of news articles using trained neural network model'

    def handle(self, *args, **options):
        # Load the trained model and tokenizer
        try:
            model = load_model('models/sentiment_model.h5')
            with open('models/sentiment_tokenizer.pkl', 'rb') as f:
                tokenizer = pickle.load(f)
            with open('models/sentiment_label_encoder.pkl', 'rb') as f:
                label_encoder = pickle.load(f)
        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f'Model files not found: {e}'))
            return

        # Get database connection
        db = get_db()
        processed_collection = db['processed_news']

        # Get all news articles
        news_articles = list(processed_collection.find())

        if not news_articles:
            self.stdout.write(self.style.WARNING('No news articles found to analyze'))
            return

        self.stdout.write(f'Analyzing sentiment for {len(news_articles)} news articles...')

        updated_count = 0
        for article in news_articles:
            # Combine title and content for better analysis
            text_to_analyze = f"{article.get('title', '')} {article.get('content', '')}".strip()

            if not text_to_analyze:
                continue

            # Preprocess text (same as training)
            processed_text = self.preprocess_text(text_to_analyze)

            # Tokenize and pad
            sequence = tokenizer.texts_to_sequences([processed_text])
            padded_sequence = pad_sequences(sequence, maxlen=100)

            # Predict sentiment
            prediction = model.predict(padded_sequence, verbose=0)
            predicted_class = np.argmax(prediction, axis=1)[0]
            confidence = np.max(prediction, axis=1)[0]

            # Convert to sentiment label
            sentiment_label = label_encoder.inverse_transform([predicted_class])[0]

            # Convert to numerical score (-1 to 1 scale)
            if sentiment_label == 'positive':
                sentiment_score = confidence * 1.0  # 0.0 to 1.0
            elif sentiment_label == 'negative':
                sentiment_score = -confidence * 1.0  # -1.0 to 0.0
            else:  # neutral
                sentiment_score = 0.0  # exactly 0

            # Update the article in database
            processed_collection.update_one(
                {'_id': article['_id']},
                {'$set': {
                    'Sentiment Score': float(sentiment_score),
                    'sentiment_label': sentiment_label,
                    'sentiment_confidence': float(confidence)
                }}
            )

            updated_count += 1

            if updated_count % 10 == 0:
                self.stdout.write(f'Processed {updated_count}/{len(news_articles)} articles...')

        self.stdout.write(self.style.SUCCESS(f'Successfully analyzed sentiment for {updated_count} news articles'))

        # Show sample results
        sample_articles = list(processed_collection.find().limit(5))
        self.stdout.write('\nSample results:')
        for article in sample_articles:
            self.stdout.write(f"Title: {article.get('title', '')[:50]}...")
            self.stdout.write(f"Sentiment: {article.get('Sentiment Score', 'N/A')} ({article.get('sentiment_label', 'N/A')})")
            self.stdout.write('---')

    def preprocess_text(self, text):
        """Preprocess text same as training data"""
        import nltk
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        from nltk.stem import WordNetLemmatizer

        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))

        # Convert to lowercase
        text = text.lower()
        # Remove special characters and numbers
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        # Tokenize
        tokens = word_tokenize(text)
        # Remove stopwords and lemmatize
        tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
        return ' '.join(tokens)
