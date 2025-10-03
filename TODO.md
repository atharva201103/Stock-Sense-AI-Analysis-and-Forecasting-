# TODO: Fix Frontend-Backend Communication and Backend User Model

## Backend Changes
- [x] Update backend/aut/models.py: Add UserProfile model with balance field.
- [x] Update backend/aut/serializers.py: Add PortfolioSerializer and UserProfileSerializer.
- [x] Update backend/aut/views.py: Modify PortfolioView and WatchlistView to use Django models; add BalanceView.
- [x] Update backend/aut/urls.py: Add balance endpoint, fix watchlist URL to include 'api/' prefix.
- [x] Run Django migrations for new models.

## Frontend Changes
- [x] Update frontend/services/user-service.ts: Change API_URL to Django backend URL, adjust endpoint paths to match Django URLs.

## Testing
- [x] Test API endpoints for portfolio, watchlist, balance.
- [x] Verify frontend can fetch and update user data correctly.
