from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
import os
import uuid
import json
import requests
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .serializers import WatchlistSerializer, PortfolioSerializer, UserProfileSerializer
from .models import UserProfile, Portfolio, Watchlist
import pickle
import tensorflow as tf
from .mongodb_client import get_db
import numpy as np
import re



def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class RegisterView(APIView) :
    permission_classes = [AllowAny]
    def post(self, request)  :
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create(username=username, password=make_password(password), email=email)
        user.save()
        # Create UserProfile
        UserProfile.objects.create(user=user)
        token = get_tokens_for_user(user = user)
        return Response(token, status=status.HTTP_201_CREATED)
    
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        print("Username:", username)
        print("Password:", password)

        user = authenticate(username=username, password=password)

        if user:
            token = get_tokens_for_user(user=user)
            return Response(token, status=status.HTTP_200_OK)
        else:
            # Always return a response for invalid credentials
            return Response(
                {"error": "Invalid username or password"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        



from rest_framework_simplejwt.tokens import AccessToken

class UserFromTokenView(APIView):
    permission_classes = [AllowAny]  # you can change this if needed

    def post(self, request):
        token = request.data.get('token')

        if not token:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
            
            return Response({
                'username': user.username,
                'email': user.email,
                'id': user.id,
                
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Invalid or expired token'}, status=status.HTTP_401_UNAUTHORIZED)



class ModelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            prompt = request.data.get('prompt', '')
            user = request.user  # ✅ Now works with JWT

            print("---------------------------------------------")
            print("User:", user)
            print("Prompt:", prompt[:200] + "..." if len(prompt) > 200 else prompt)
            print("---------------------------------------------")

            # Load trained models
            xgb_model = None
            le = None
            lstm_model = None
            arima_model = None
            try:
                with open('models/xgb_model.pkl', 'rb') as f:
                    xgb_model = pickle.load(f)
                with open('models/label_encoder.pkl', 'rb') as f:
                    le = pickle.load(f)
                lstm_model = tf.keras.models.load_model('models/lstm_model.h5')
                with open('models/arima_model.pkl', 'rb') as f:
                    arima_model = pickle.load(f)
                print("Models loaded successfully")
            except Exception as e:
                print("Error loading models:", e)

            # Parse portfolio stocks from prompt and add model insights
            portfolio_section = re.search(r'Portfolio Holdings:\n(.*?)\n\nRecent Transactions:', prompt, re.DOTALL)
            if portfolio_section:
                holdings_text = portfolio_section.group(1)
                holdings = re.findall(r'- (\w+):', holdings_text)
                print("Portfolio stocks:", holdings)
                model_insights = "\n\nModel-based Insights:\n"
                db = get_db()
                processed_collection = db['processed_news']
                for stock in holdings:
                    # Get recent news for this stock
                    news = list(processed_collection.find({'stock': stock}).sort('date', -1).limit(5))
                    if news:
                        avg_sentiment = np.mean([n.get('Sentiment Score', 0) for n in news])
                        avg_relevance = np.mean([n.get('Relevance Score', 5) for n in news])
                        volatility = news[0].get('Volatility Indicator', 'Medium')
                        impact = news[0].get('Impact Level', 'Medium')
                        vol_map = {'Low': 0, 'Medium': 1, 'High': 2}
                        imp_map = {'Low': 0, 'Medium': 1, 'High': 2}
                        features = [avg_sentiment, avg_relevance, vol_map.get(volatility, 1), imp_map.get(impact, 1)]
                        if xgb_model and le:
                            pred = xgb_model.predict([features])
                            nature = le.inverse_transform(pred)[0]
                            recommendation = 'Buy' if nature == 'Positive' else 'Sell' if nature == 'Negative' else 'Hold'
                            model_insights += f"- {stock}: Sentiment {avg_sentiment:.2f}, Nature: {nature}, Recommendation: {recommendation}\n"
                        else:
                            model_insights += f"- {stock}: Average Sentiment {avg_sentiment:.2f}, No model prediction available\n"
                    else:
                        model_insights += f"- {stock}: No recent news data\n"
                prompt += model_insights

            # Enhanced question understanding with real-time data capabilities
            prompt_lower = prompt.lower()

            # Check for real-time price queries
            price_keywords = ['current price', 'price of', 'stock price', 'share price', 'live price', 'what is price']
            is_price_query = any(keyword in prompt_lower for keyword in price_keywords)

            if is_price_query:
                # Extract stock symbol from query
                stock_symbol = None
                common_stocks = {
                    'reliance': 'RELIANCE',
                    'tcs': 'TCS',
                    'infosys': 'INFY',
                    'infy': 'INFY',
                    'hdfc bank': 'HDFCBANK',
                    'hdfc': 'HDFCBANK',
                    'icici bank': 'ICICIBANK',
                    'icici': 'ICICIBANK',
                    'hindustan unilever': 'HINDUNILVR',
                    'hul': 'HINDUNILVR',
                    'itc': 'ITC',
                    'kotak mahindra bank': 'KOTAKBANK',
                    'kotak': 'KOTAKBANK',
                    'larsen & toubro': 'LT',
                    'lt': 'LT',
                    'bajaj finance': 'BAJFINANCE',
                    'bajaj': 'BAJFINANCE'
                }

                for key, symbol in common_stocks.items():
                    if key in prompt_lower:
                        stock_symbol = symbol
                        break

                if stock_symbol:
                    # Fetch real-time price from database
                    db = get_db()
                    stock_prices_collection = db['stock_prices']
                    price_data = stock_prices_collection.find_one({'symbol': stock_symbol})

                    if price_data:
                        current_price = price_data.get('current_price', 0)
                        change = price_data.get('change', 0)
                        change_percent = price_data.get('change_percent', 0)
                        volume = price_data.get('volume', 0)
                        market_cap = price_data.get('market_cap', '')
                        week_high = price_data.get('week_high', 0)
                        week_low = price_data.get('week_low', 0)
                        timestamp = price_data.get('timestamp')

                        price_info = f"""
Current Price of {stock_symbol}: ₹{current_price:.2f}
Change: {change:+.2f} ({change_percent:+.2f}%)
Volume: {volume:,}
Market Cap: {market_cap}
52W High: ₹{week_high:.2f}
52W Low: ₹{week_low:.2f}
Last Updated: {timestamp.strftime('%H:%M %d/%m/%Y') if timestamp else 'N/A'}
Source: Moneycontrol
"""
                        prompt += f"\n\nReal-time stock data:\n{price_info}"

            # Dynamic question understanding using AI classification
            question_classifier_prompt = f"""
Analyze this user question and classify it into one of these categories:
1. GENERAL_INVESTMENT - Questions about general stock recommendations, future investments, market picks (e.g., "which stock should I look for my future investment", "best stocks to invest in")
2. PORTFOLIO_SPECIFIC - Questions about user's own portfolio, holdings, transactions, balance (e.g., "my portfolio", "my holdings", "analyze my stocks")
3. MARKET_ANALYSIS - Questions about market trends, sector analysis, economic outlook (e.g., "market analysis", "sector trends", "economic forecast")
4. FINANCIAL_EDUCATION - Questions about investment basics, strategies, terminology (e.g., "what is diversification", "how to invest", "stock market basics")
5. PRICE_QUERY - Questions asking for current stock prices or real-time data (e.g., "current price of reliance", "what is stock price")

User question: "{prompt}"

Respond with ONLY the category name (GENERAL_INVESTMENT, PORTFOLIO_SPECIFIC, MARKET_ANALYSIS, FINANCIAL_EDUCATION, or PRICE_QUERY).
"""

            # Use AI to classify the question
            classifier_payload = {
                "model": "deepseek-r1:1.5b",
                "prompt": question_classifier_prompt,
                "stream": False
            }

            try:
                classifier_response = requests.post("http://localhost:11434/api/generate", json=classifier_payload)
                if classifier_response.status_code == 200:
                    classifier_output = classifier_response.json()
                    question_type = classifier_output['response'].strip().upper()
                    # Remove any <think> blocks
                    question_type = re.sub(r'<think>.*?</think>', '', question_type, flags=re.DOTALL).strip()
                    print(f"Question classified as: {question_type}")
                else:
                    question_type = "GENERAL_INVESTMENT"  # fallback
                    print("Classification failed, using fallback")
            except Exception as e:
                question_type = "GENERAL_INVESTMENT"  # fallback
                print(f"Classification error: {e}, using fallback")

            # Determine the appropriate prompt based on AI-classified question type
            if question_type == "GENERAL_INVESTMENT":
                full_prompt = """You are StockSence, an expert AI financial advisor specializing in Indian stock markets.

When users ask general investment questions like "which stock should I look for my future investment", provide:
1. Specific stock recommendations from major Indian indices (NIFTY 50, SENSEX)
2. Focus on blue-chip companies with strong fundamentals
3. Consider current market conditions and sector performance
4. Provide diversification across sectors (IT, Banking, Pharma, Energy, etc.)
5. Include both growth and dividend-yield focused stocks
6. Always mention this is general advice and recommend consulting a financial advisor

Structure your response:
- Start with current market context
- List 5-7 specific stock recommendations with brief reasoning
- Include risk considerations
- End with disclaimer

""" + prompt
            elif question_type == "PORTFOLIO_SPECIFIC":
                full_prompt = "You are an AI financial advisor. Analyze the user's portfolio, recent transactions, and news sentiment data to provide personalized stock recommendations. Explain your reasoning based on the model insights provided.\n\n" + prompt
            elif question_type == "MARKET_ANALYSIS":
                full_prompt = """You are StockSence, a market analysis expert specializing in Indian financial markets.

Provide comprehensive market analysis covering:
1. Current market trends and indices performance
2. Sector-wise analysis and outlook
3. Key economic indicators affecting markets
4. Investment themes and opportunities
5. Risk factors and market sentiment

Use data-driven insights and maintain objectivity.

""" + prompt
            else:  # FINANCIAL_EDUCATION or fallback
                full_prompt = """You are StockSence, an AI financial advisor specializing in Indian stock markets.

Provide helpful, accurate responses about:
- Stock market basics and concepts
- Investment strategies and principles
- Risk management
- Financial planning advice
- Market terminology explanations

Keep responses informative, balanced, and always include appropriate disclaimers for financial advice.

""" + prompt

            payload = {
                "model": "deepseek-r1:1.5b",
                "prompt": full_prompt,
                "stream": False
            }

            print("Sending payload to Ollama:", payload)

            # Send request to Ollama
            ollama_response = requests.post("http://localhost:11434/api/generate", json=payload)
            print("Ollama response status:", ollama_response.status_code)
            if ollama_response.status_code != 200:
                print("Ollama error text:", ollama_response.text)
                return JsonResponse({"error": f"Ollama API error: {ollama_response.status_code} - {ollama_response.text}"}, status=500)
            output = ollama_response.json()
            print("Ollama output keys:", list(output.keys()))
            response = output['response']
            print("Raw AI response:", response)
            print("AI response length:", len(response))

            # Remove <think> blocks from DeepSeek R1 responses
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
            print("Response after removing <think>:", response)
            divided_text = response.split('```')
            explanation = ""
            code = ""
            if len(divided_text) > 1 :
                for i in range(0,len(divided_text)):
                    if i % 2 == 1 :
                        image_name = f"{uuid.uuid4().hex}.png"
                        image_path = os.path.join("media", image_name)
                        code = divided_text[i]
                        code = code.replace('python', '')
                        code = code.replace("plt.show()", f"plt.savefig('{image_path}')\nplt.close()")

                    else :
                        explanation = explanation + divided_text[i]
                with open("chart.py" , 'w') as f :
                    f.write(code)
                with open("exp.txt" , 'w') as f:
                    f.write(explanation)

                os.system("python3 chart.py")
                text = ''
                with open('exp.txt' , 'r') as f :
                    text =f.read()

                return JsonResponse({
                    "type": "image",
                    "image_url": f"/media/{image_name}",
                    "message": text
                })
            else :
                return JsonResponse({
                    "type": "text",
                    "message": response
                })

    

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

        return JsonResponse({"error": "Invalid request method"}, status=400)


class PortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from .mongodb_client import get_db
            db = get_db()
            portfolio_collection = db.portfolio
            transactions_collection = db.transactions

            user_id = request.user.id
            print(f"Fetching portfolio for user: {user_id}")

            # Try to get existing portfolio
            portfolio = portfolio_collection.find_one({"userId": user_id})
            if portfolio:
                print(f"Portfolio from DB: {portfolio}")
                return Response({"success": True, "portfolio": {"holdings": portfolio['holdings']}}, status=200)

            # If no portfolio, calculate from transactions
            transactions = list(transactions_collection.find({"userId": user_id}).sort("date", 1))
            holdings = {}

            for tx in transactions:
                symbol = tx.get("symbol")
                if not symbol:
                    continue
                if tx.get("type") == "buy":
                    if symbol not in holdings:
                        holdings[symbol] = {"symbol": symbol, "shares": 0, "totalCost": 0}
                    holdings[symbol]["shares"] += tx.get("shares", 0)
                    holdings[symbol]["totalCost"] += tx.get("amount", 0)
                elif tx.get("type") == "sell":
                    if symbol in holdings:
                        holdings[symbol]["shares"] -= tx.get("shares", 0)
                        holdings[symbol]["totalCost"] -= tx.get("amount", 0)
                        if holdings[symbol]["shares"] <= 0:
                            del holdings[symbol]

            holdings_list = []
            for h in holdings.values():
                if h["shares"] > 0:
                    holdings_list.append({
                        "symbol": h["symbol"],
                        "name": h["symbol"] + " Stock",
                        "shares": h["shares"],
                        "avgPrice": h["totalCost"] / h["shares"] if h["shares"] > 0 else 0,
                        "totalCost": h["totalCost"]
                    })

            print(f"Calculated holdings: {holdings_list}")
            return Response({"success": True, "portfolio": {"holdings": holdings_list}}, status=200)
        except Exception as e:
            print("Error fetching portfolio:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)

    def post(self, request):
        try:
            asset_name = request.data.get("asset_name")
            quantity = request.data.get("quantity")
            value = request.data.get("value")

            if not asset_name or quantity is None or value is None:
                return Response(
                    {"success": False, "error": "Missing required fields"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            Portfolio.objects.create(
                user=request.user,
                asset_name=asset_name,
                quantity=float(quantity),
                value=float(value)
            )

            return Response(
                {
                    "success": True,
                    "message": "Asset added successfully",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            print("Error adding to portfolio:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)

class WatchlistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            watchlists = Watchlist.objects.filter(user=request.user)
            serializer = WatchlistSerializer(watchlists, many=True)
            stocks = [{"symbol": item['stock_symbol'], "name": item['stock_symbol']} for item in serializer.data]
            return Response({"success": True, "watchlist": stocks})
        except Exception as e:
            print("Error fetching watchlist:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)

    def post(self, request):
        try:
            stock_symbol = request.data.get("stock_symbol")
            stock_name = request.data.get("stock_name", stock_symbol)

            if not stock_symbol:
                return Response(
                    {"success": False, "error": "Stock symbol is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if Watchlist.objects.filter(user=request.user, stock_symbol=stock_symbol).exists():
                return Response(
                    {"success": False, "error": "Stock already in watchlist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            Watchlist.objects.create(
                user=request.user,
                stock_symbol=stock_symbol
            )

            return Response({"success": True, "message": "Added to watchlist"})
        except Exception as e:
            print("Error adding to watchlist:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)

class BalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            serializer = UserProfileSerializer(profile)
            return Response({"success": True, "balance": serializer.data['balance']})
        except Exception as e:
            print("Error fetching balance:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)

    def put(self, request):
        try:
            balance = request.data.get("balance")
            if balance is None:
                return Response({"success": False, "error": "Balance is required"}, status=400)

            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.balance = balance
            profile.save()
            return Response({"success": True, "balance": balance})
        except Exception as e:
            print("Error updating balance:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)

class AlertsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Load models
            xgb_model = None
            le = None
            try:
                with open('models/xgb_model.pkl', 'rb') as f:
                    xgb_model = pickle.load(f)
                with open('models/label_encoder.pkl', 'rb') as f:
                    le = pickle.load(f)
            except Exception as e:
                print("Error loading models for alerts:", e)
                return Response({"success": False, "error": "Models not available"}, status=500)

            # Get user portfolio
            db = get_db()
            portfolio_collection = db.portfolio
            transactions_collection = db.transactions
            user_id = request.user.id
            portfolio = portfolio_collection.find_one({"userId": user_id})
            holdings = []
            if portfolio:
                holdings = portfolio.get('holdings', [])
            else:
                # Calculate from transactions
                transactions = list(transactions_collection.find({"userId": user_id}).sort("date", 1))
                holdings_dict = {}
                for tx in transactions:
                    symbol = tx.get("symbol")
                    if tx.get("type") == "buy":
                        if symbol not in holdings_dict:
                            holdings_dict[symbol] = {"symbol": symbol, "shares": 0, "totalCost": 0}
                        holdings_dict[symbol]["shares"] += tx.get("shares", 0)
                        holdings_dict[symbol]["totalCost"] += tx.get("amount", 0)
                    elif tx.get("type") == "sell":
                        if symbol in holdings_dict:
                            holdings_dict[symbol]["shares"] -= tx.get("shares", 0)
                            holdings_dict[symbol]["totalCost"] -= tx.get("amount", 0)
                            if holdings_dict[symbol]["shares"] <= 0:
                                del holdings_dict[symbol]
                holdings = list(holdings_dict.values())

            # Get alerts for negative sentiment
            alerts = []
            processed_collection = db['processed_news']
            for holding in holdings:
                stock = holding['symbol']
                news = list(processed_collection.find({'stock': stock}).sort('date', -1).limit(5))
                if news:
                    avg_sentiment = np.mean([n.get('Sentiment Score', 0) for n in news])
                    avg_relevance = np.mean([n.get('Relevance Score', 5) for n in news])
                    volatility = news[0].get('Volatility Indicator', 'Medium')
                    impact = news[0].get('Impact Level', 'Medium')
                    vol_map = {'Low': 0, 'Medium': 1, 'High': 2}
                    imp_map = {'Low': 0, 'Medium': 1, 'High': 2}
                    features = [avg_sentiment, avg_relevance, vol_map.get(volatility, 1), imp_map.get(impact, 1)]
                    pred = xgb_model.predict([features])
                    nature = le.inverse_transform(pred)[0]
                    if nature != 'Positive':
                        alerts.append({
                            'stock': stock,
                            'nature': nature,
                            'sentiment': avg_sentiment,
                            'message': f"Negative sentiment for {stock}: {nature}"
                        })

            return Response({"success": True, "alerts": alerts})
        except Exception as e:
            print("Error fetching alerts:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)
