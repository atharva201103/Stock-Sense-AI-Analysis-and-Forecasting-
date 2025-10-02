from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.urls import path
from aut.views import RegisterView, LoginView , ModelView , UserFromTokenView , PortfolioView,WatchlistView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("api/register" , RegisterView.as_view() , name = "register"),
    path("api/login" , LoginView.as_view() , name = "login"),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/user' , UserFromTokenView.as_view() ,name='user_profile'),
    path('model/', ModelView.as_view(), name='model'),
    path('api/user/portfolio', PortfolioView.as_view(), name='user-portfolio'),
    path('user/watchlist/', WatchlistView.as_view(), name='user-watchlist'),



]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)