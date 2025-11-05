from django.core.management.base import BaseCommand
import pandas as pd
from aut.mongodb_client import get_db
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
import numpy as np
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Forecast stock prices using EMA, ARIMA, and XGBoost models'

    def calculate_ema(self, prices, period=20):
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()

    def handle(self, *args, **options):
        db = get_db()
        stock_prices_collection = db['stock_prices']
        forecasts_collection = db['forecasts']

        # Fetch all stock prices
        stock_data = list(stock_prices_collection.find())
        if not stock_data:
            self.stdout.write(self.style.WARNING('No stock price data found. Run scrape_stock_prices first.'))
            return

        df = pd.DataFrame(stock_data)

        # Group by symbol and sort by timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['symbol', 'timestamp'])

        forecast_results = []

        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].copy()

            if len(symbol_data) < 30:  # Need minimum data for forecasting
                self.stdout.write(self.style.WARNING(f'Not enough data for {symbol}'))
                continue

            prices = symbol_data['current_price'].values
            dates = symbol_data['timestamp'].values

            # Calculate EMA
            ema_values = self.calculate_ema(pd.Series(prices))
            ema_forecast = ema_values.iloc[-1] if len(ema_values) > 0 else None

            # Prepare data for ARIMA
            try:
                arima_model = ARIMA(prices, order=(5,1,0))
                arima_result = arima_model.fit()
                arima_forecast = arima_result.forecast(steps=1)[0]
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'ARIMA failed for {symbol}: {e}'))
                arima_forecast = None

            # Prepare data for XGBoost regression
            # Create features from price history
            features = []
            targets = []

            for i in range(10, len(prices)):
                feature_row = prices[i-10:i].tolist()
                features.append(feature_row)
                targets.append(prices[i])

            if len(features) > 0:
                X = np.array(features)
                y = np.array(targets)

                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

                # Train XGBoost regressor
                xgb_model = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=3)
                xgb_model.fit(X_train, y_train)

                # Predict next price
                last_sequence = prices[-10:].reshape(1, -1)
                xgb_forecast = xgb_model.predict(last_sequence)[0]

                # Calculate RMSE for evaluation
                y_pred = xgb_model.predict(X_test)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                self.stdout.write(f'XGBoost RMSE for {symbol}: {rmse:.2f}')
            else:
                xgb_forecast = None

            # Store forecast
            forecast_doc = {
                'ticker': symbol,
                'arima': float(arima_forecast) if arima_forecast is not None else None,
                'ema': float(ema_forecast) if ema_forecast is not None else None,
                'xgboost': float(xgb_forecast) if xgb_forecast is not None else None,
                'date': datetime.now()
            }

            forecasts_collection.update_one(
                {'ticker': symbol},
                {'$set': forecast_doc},
                upsert=True
            )

            forecast_results.append(forecast_doc)
            self.stdout.write(f'Forecasted {symbol}: ARIMA={arima_forecast:.2f}, EMA={ema_forecast:.2f}, XGBoost={xgb_forecast:.2f}')

        self.stdout.write(self.style.SUCCESS(f'Successfully forecasted {len(forecast_results)} stocks'))
