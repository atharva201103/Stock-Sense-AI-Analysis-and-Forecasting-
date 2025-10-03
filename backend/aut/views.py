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
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            prompt = request.data.get('prompt', '')
            user = request.user  # ✅ Now works with JWT

            print("---------------------------------------------")
            print("User:", user)
            print("Prompt:", prompt[:200] + "..." if len(prompt) > 200 else prompt)
            print("---------------------------------------------")
            payload = {
                "model": "deepseek-r1:1.5b",
                "messages": [
                    {"role": "system", "content": ""},
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }

            print("Sending payload to Ollama:", payload)

            # Send request to Ollama
            ollama_response = requests.post("http://localhost:11434/api/chat", json=payload)
            print("Ollama response status:", ollama_response.status_code)
            if ollama_response.status_code != 200:
                print("Ollama error text:", ollama_response.text)
                return JsonResponse({"error": f"Ollama API error: {ollama_response.status_code} - {ollama_response.text}"}, status=500)
            output = ollama_response.json()
            print("Ollama output keys:", list(output.keys()))
            response = output['message']['content']
            print("Raw AI response:", response)
            print("AI response length:", len(response))

            # Remove <think> blocks from DeepSeek R1 responses
            import re
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
            portfolios = Portfolio.objects.filter(user=request.user)
            serializer = PortfolioSerializer(portfolios, many=True)
            holdings = []
            for item in serializer.data:
                holdings.append({
                    "symbol": item['asset_name'],
                    "name": item['asset_name'],
                    "shares": item['quantity'],
                    "avgPrice": item['value'] / item['quantity'] if item['quantity'] > 0 else 0,
                    "totalCost": item['value']
                })
            return Response({"success": True, "portfolio": {"holdings": holdings}}, status=200)
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
