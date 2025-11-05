from django.core.management.base import BaseCommand
import sys
sys.path.insert(0, '/Users/atharvavitthaljawalkar/Desktop/DataSets/backend/venv/lib/python3.11/site-packages')
import pandas as pd
import numpy as np
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Embedding, LSTM, Bidirectional
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.utils import to_categorical
import pickle
import os

class Command(BaseCommand):
    help = 'Train a neural network model for sentiment analysis of financial news'

    def handle(self, *args, **options):
        # Download required NLTK data
        try:
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('wordnet')
        except:
            self.stdout.write(self.style.WARNING('NLTK data download failed, proceeding...'))

        # Create sample training data for financial news sentiment
        sample_data = self.create_sample_training_data()

        # Preprocess the data
        processed_data = self.preprocess_data(sample_data)

        # Train the model
        self.train_sentiment_model(processed_data)

        self.stdout.write(self.style.SUCCESS('Sentiment analysis model training completed'))

    def create_sample_training_data(self):
        """Create sample training data for financial news sentiment"""
        data = [
            # Positive sentiment examples
            {"text": "Company reports strong quarterly earnings beating expectations", "sentiment": "positive"},
            {"text": "Stock surges after positive analyst recommendations", "sentiment": "positive"},
            {"text": "Company announces major contract win worth millions", "sentiment": "positive"},
            {"text": "Profitable quarter with record revenue growth", "sentiment": "positive"},
            {"text": "Buy recommendation from top investment firms", "sentiment": "positive"},
            {"text": "Company exceeds market expectations with strong performance", "sentiment": "positive"},
            {"text": "Positive outlook for the company's future growth", "sentiment": "positive"},
            {"text": "Stock price rallies on positive earnings guidance", "sentiment": "positive"},
            {"text": "Company announces dividend increase and share buyback", "sentiment": "positive"},
            {"text": "Strong balance sheet and cash flow position", "sentiment": "positive"},

            # Negative sentiment examples
            {"text": "Company reports disappointing quarterly results", "sentiment": "negative"},
            {"text": "Stock plunges after profit warning", "sentiment": "negative"},
            {"text": "Company faces regulatory investigation", "sentiment": "negative"},
            {"text": "Loss-making quarter with declining revenue", "sentiment": "negative"},
            {"text": "Sell recommendation from major analysts", "sentiment": "negative"},
            {"text": "Company misses earnings expectations significantly", "sentiment": "negative"},
            {"text": "Negative outlook for the industry sector", "sentiment": "negative"},
            {"text": "Stock drops on disappointing guidance", "sentiment": "negative"},
            {"text": "Company announces layoffs and cost cutting", "sentiment": "negative"},
            {"text": "Weak balance sheet with high debt levels", "sentiment": "negative"},

            # Neutral sentiment examples
            {"text": "Company announces regular dividend payment", "sentiment": "neutral"},
            {"text": "Stock trades within normal range", "sentiment": "neutral"},
            {"text": "Company provides business update", "sentiment": "neutral"},
            {"text": "Regular quarterly reporting period", "sentiment": "neutral"},
            {"text": "Company maintains current guidance", "sentiment": "neutral"},
            {"text": "Stock shows normal market volatility", "sentiment": "neutral"},
            {"text": "Company announces board changes", "sentiment": "neutral"},
            {"text": "Standard business operations continue", "sentiment": "neutral"},
            {"text": "Company reports expected results", "sentiment": "neutral"},
            {"text": "Market conditions remain stable", "sentiment": "neutral"},
        ]

        return pd.DataFrame(data)

    def preprocess_data(self, df):
        """Preprocess the text data for training"""
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))

        def preprocess_text(text):
            # Convert to lowercase
            text = text.lower()
            # Remove special characters and numbers
            text = re.sub(r'[^a-zA-Z\s]', '', text)
            # Tokenize
            tokens = word_tokenize(text)
            # Remove stopwords and lemmatize
            tokens = [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
            return ' '.join(tokens)

        df['processed_text'] = df['text'].apply(preprocess_text)

        # Encode labels
        le = LabelEncoder()
        df['sentiment_encoded'] = le.fit_transform(df['sentiment'])

        # Save label encoder
        os.makedirs('models', exist_ok=True)
        with open('models/sentiment_label_encoder.pkl', 'wb') as f:
            pickle.dump(le, f)

        return df

    def train_sentiment_model(self, df):
        """Train the neural network model"""
        # Prepare data for training
        X = df['processed_text'].values
        y = df['sentiment_encoded'].values

        # Tokenize text
        tokenizer = Tokenizer(num_words=5000)
        tokenizer.fit_on_texts(X)
        X_sequences = tokenizer.texts_to_sequences(X)
        X_padded = pad_sequences(X_sequences, maxlen=100)

        # Convert labels to categorical
        y_categorical = to_categorical(y)

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_padded, y_categorical, test_size=0.2, random_state=42
        )

        # Build model
        model = Sequential()
        model.add(Embedding(5000, 128, input_length=100))
        model.add(Bidirectional(LSTM(64, return_sequences=True)))
        model.add(Dropout(0.3))
        model.add(Bidirectional(LSTM(32)))
        model.add(Dropout(0.3))
        model.add(Dense(64, activation='relu'))
        model.add(Dropout(0.3))
        model.add(Dense(3, activation='softmax'))  # 3 classes: positive, negative, neutral

        model.compile(
            loss='categorical_crossentropy',
            optimizer='adam',
            metrics=['accuracy']
        )

        # Train model
        history = model.fit(
            X_train, y_train,
            epochs=1000,
            batch_size=16,
            validation_split=0.2,
            verbose=1
        )

        # Evaluate model
        loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
        self.stdout.write(f'Model Accuracy: {accuracy:.4f}')

        # Save model and tokenizer
        model.save('models/sentiment_model.h5')
        with open('models/sentiment_tokenizer.pkl', 'wb') as f:
            pickle.dump(tokenizer, f)

        # Print classification report
        y_pred = model.predict(X_test)
        y_pred_classes = np.argmax(y_pred, axis=1)
        y_test_classes = np.argmax(y_test, axis=1)

        report = classification_report(y_test_classes, y_pred_classes,
                                    target_names=['negative', 'neutral', 'positive'])
        self.stdout.write(f'Classification Report:\n{report}')
