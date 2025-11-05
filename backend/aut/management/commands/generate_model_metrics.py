from django.core.management.base import BaseCommand
import pandas as pd
from aut.mongodb_client import get_db
import os
import pickle
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score
from sklearn.model_selection import train_test_split, cross_val_score
from statsmodels.tsa.arima.model import ARIMA
from tensorflow.keras.models import load_model
from xgboost import XGBClassifier, XGBRegressor
from datetime import datetime

class Command(BaseCommand):
    help = 'Generate comprehensive metrics report for all ML models (XGBoost, LSTM, ARIMA, EMA)'

    def calculate_ema(self, prices, period=20):
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()

    def handle(self, *args, **options):
        db = get_db()
        processed_collection = db['processed_news']
        stock_prices_collection = db['stock_prices']

        metrics_report = {
            'timestamp': datetime.now(),
            'models': {}
        }

        # 1. XGBoost Classification (News Sentiment) - Using Cross-Validation
        self.stdout.write('Evaluating XGBoost Classification Model...')
        try:
            news_data = list(processed_collection.find())
            if news_data:
                df = pd.DataFrame(news_data)
                df['Sentiment Score'] = pd.to_numeric(df['Sentiment Score'], errors='coerce')
                df['Relevance Score'] = pd.to_numeric(df['Relevance Score'], errors='coerce')
                features = ['Sentiment Score', 'Relevance Score', 'Volatility Indicator', 'Impact Level']
                df['Volatility Indicator'] = df['Volatility Indicator'].map({'Low': 0, 'Medium': 1, 'High': 2})
                df['Impact Level'] = df['Impact Level'].map({'Low': 0, 'Medium': 1, 'High': 2})
                df = df.dropna(subset=features)

                X = df[features]
                y = df['Nature of News']

                # Load model and label encoder
                with open('models/xgb_model.pkl', 'rb') as f:
                    xgb_clf = pickle.load(f)
                with open('models/label_encoder.pkl', 'rb') as f:
                    le = pickle.load(f)

                y_encoded = le.fit_transform(y)

                # Use cross-validation for more reliable evaluation
                cv_scores = cross_val_score(xgb_clf, X, y_encoded, cv=3, scoring='accuracy')

                # Also evaluate on a holdout set if enough data
                if len(df) >= 20:
                    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)
                    xgb_clf_cv = XGBClassifier()
                    xgb_clf_cv.fit(X_train, y_train)
                    y_pred = xgb_clf_cv.predict(X_test)
                    test_accuracy = accuracy_score(y_test, y_pred)
                else:
                    test_accuracy = cv_scores.mean()

                metrics_report['models']['XGBoost_Classification'] = {
                    'cross_val_accuracy_mean': float(cv_scores.mean()),
                    'cross_val_accuracy_std': float(cv_scores.std()),
                    'test_accuracy': float(test_accuracy),
                    'dataset_size': len(df),
                    'cv_folds': 5
                }
                self.stdout.write(f'XGBoost Classification - CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})')
                self.stdout.write(f'XGBoost Classification - Test Accuracy: {test_accuracy:.4f}')
            else:
                self.stdout.write(self.style.WARNING('No news data for XGBoost evaluation'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'XGBoost Classification evaluation failed: {e}'))

        # 2. LSTM Time Series (Sentiment)
        self.stdout.write('Evaluating LSTM Model...')
        try:
            if news_data:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                sentiment_series = df['Sentiment Score'].values

                seq_length = 10
                X_lstm, y_lstm = [], []
                for i in range(len(sentiment_series) - seq_length):
                    X_lstm.append(sentiment_series[i:i+seq_length])
                    y_lstm.append(sentiment_series[i+seq_length])

                if len(X_lstm) > 0:
                    X_lstm = np.array(X_lstm).reshape(-1, seq_length, 1)
                    y_lstm = np.array(y_lstm)

                    lstm_model = load_model('models/lstm_model.h5')
                    y_pred = lstm_model.predict(X_lstm, verbose=0).flatten()

                    mse = mean_squared_error(y_lstm, y_pred)
                    mae = mean_absolute_error(y_lstm, y_pred)
                    rmse = np.sqrt(mse)

                    metrics_report['models']['LSTM'] = {
                        'mse': float(mse),
                        'mae': float(mae),
                        'rmse': float(rmse),
                        'dataset_size': len(X_lstm)
                    }
                    self.stdout.write(f'LSTM - RMSE: {rmse:.4f}, MAE: {mae:.4f}')
                else:
                    self.stdout.write(self.style.WARNING('Not enough data for LSTM evaluation'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'LSTM evaluation failed: {e}'))

        # 3. ARIMA Time Series (Sentiment)
        self.stdout.write('Evaluating ARIMA Model...')
        try:
            if 'sentiment_series' in locals() and len(sentiment_series) > 10:
                with open('models/arima_model.pkl', 'rb') as f:
                    arima_result = pickle.load(f)

                # Forecast on training data for evaluation
                predictions = arima_result.predict(start=10, end=len(sentiment_series)-1)
                actual = sentiment_series[10:]

                mse = mean_squared_error(actual, predictions)
                mae = mean_absolute_error(actual, predictions)
                rmse = np.sqrt(mse)

                metrics_report['models']['ARIMA'] = {
                    'mse': float(mse),
                    'mae': float(mae),
                    'rmse': float(rmse),
                    'dataset_size': len(actual)
                }
                self.stdout.write(f'ARIMA - RMSE: {rmse:.4f}, MAE: {mae:.4f}')
            else:
                self.stdout.write(self.style.WARNING('Not enough data for ARIMA evaluation'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'ARIMA evaluation failed: {e}'))

        # 4. EMA Forecasting (Stock Prices)
        self.stdout.write('Evaluating EMA Model...')
        try:
            stock_data = list(stock_prices_collection.find())
            if stock_data:
                df_stocks = pd.DataFrame(stock_data)
                df_stocks['timestamp'] = pd.to_datetime(df_stocks['timestamp'])
                df_stocks = df_stocks.sort_values(['symbol', 'timestamp'])

                ema_errors = []
                for symbol in df_stocks['symbol'].unique():
                    symbol_data = df_stocks[df_stocks['symbol'] == symbol]
                    if len(symbol_data) >= 30:
                        prices = symbol_data['current_price'].values
                        ema_values = self.calculate_ema(pd.Series(prices))

                        # Compare EMA with actual prices (next day prediction)
                        actual_next = prices[20:]  # After EMA warmup
                        ema_pred = ema_values[19:-1].values  # EMA predictions

                        if len(actual_next) == len(ema_pred):
                            mse = mean_squared_error(actual_next, ema_pred)
                            mae = mean_absolute_error(actual_next, ema_pred)
                            rmse = np.sqrt(mse)
                            ema_errors.append((mse, mae, rmse))

                if ema_errors:
                    avg_mse = np.mean([e[0] for e in ema_errors])
                    avg_mae = np.mean([e[1] for e in ema_errors])
                    avg_rmse = np.mean([e[2] for e in ema_errors])

                    metrics_report['models']['EMA'] = {
                        'mse': float(avg_mse),
                        'mae': float(avg_mae),
                        'rmse': float(avg_rmse),
                        'stocks_evaluated': len(ema_errors)
                    }
                    self.stdout.write(f'EMA - Avg RMSE: {avg_rmse:.4f}, Avg MAE: {avg_mae:.4f}')
                else:
                    self.stdout.write(self.style.WARNING('Not enough stock data for EMA evaluation'))
            else:
                self.stdout.write(self.style.WARNING('No stock data for EMA evaluation'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'EMA evaluation failed: {e}'))

        # 5. XGBoost Regression (Stock Forecasting)
        self.stdout.write('Evaluating XGBoost Regression Model...')
        try:
            if stock_data:
                xgb_errors = []
                for symbol in df_stocks['symbol'].unique():
                    symbol_data = df_stocks[df_stocks['symbol'] == symbol]
                    if len(symbol_data) >= 20:
                        prices = symbol_data['current_price'].values

                        features = []
                        targets = []
                        for i in range(10, len(prices)):
                            feature_row = prices[i-10:i].tolist()
                            features.append(feature_row)
                            targets.append(prices[i])

                        if len(features) > 5:
                            X = np.array(features)
                            y = np.array(targets)

                            # Simple train/test split
                            split_idx = int(0.8 * len(X))
                            X_train, X_test = X[:split_idx], X[split_idx:]
                            y_train, y_test = y[:split_idx], y[split_idx:]

                            xgb_reg = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=3)
                            xgb_reg.fit(X_train, y_train)

                            y_pred = xgb_reg.predict(X_test)
                            mse = mean_squared_error(y_test, y_pred)
                            mae = mean_absolute_error(y_test, y_pred)
                            rmse = np.sqrt(mse)
                            r2 = r2_score(y_test, y_pred)
                            xgb_errors.append((mse, mae, rmse, r2))

                if xgb_errors:
                    avg_mse = np.mean([e[0] for e in xgb_errors])
                    avg_mae = np.mean([e[1] for e in xgb_errors])
                    avg_rmse = np.mean([e[2] for e in xgb_errors])
                    avg_r2 = np.mean([e[3] for e in xgb_errors])

                    metrics_report['models']['XGBoost_Regression'] = {
                        'mse': float(avg_mse),
                        'mae': float(avg_mae),
                        'rmse': float(avg_rmse),
                        'r2_score': float(avg_r2),
                        'stocks_evaluated': len(xgb_errors)
                    }
                    self.stdout.write(f'XGBoost Regression - Avg RMSE: {avg_rmse:.4f}, Avg R²: {avg_r2:.4f}')
                else:
                    self.stdout.write(self.style.WARNING('Not enough stock data for XGBoost evaluation'))
            else:
                self.stdout.write(self.style.WARNING('No stock data for XGBoost evaluation'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'XGBoost Regression evaluation failed: {e}'))

        # Save report
        import json
        with open('models/metrics_report.json', 'w') as f:
            json.dump(metrics_report, f, indent=2, default=str)

        self.stdout.write(self.style.SUCCESS('Metrics report generated and saved to models/metrics_report.json'))

        # Print summary
        self.stdout.write('\n=== MODEL METRICS SUMMARY ===')
        for model_name, metrics in metrics_report['models'].items():
            self.stdout.write(f'\n{model_name}:')
            for metric, value in metrics.items():
                self.stdout.write(f'  {metric}: {value}')
