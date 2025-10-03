# MongoDB schemas are not strictly required for NoSQL, but we can define expected document structures for clarity and validation if needed.

# Example schema definitions for news and forecasts collections

news_schema = {
    "title": "string",
    "link": "string",
    "scraped_at": "datetime"
}

forecast_schema = {
    "ticker": "string",
    "arima": "float or null",
    "ema": "float or null",
    "xgboost": "float or null",
    "date": "datetime"
}

# These schemas can be used for validation or documentation purposes.
