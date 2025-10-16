# MongoDB schemas are not strictly required for NoSQL, but we can define expected document structures for clarity and validation if needed.

# Schema for processed_news collection in trada_db
processed_news_schema = {
    "id": "string",  # Unique identifier
    "title": "string",  # News title
    "content": "string",  # Full article content
    "summary": "string",  # Short summary of the article
    "source": "string",  # News source (e.g., 'Moneycontrol')
    "date": "string",  # ISO date string
    "url": "string",  # Link to the full article
    "category": "string",  # Category like 'stocks', 'economy'
    "tags": "array of strings"  # Tags like ['stocks', 'business']
}

forecast_schema = {
    "ticker": "string",
    "arima": "float or null",
    "ema": "float or null",
    "xgboost": "float or null",
    "date": "datetime"
}

# Schema for stock_prices collection in trada_db
stock_prices_schema = {
    "symbol": "string",  # Stock symbol (e.g., 'RELIANCE', 'TCS')
    "current_price": "float",  # Current market price
    "change": "float",  # Price change from previous close
    "change_percent": "float",  # Percentage change
    "volume": "integer",  # Trading volume
    "market_cap": "string",  # Market capitalization (formatted string)
    "week_high": "float",  # 52-week high price
    "week_low": "float",  # 52-week low price
    "timestamp": "datetime",  # When the data was last updated
    "source": "string"  # Data source (e.g., 'Yahoo Finance')
}

# Schema for raw_news collection in trada_db
raw_news_schema = {
    "id": "string",  # Unique identifier
    "title": "string",  # News title
    "content": "string",  # Full article content
    "summary": "string",  # Short summary of the article
    "source": "string",  # News source (e.g., 'Moneycontrol')
    "date": "datetime",  # Publication date
    "url": "string",  # Link to the full article
    "category": "string",  # Category like 'business'
    "tags": "array of strings"  # Tags like ['business', 'finance', 'stocks']
}

# These schemas can be used for validation or documentation purposes.
