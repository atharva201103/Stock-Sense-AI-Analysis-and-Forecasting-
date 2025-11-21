from django.core.management.base import BaseCommand
import requests
import sys
sys.path.insert(0, '/Users/atharvavitthaljawalkar/Desktop/DataSets/backend/venv/lib/python3.11/site-packages')
from bs4 import BeautifulSoup
from datetime import datetime
import uuid
import json
import fcntl
import os
from aut.mongodb_client import get_db

def analyze_news(title, summary, stock, source):
    prompt = f"""
Analyze the following news article about the stock {stock} and provide the information in the exact JSON format below. Fill in the values based on the content. If a field is not applicable or cannot be determined, use appropriate defaults (e.g., empty list for lists, "Neutral" for Nature of News).

Output only the JSON object, nothing else.

{{
  "Nature of News": "string (Positive, Negative, or Neutral)",
  "Sector of Company": "string",
  "Impact Level": "High/Medium/Low",
  "Stock Mentioned": "{stock}",
  "Date of News": "YYYY-MM-DD",
  "Source": "{source}",
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

class Command(BaseCommand):
    help = 'Scrape stock news from Moneycontrol, analyze with AI, and store in raw_news and processed_news collections'

    def extract_news_items(self, soup, source):
        """Extract news items from the soup based on source configuration."""
        news_items = []
        # Find all 'a' tags with href
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href')
            if href and source['link_pattern'] in href:
                news_items.append(a_tag)
        return news_items

    def handle(self, *args, **options):
        # Use file locking to prevent concurrent execution
        lock_file = '/tmp/scrape_news.lock'
        try:
            lock_fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stdout.write(self.style.WARNING('Another instance of scrape_news is already running. Exiting.'))
            return

        try:
            # Get MongoDB database and collections
            db = get_db()
            raw_news_collection = db['raw_news']
            processed_news_collection = db['processed_news']

            # List of stocks to check for in titles
            stocks = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'HINDUNILVR', 'ITC', 'KOTAKBANK', 'LT', 'BAJFINANCE']

            self.stdout.write('Starting news scrape from multiple sources')

            # Scrape from both Moneycontrol and Screener.in
            sources = [
                {
                    'name': 'Moneycontrol',
                    'url': 'https://www.moneycontrol.com/news/business/stocks/',
                    'link_pattern': '/news/business/stocks/',
                    'selectors': [
                        ('div', {'class': 'arti-flow'}),
                        ('div', {'class': 'content_wrapper arti-flow'}),
                        ('div', {'id': 'contentdata'}),
                        ('div', {'class': 'article_content'}),
                        ('div', {'class': 'story-content'}),
                        ('article', {}),
                        ('div', {'class': 'content'}),
                    ]
                },
                {
                    'name': 'Moneycontrol',
                    'url': 'https://www.moneycontrol.com/news/business/stocks/',
                    'link_pattern': '/news/business/stocks/',
                    'selectors': [
                        ('div', {'class': 'arti-flow'}),
                        ('div', {'class': 'content_wrapper arti-flow'}),
                        ('div', {'id': 'contentdata'}),
                        ('div', {'class': 'article_content'}),
                        ('div', {'class': 'story-content'}),
                        ('article', {}),
                        ('div', {'class': 'content'}),
                    ]
                }
            ]

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            all_news_items = []
            for source in sources:
                try:
                    self.stdout.write(f'Scraping from {source["name"]}')
                    response = requests.get(source['url'], headers=headers, timeout=15)
                    if response.status_code != 200:
                        self.stdout.write(self.style.WARNING(f'Failed to fetch from {source["name"]}: {response.status_code}'))
                        continue

                    soup = BeautifulSoup(response.content, 'lxml')
                    news_items = self.extract_news_items(soup, source)
                    all_news_items.extend([(item, source) for item in news_items])
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error scraping {source["name"]}: {e}'))
                    continue

            # Remove duplicates while preserving order
            seen_links = set()
            unique_news_items = []
            for item, source in all_news_items:
                href = item.get('href')
                if href and href not in seen_links:
                    seen_links.add(href)
                    unique_news_items.append((item, source))

            news_items_with_sources = unique_news_items
            self.stdout.write(f'Found {len(news_items_with_sources)} unique news items after deduplication')

            count = 0
            processed_count = 0
            seen_links = set()
            for item, source in news_items_with_sources[:50]:  # Process up to 50 items
                # Extract clean title - try to get text from the link, excluding child elements that might contain UI text
                title = item.get_text(strip=True)
                if not title:
                    continue

                # Remove unwanted UI text patterns that appear in Moneycontrol links
                ui_patterns = [
                    'TradeWatchlistPortfolioMessageSet Alert',
                    'Choose Stock Exchange: BSE LIVE NSE LIVE',
                    'Volume Todays L/H More ×',
                    '26 Aug, 2025 12:21',
                    'buy',
                    'sell',
                    'hold',
                    'TradeWatchlist',
                    'PortfolioMessageSet',
                    'Alert Choose',
                    'Stock Exchange:',
                    'BSE LIVE',
                    'NSE LIVE',
                    'Volume Todays',
                    'L/H More ×'
                ]

                for pattern in ui_patterns:
                    title = title.replace(pattern, '').strip()

                # Clean up extra spaces and normalize
                title = ' '.join(title.split())

                link = item['href']
                if link.startswith('/'):
                    link = source['url'].rstrip('/') + link

                # Skip if title contains unwanted content like CSS classes or JavaScript
                if any(skip in title.lower() for skip in ['.mc-modal', 'function', 'var ', 'display:', 'rgba', 'css', 'style', 'script']):
                    continue

                # Skip if link contains unwanted patterns
                if any(skip in link for skip in ['#', 'javascript:', 'mailto:']):
                    continue

                # Additional check: title should not be too long or contain too many numbers/dates
                if len(title) > 200 or title.count('2025') > 1 or title.count('Aug') > 1:
                    continue

                if title and link and len(title) > 15 and link not in seen_links:  # Filter short titles and duplicates
                    seen_links.add(link)
                    # Fetch article content
                    try:
                        article_response = requests.get(link, headers=headers, timeout=10)
                        article_soup = BeautifulSoup(article_response.content, 'lxml')

                        # Try multiple selectors for article content
                        content_div = None

                        for tag, attrs in source['selectors']:
                            if attrs:
                                content_div = article_soup.find(tag, attrs)
                            else:
                                content_div = article_soup.find(tag)
                            if content_div:
                                break

                        if content_div:
                            content = content_div.get_text().strip()
                            # Clean content: remove extra spaces and unwanted elements
                            content = ' '.join(content.split())

                            # Remove CSS and JavaScript content patterns more aggressively
                            css_js_patterns = [
                                r'\.mc-modal-wrap\s*\{[^}]*\}',
                                r'\.mc-modal\s*\{[^}]*\}',
                                r'/\*.*?\*/',
                                r'function\s*\([^)]*\)\s*\{[^}]*\}',
                                r'var\s+[a-zA-Z_][a-zA-Z0-9_]*\s*=',
                                r'display:\s*[^;]+;',
                                r'rgba?\([^)]+\)',
                                r'z-index:\s*[^;]+;',
                                r'position:\s*[^;]+;',
                                r'background:\s*[^;]+;',
                                r'width:\s*[^;]+;',
                                r'height:\s*[^;]+;',
                                r'font-size:\s*[^;]+;',
                                r'color:\s*[^;]+;',
                                r'margin:\s*[^;]+;',
                                r'padding:\s*[^;]+;',
                                r'border:\s*[^;]+;',
                                r'float:\s*[^;]+;',
                                r'clear:\s*[^;]+;',
                                r'text-align:\s*[^;]+;',
                                r'vertical-align:\s*[^;]+;',
                                r'overflow:\s*[^;]+;',
                                r'cursor:\s*[^;]+;',
                                r'box-shadow:\s*[^;]+;',
                                r'transition:\s*[^;]+;',
                                r'animation:\s*[^;]+;',
                                r'transform:\s*[^;]+;',
                                r'opacity:\s*[^;]+;',
                                r'visibility:\s*[^;]+;',
                                r'clip:\s*[^;]+;',
                                r'filter:\s*[^;]+;',
                                r'content:\s*[^;]+;',
                                r'counter-increment:\s*[^;]+;',
                                r'counter-reset:\s*[^;]+;',
                                r'outline:\s*[^;]+;',
                                r'list-style:\s*[^;]+;',
                                r'table-layout:\s*[^;]+;',
                                r'caption-side:\s*[^;]+;',
                                r'empty-cells:\s*[^;]+;',
                                r'border-collapse:\s*[^;]+;',
                                r'border-spacing:\s*[^;]+;',
                                r'speak:\s*[^;]+;',
                                r'speak-header:\s*[^;]+;',
                                r'speak-numeral:\s*[^;]+;',
                                r'speak-punctuation:\s*[^;]+;',
                                r'volume:\s*[^;]+;',
                                r'speech-rate:\s*[^;]+;',
                                r'pause:\s*[^;]+;',
                                r'cue:\s*[^;]+;',
                                r'play-during:\s*[^;]+;',
                                r'azimuth:\s*[^;]+;',
                                r'elevation:\s*[^;]+;',
                                r'voice-family:\s*[^;]+;',
                                r'pitch:\s*[^;]+;',
                                r'pitch-range:\s*[^;]+;',
                                r'stress:\s*[^;]+;',
                                r'richness:\s*[^;]+;',
                                r'phonemes:\s*[^;]+;',
                                r'@media\s*[^}]*\}',
                                r'@keyframes\s*[^}]*\}',
                                r'\{[^}]*\}',  # Remove any remaining CSS blocks
                            ]

                            import re
                            for pattern in css_js_patterns:
                                content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)

                            # Clean again after removal
                            content = ' '.join(content.split())

                            # Additional validation - check if content looks like actual news
                            # Should contain sentences, not just CSS properties
                            sentences = [s.strip() for s in content.split('.') if s.strip() and len(s.strip()) > 10]
                            if len(sentences) >= 2 and len(content) > 100:
                                summary = content[:500] + '...' if len(content) > 500 else content
                            else:
                                # Try to get content from paragraphs instead
                                paragraphs = content_div.find_all('p')
                                if paragraphs:
                                    para_text = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                                    if len(para_text) > 50:
                                        content = para_text
                                        summary = content[:500] + '...' if len(content) > 500 else content
                                    else:
                                        content = title
                                        summary = title
                                else:
                                    content = title
                                    summary = title
                        else:
                            # Try to get content from meta description or other sources
                            meta_desc = article_soup.find('meta', {'name': 'description'})
                            if meta_desc and meta_desc.get('content'):
                                content = meta_desc['content'].strip()
                                summary = content
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

                    # Check if news already exists (check both title and url to avoid duplicates)
                    if raw_news_collection.find_one({'$or': [{'title': title}, {'url': link}]}):
                        self.stdout.write(f'Skipping duplicate news: {title}')
                        continue

                    # Store in raw_news collection
                    raw_news_collection.insert_one({
                        '_id': news_id,  # Use _id for consistency with processed_news
                        'title': title,
                        'content': content,
                        'summary': summary,
                        'source': source['name'],
                        'date': news_date,
                        'url': link,
                        'category': 'business',
                        'tags': ['business', 'finance', 'stocks']
                    })
                    count += 1

                    # Analyze the news using AI
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

                    analyzed = analyze_news(title, summary, stock, source['name'])
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
                            'Source': source['name'],
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
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during scrape: {e}'))
            import traceback
            traceback.print_exc()
        finally:
            # Clean up lock file
            try:
                os.close(lock_fd)
                os.unlink(lock_file)
            except:
                pass
