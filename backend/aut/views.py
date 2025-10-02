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
from .serializers import WatchlistSerializer



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
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            prompt = request.data.get('prompt', '')
            user = request.user  # ✅ Now works with JWT

            print("---------------------------------------------")
            print(user)   
            print("---------------------------------------------")
            payload = {
                "model": "llama3.2:3b",
                "prompt": prompt,
                "system": f"you are a stock market assistant named alex and u analyze user portfolio and answer users doubt related to stock market ",
                "stream": False
            }

            # Send request to Ollama
            response = requests.post("http://localhost:11434/api/generate", json=payload)
            result = response.json()
            # Check if model generated chart code
            if response.status_code == 200 :
                output = response.json()
                response = output['response']
                divided_text = response.split('```')
                explanation = ""
                code = ""
                if len(divided_text) >=1 :
                    for i in range(0,len(divided_text)):
                        if i == 1 :
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


from .mongodb_client import get_db
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import traceback
from datetime import datetime

class PortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            db = get_db()
            portfolio_collection = db.portfolio

            # Get user portfolio from MongoDB
            portfolio = portfolio_collection.find_one({"userId": str(request.user.id)})

            if portfolio and portfolio.get('holdings'):
                holdings = portfolio['holdings']
            else:
                holdings = []

            return Response({"success": True, "portfolio": {"holdings": holdings}}, status=200)
        except Exception as e:
            print("Error fetching portfolio:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)

    def post(self, request):
        try:
            db = get_db()
            portfolio_collection = db.portfolio

            user_id = str(request.user.id)
            asset_name = request.data.get("asset_name")
            quantity = request.data.get("quantity")
            value = request.data.get("value")

            if not asset_name or not quantity or not value:
                return Response(
                    {"success": False, "error": "Missing required fields"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get existing portfolio or create new one
            portfolio = portfolio_collection.find_one({"userId": user_id})
            if not portfolio:
                portfolio = {
                    "userId": user_id,
                    "holdings": [],
                    "lastUpdated": datetime.utcnow(),
                    "createdAt": datetime.utcnow()
                }

            # Add new holding
            new_holding = {
                "symbol": asset_name,
                "name": asset_name,  # You might want to get the full name from somewhere
                "shares": float(quantity),
                "avgPrice": float(value) / float(quantity),
                "totalCost": float(value)
            }

            portfolio['holdings'].append(new_holding)
            portfolio['lastUpdated'] = datetime.utcnow()

            # Upsert portfolio
            portfolio_collection.replace_one(
                {"userId": user_id},
                portfolio,
                upsert=True
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
            db = get_db()
            watchlist_collection = db.watchlist

            # Get user watchlist from MongoDB
            watchlist = watchlist_collection.find_one({"userId": str(request.user.id)})

            if watchlist and watchlist.get('stocks'):
                stocks = watchlist['stocks']
            else:
                stocks = []

            return Response({"success": True, "watchlist": stocks})
        except Exception as e:
            print("Error fetching watchlist:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)

    def post(self, request):
        try:
            db = get_db()
            watchlist_collection = db.watchlist

            user_id = str(request.user.id)
            stock_symbol = request.data.get("stock_symbol")
            stock_name = request.data.get("stock_name", stock_symbol)

            if not stock_symbol:
                return Response(
                    {"success": False, "error": "Stock symbol is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get existing watchlist or create new one
            watchlist = watchlist_collection.find_one({"userId": user_id})
            if not watchlist:
                watchlist = {
                    "userId": user_id,
                    "stocks": [],
                    "lastUpdated": datetime.utcnow(),
                    "createdAt": datetime.utcnow()
                }

            # Check if stock already exists
            existing_stock = next((s for s in watchlist['stocks'] if s['symbol'] == stock_symbol), None)
            if existing_stock:
                return Response(
                    {"success": False, "error": "Stock already in watchlist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Add new stock
            new_stock = {
                "symbol": stock_symbol,
                "name": stock_name
            }

            watchlist['stocks'].append(new_stock)
            watchlist['lastUpdated'] = datetime.utcnow()

            # Upsert watchlist
            watchlist_collection.replace_one(
                {"userId": user_id},
                watchlist,
                upsert=True
            )

            return Response({"success": True, "message": "Added to watchlist"})
        except Exception as e:
            print("Error adding to watchlist:", str(e))
            return Response({"success": False, "error": str(e)}, status=500)
