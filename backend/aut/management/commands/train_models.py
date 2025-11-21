from django.core.management.base import BaseCommand
import pandas as pd
from aut.mongodb_client import get_db
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.losses import MeanSquaredError
from statsmodels.tsa.arima.model import ARIMA
import numpy as np

class Command(BaseCommand):
    help = 'Train ML models on processed_news data for sentiment analysis and stock recommendations'

    def handle(self, *args, **options):
        db = get_db()
        processed_collection = db['processed_news']

        # Fetch all processed news
        news_data = list(processed_collection.find())
        if not news_data:
            self.stdout.write(self.style.WARNING('No processed news data found. Run scrape_news first.'))
            return

        df = pd.DataFrame(news_data)

        # Convert numeric columns to proper types
        df['Sentiment Score'] = pd.to_numeric(df['Sentiment Score'], errors='coerce')
        df['Relevance Score'] = pd.to_numeric(df['Relevance Score'], errors='coerce')

        # Prepare data for XGBoost classification (Nature of News)
        features = ['Sentiment Score', 'Relevance Score', 'Volatility Indicator', 'Impact Level']
        df['Volatility Indicator'] = df['Volatility Indicator'].map({'Low': 0, 'Medium': 1, 'High': 2})
        df['Impact Level'] = df['Impact Level'].map({'Low': 0, 'Medium': 1, 'High': 2})

        # Drop rows with NaN in features
        df = df.dropna(subset=features)

        X = df[features]
        y = df['Nature of News']

        le = LabelEncoder()
        y_encoded = le.fit_transform(y)
        y_encoded = y_encoded - y_encoded.min()

        X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

        # Train XGBoost
        xgb_model = XGBClassifier()
        xgb_model.fit(X_train, y_train)
        y_pred = xgb_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        self.stdout.write(f'XGBoost Accuracy: {accuracy}')

        # Save XGBoost model
        os.makedirs('models', exist_ok=True)
        with open('models/xgb_model.pkl', 'wb') as f:
            pickle.dump(xgb_model, f)
        with open('models/label_encoder.pkl', 'wb') as f:
            pickle.dump(le, f)

        # Prepare data for LSTM (sentiment time series)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        sentiment_series = df['Sentiment Score'].values

        # Create sequences
        seq_length = 10
        X_lstm, y_lstm = [], []
        for i in range(len(sentiment_series) - seq_length):
            X_lstm.append(sentiment_series[i:i+seq_length])
            y_lstm.append(sentiment_series[i+seq_length])

        X_lstm = np.array(X_lstm).reshape(-1, seq_length, 1)
        y_lstm = np.array(y_lstm)

        if len(X_lstm) > 0:
            # Train LSTM
            lstm_model = Sequential()
            lstm_model.add(LSTM(50, activation='relu', input_shape=(seq_length, 1)))
            lstm_model.add(Dense(1))
            lstm_model.compile(optimizer='adam', loss=MeanSquaredError())
            lstm_model.fit(X_lstm, y_lstm, epochs=10, verbose=0)
            lstm_model.save('models/lstm_model.h5')
            self.stdout.write('LSTM model trained and saved')
        else:
            self.stdout.write(self.style.WARNING('Not enough data for LSTM training'))

        # Train ARIMA for trend analysis
        try:
            arima_model = ARIMA(sentiment_series, order=(5,1,0))
            arima_result = arima_model.fit()
            with open('models/arima_model.pkl', 'wb') as f:
                pickle.dump(arima_result, f)
            self.stdout.write('ARIMA model trained and saved')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'ARIMA training failed: {e}'))

        self.stdout.write(self.style.SUCCESS('Model training completed'))
