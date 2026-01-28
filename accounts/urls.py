from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    AccountViewSets,
    ProtectedAPIView,
    RegisterView,
    StockViewSet,
    TradeViewSet,
)

router = DefaultRouter()

router.register(r"accounts", AccountViewSets, basename="accounts")
router.register(r"stocks", StockViewSet, basename="stocks")
router.register(r"trades", TradeViewSet, basename="trades")

urlpatterns = [
    path("auth/", RegisterView.as_view(), name="auth"),
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/protect/", ProtectedAPIView.as_view(), name="protected_view"),
    path("", include(router.urls)),
]
