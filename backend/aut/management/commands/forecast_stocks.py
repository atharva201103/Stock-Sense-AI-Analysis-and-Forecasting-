from django.core.management.base import BaseCommand
import yfinance as yf
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from xgboost import XGBRegressor
from aut.mongodb_client import get_mongo_client
from datetime import datetime

class Command(BaseCommand):
    help = 'Forecast stock prices using ARIMA, EMA, XGBoost'

    def handle(self, *args, **options):
        ticker = '^NSEI'  # NIFTY 50
        data = yf.download(ticker, period='1y')
        if data.empty:
            self.stdout.write(self.style.ERROR('No data downloaded'))
            return

        close = data['Close']

        # ARIMA
        try:
            model_arima = ARIMA(close, order=(5,1,0))
            model_arima_fit = model_arima.fit()
            forecast_arima = model_arima_fit.forecast(steps=1).iloc[0]
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'ARIMA failed: {e}'))
            forecast_arima = None

        # EMA
        ema = close.ewm(span=20).mean().iloc[-1]

        # XGBoost
        try:
            close_df = pd.DataFrame(close)
            close_df['lag1'] = close_df['Close'].shift(1)
            close_df = close_df.dropna()
            X = close_df[['lag1']]
            y = close_df['Close']
            model_xgb = XGBRegressor()
            model_xgb.fit(X, y)
            last_close = close.iloc[-1]
            forecast_xgb = model_xgb.predict([[last_close]])[0]
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'XGBoost failed: {e}'))
            forecast_xgb = None

        # Store in DB
        client = get_mongo_client()
        db = client['stock_db']
        forecast_collection = db['forecasts']

        forecast_collection.insert_one({
            'ticker': ticker,
            'arima': float(forecast_arima) if forecast_arima else None,
            'ema': float(ema),
            'xgboost': float(forecast_xgb) if forecast_xgb else None,
            'date': datetime.now()
        })

        self.stdout.write(self.style.SUCCESS('Forecasts generated and stored'))
