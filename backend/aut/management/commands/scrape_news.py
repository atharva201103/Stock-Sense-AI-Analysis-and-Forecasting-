from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import uuid
import json
from aut.mongodb_client import get_db

def analyze_news(title, summary, stock):
    prompt = f"""
Analyze the following news article about the stock {stock} and provide the information in the exact JSON format below. Fill in the values based on the content. If a field is not applicable or cannot be determined, use appropriate defaults (e.g., empty list for lists, "Neutral" for Nature of News).

Output only the JSON object, nothing else.

{{
  "Nature of News": "Positive/Negative/Neutral",
  "Sector of Company": "string",
  "Impact Level": "High/Medium/Low",
  "Stock Mentioned": "{stock}",
  "Date of News": "YYYY-MM-DD",
  "Source": "Moneycontrol",
  "News Type": ["list of types like Mergers, Partnership, etc."],
  "Keywords": ["list of keywords"],
  "Volatility Indicator": "High/Medium/Low",
  "Relevance Score": 1-10,
  "Competitor Impact": "Yes/No",
  "Market Trend Alignment": "Positive/Negative/Neutral",
  "Regulatory Impact": "Yes/No",
  "Social Media Buzz": "Yes/No",
  "Financial Metrics Mentioned": ["list"],
  "Sentiment Score": -1.0 to 1.0
}}

Title: {title}
Summary: {summary}
"""

    try:
        ollama_response = requests.post('http://localhost:11434/api/chat', json={
            "model": "deepseek-r1:1.5b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }, timeout=30)

        if ollama_response.status_code == 200:
            data = ollama_response.json()
            content = data['message']['content'].strip()
            # Remove thinking tags if present
            if '<think>' in content and '</think>' in content:
                end_think = content.find('</think>')
                content = content[end_think + 8:].strip()
            # Remove markdown
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            analyzed = json.loads(content)
            return analyzed
        else:
            print(f"Ollama error: {ollama_response.status_code}")
            return None
    except Exception as e:
        print(f"Analysis failed: {e}")
        return None
            # Remove markdown

class Command(BaseCommand):
    help = 'Scrape stock news from Moneycontrol, analyze with AI, and store in raw_news and processed_news collections'

    def handle(self, *args, **options):
        try:
            self.stdout.write('Starting news scrape')
            url = 'https://www.moneycontrol.com/news/business/stocks/'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            self.stdout.write(f'Response status: {response.status_code}')
            soup = BeautifulSoup(response.content, 'lxml')

            # Find news items - look for links containing '/news/business/stocks/'
            news_items = soup.find_all('a', href=lambda href: href and '/news/business/stocks/' in href)
            self.stdout.write(f'Found {len(news_items)} potential news items')

            db = get_db()
            self.stdout.write('DB connected')
            raw_news_collection = db['raw_news']
            processed_news_collection = db['processed_news']

            # List of stocks to check for in titles
            stocks = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'HINDUNILVR', 'ITC', 'KOTAKBANK', 'LT', 'BAJFINANCE']

            count = 0
            processed_count = 0
            seen_links = set()
            for item in news_items[:20]:  # Get more to filter
                title = item.text.strip()
                link = item['href']
                if link.startswith('/'):
                    link = 'https://www.moneycontrol.com' + link

                title = ' '.join(title.split())
                if title and link and len(title) > 10 and link not in seen_links:  # Filter short titles and duplicates
                    seen_links.add(link)
                    # Fetch article content
                    try:
                        article_response = requests.get(link, headers=headers, timeout=10)
                        article_soup = BeautifulSoup(article_response.content, 'lxml')
                        content_div = article_soup.find('div', class_='arti-flow') or article_soup.find('div', class_='content_wrapper') or article_soup.find('div', id='contentdata')
                        if content_div:
                            content = content_div.get_text().strip()
                            # Clean content: remove extra spaces
                            content = ' '.join(content.split())
                            summary = content[:500] + '...' if len(content) > 500 else content
                        else:
                            content = title
                            summary = title
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Failed to fetch content for {title}: {e}'))
                        content = title
                        summary = title

                    # Generate unique id
                    news_id = str(uuid.uuid4())

                    # Current date as datetime object for proper MongoDB sorting
                    news_date = datetime.now()

                    # Check if news already exists
                    if raw_news_collection.find_one({'title': title}):
                        self.stdout.write(f'Skipping duplicate news: {title}')
                        continue

                    # Store in raw_news collection
                    raw_news_collection.insert_one({
                        'id': news_id,
                        'title': title,
                        'content': content,
                        'summary': summary,
                        'source': 'Moneycontrol',
                        'date': news_date,
                        'url': link,
                        'category': 'business',
                        'tags': ['business', 'finance', 'stocks']
                    })
                    count += 1

                    # Analyze the news
                    # Determine stock from title
                    stock = 'General'
                    for s in stocks:
                        if s.lower() in title.lower():
                            stock = s
                            break

                    # Check if already processed
                    if processed_news_collection.find_one({'title': title}):
                        self.stdout.write(f'Skipping duplicate processed news: {title}')
                        continue

                    analyzed = analyze_news(title, summary, stock)
                    if analyzed:
                        # Merge analyzed data with news info
                        processed_item = {
                            'stock': stock,
                            'title': title,
                            'summary': summary,
                            'link': link,
                            'date': news_date,
                            **analyzed
                        }
                        processed_news_collection.insert_one(processed_item)
                        processed_count += 1
                    else:
                        # Fallback with default attributes
                        self.stdout.write(self.style.WARNING(f'Analysis failed for {title}, using defaults'))
                        processed_item = {
                            'stock': stock,
                            'title': title,
                            'summary': summary,
                            'link': link,
                            'date': news_date,
                            'Nature of News': 'Neutral',
                            'Sector of Company': 'General',
                            'Impact Level': 'Medium',
                            'Stock Mentioned': stock,
                            'Date of News': news_date.strftime('%Y-%m-%d'),
                            'Source': 'Moneycontrol',
                            'News Type': [],
                            'Keywords': [],
                            'Volatility Indicator': 'Medium',
                            'Relevance Score': 5,
                            'Competitor Impact': 'No',
                            'Market Trend Alignment': 'Neutral',
                            'Regulatory Impact': 'No',
                            'Social Media Buzz': 'No',
                            'Financial Metrics Mentioned': [],
                            'Sentiment Score': 0.0
                        }
                        processed_news_collection.insert_one(processed_item)
                        processed_count += 1

                    if count >= 10:
                        break

            self.stdout.write(self.style.SUCCESS(f'Successfully scraped {count} news items and processed {processed_count} with AI analysis'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during scrape: {e}'))
            import traceback
            traceback.print_exc()
