from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from aut.mongodb_client import get_db

class Command(BaseCommand):
    help = 'Scrape real-time stock prices from Moneycontrol and store in database'

    def handle(self, *args, **options):
        try:
            self.stdout.write('Starting stock price scrape from Moneycontrol')

            # List of major Indian stocks to scrape - using Yahoo Finance API
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
            }

            db = get_db()
            stock_prices_collection = db['stock_prices']

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            scraped_count = 0

            for stock_symbol, yahoo_symbol in stocks.items():
                try:
                    # Use Yahoo Finance API for real-time data
                    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?period1={int((datetime.now().timestamp() - 86400))}&period2={int(datetime.now().timestamp())}&interval=1d'
                    print(f"Fetching data for {stock_symbol} from Yahoo Finance")

                    response = requests.get(url, headers=headers, timeout=10)

                    if response.status_code == 200:
                        data = response.json()
                        chart = data.get('chart', {}).get('result', [{}])[0]
                        meta = chart.get('meta', {})

                        if meta:
                            current_price = meta.get('regularMarketPrice', 0)
                            previous_close = meta.get('previousClose', 0)
                            change = current_price - previous_close if current_price and previous_close else 0
                            change_percent = (change / previous_close * 100) if previous_close else 0

                            # Get additional data
                            volume = meta.get('regularMarketVolume', 0)
                            market_cap = meta.get('marketCap', 0)
                            week_high = meta.get('fiftyTwoWeekHigh', 0)
                            week_low = meta.get('fiftyTwoWeekLow', 0)

                            print(f"Successfully fetched {stock_symbol}: ₹{current_price}")
                        else:
                            self.stdout.write(self.style.WARNING(f'No meta data for {stock_symbol}'))
                            continue
                    else:
                        self.stdout.write(self.style.WARNING(f'Yahoo Finance API failed for {stock_symbol}: {response.status_code}'))
                        continue

                    # Store in database
                    stock_data = {
                        'symbol': stock_symbol,
                        'current_price': current_price,
                        'change': change,
                        'change_percent': change_percent,
                        'volume': volume,
                        'market_cap': market_cap,
                        'week_high': week_high,
                        'week_low': week_low,
                        'timestamp': datetime.now(),
                        'source': 'Yahoo Finance'
                    }

                    # Update or insert
                    stock_prices_collection.update_one(
                        {'symbol': stock_symbol},
                        {'$set': stock_data},
                        upsert=True
                    )

                    scraped_count += 1
                    self.stdout.write(f'Scraped {stock_symbol}: ₹{current_price} ({change:+.2f})')

                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Failed to scrape {stock_symbol}: {e}'))
                    continue

            self.stdout.write(self.style.SUCCESS(f'Successfully scraped {scraped_count} stock prices from Yahoo Finance'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during stock price scrape: {e}'))
            import traceback
            traceback.print_exc()
