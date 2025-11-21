from django.core.management.base import BaseCommand
import requests
from datetime import datetime, timedelta
from aut.mongodb_client import get_db

class Command(BaseCommand):
    help = 'Fetch last 60 days of stock prices for multiple Indian stocks from Yahoo Finance'

    def handle(self, *args, **options):
        try:
            self.stdout.write('Starting 60-day stock history scrape from Yahoo Finance')

            stocks = {
                'RELIANCE': 'RELIANCE.NS',
                'TCS': 'TCS.NS',
                'INFY': 'INFY.NS',
                'HDFCBANK': 'HDFCBANK.NS',
                'ICICIBANK': 'ICICIBANK.NS',
                'HINDUNILVR': 'HINDUNILVR.NS',
                'ITC': 'ITC.NS',
                'KOTAKBANK': 'KOTAKBANK.NS',
                'LT': 'LT.NS',
                'BAJFINANCE': 'BAJFINANCE.NS',
                'BHARTIARTL': 'BHARTIARTL.NS',
                'MARUTI': 'MARUTI.NS',
                'AXISBANK': 'AXISBANK.NS',
                'BAJAJ-AUTO': 'BAJAJ-AUTO.NS',
                'HCLTECH': 'HCLTECH.NS',
                'WIPRO': 'WIPRO.NS',
                'NTPC': 'NTPC.NS',
                'POWERGRID': 'POWERGRID.NS',
                'ONGC': 'ONGC.NS',
                'COALINDIA': 'COALINDIA.NS',
                'GRASIM': 'GRASIM.NS',
                'ULTRACEMCO': 'ULTRACEMCO.NS',
                'NESTLEIND': 'NESTLEIND.NS',
                'BRITANNIA': 'BRITANNIA.NS',
                'HEROMOTOCO': 'HEROMOTOCO.NS',
                'DRREDDY': 'DRREDDY.NS',
                'CIPLA': 'CIPLA.NS',
                'SUNPHARMA': 'SUNPHARMA.NS',
                'TATAMOTORS': 'TATAMOTORS.NS',
                'M&M': 'M&M.NS'
                # add more if needed
            }

            db = get_db()
            stock_prices_collection = db['stock_prices']

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }

            scraped_count = 0
            days_back = 60  # 👈 change this to control how many days to fetch

            for stock_symbol, yahoo_symbol in stocks.items():
                try:
                    self.stdout.write(f'Fetching 60-day data for {stock_symbol}...')

                    # Calculate UNIX timestamps for the last 60 days
                    end_time = int(datetime.now().timestamp())
                    start_time = int((datetime.now() - timedelta(days=days_back)).timestamp())

                    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?period1={start_time}&period2={end_time}&interval=1d'

                    response = requests.get(url, headers=headers, timeout=10)

                    if response.status_code != 200:
                        self.stdout.write(self.style.WARNING(f"API failed for {stock_symbol}: {response.status_code}"))
                        continue

                    data = response.json().get('chart', {}).get('result', [{}])[0]
                    timestamps = data.get('timestamp', [])
                    indicators = data.get('indicators', {}).get('quote', [{}])[0]

                    closes = indicators.get('close', [])
                    volumes = indicators.get('volume', [])

                    # Store each day's record in DB
                    for i, ts in enumerate(timestamps):
                        price = closes[i] if i < len(closes) else None
                        volume = volumes[i] if i < len(volumes) else 0
                        if not price:
                            continue

                        stock_data = {
                            'symbol': stock_symbol,
                            'current_price': round(price, 2),
                            'volume': volume,
                            'timestamp': datetime.utcfromtimestamp(ts),
                            'source': 'Yahoo Finance (Historical)'
                        }

                        # 👇 Use upsert by (symbol + timestamp)
                        stock_prices_collection.insert_one(stock_data)

                    scraped_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Successfully fetched {len(timestamps)} days for {stock_symbol}'))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error fetching {stock_symbol}: {e}'))
                    continue

            self.stdout.write(self.style.SUCCESS(f'✅ Completed scraping {scraped_count} stocks with historical data'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during stock scrape: {e}'))
            import traceback
            traceback.print_exc()
