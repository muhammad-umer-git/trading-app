from unittest.mock import patch

import fakeredis
from django.db import connection
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Account, CustomUser, Ledger, Position, Stock


class BaseAuthTestCase(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="testuser", email="test@example.com", password="Testpass123"
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.refresh_token = str(refresh)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

        self.account = Account.objects.create(
            user=self.user, balance=98270.45, account_type="live"
        )


class AuthTests(BaseAuthTestCase):

    def setUp(self):
        super().setUp()
        self.register_url = reverse("auth")
        self.login_url = reverse("token_obtain_pair")
        self.refresh_url = reverse("token_refresh")
        self.protect_url = reverse("protected_view")

        self.user_data = {
            "username": "testuser2",
            "email": "test2@example.com",
            "password": "Testpass123",
        }

    def test_register_user(self):
        response = self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            "User has been Registered Successfully", response.data["message"]
        )

    def test_login_user(self):
        CustomUser.objects.create_user(**self.user_data)
        response = self.client.post(self.login_url, self.user_data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_refresh_token(self):
        CustomUser.objects.create_user(**self.user_data)
        login_response = self.client.post(self.login_url, self.user_data, format="json")
        refresh_token = login_response.data["refresh"]
        response = self.client.post(
            self.refresh_url, {"refresh": refresh_token}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_protect_view(self):
        response = self.client.get(self.protect_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.data)
        self.assertIn("account", response.data)


class AccountTests(BaseAuthTestCase):

    def setUp(self):
        super().setUp()
        self.ledger_url = reverse("accounts-ledger", kwargs={"pk": self.account.id})
        self.positions_url = reverse(
            "accounts-positions", kwargs={"pk": self.account.id}
        )

    def test_account_legder(self):
        Ledger.objects.create(
            account=self.account, transaction_type="deposit", amount=100.0
        )
        response = self.client.get(self.ledger_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("transaction_type", response.data[0])

    def test_account_positions(self):
        Position.objects.create(
            account=self.account, symbol="AAPL", quantity=5, average_price=255
        )
        response = self.client.get(self.positions_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("symbol", response.data[0])


# @override_settings(CACHES={
#     "default":{
#         "BACKEND":"django.core.cache.backends.locmem.LocMemCache",
#         "LOCATION": "fake-cache",
#     }
# })
class StockTests(BaseAuthTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse("stocks-list")
        self.ingest_url = reverse("stocks-ingest")
        Stock.objects.create(
            symbol="AAPL", name="Apple Inc", exchange="NASDAQ", price=180.50
        )
        Stock.objects.create(
            symbol="GOOGL", name="Google", exchange="NASDAQ", price=275.20
        )
        Stock.objects.create(
            symbol="MSFT", name="Microsoft", exchange="NASDAQ", price=320.00
        )

    def test_stock_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("symbol", response.data["results"][0])
        self.assertIn("price", response.data["results"][0])

    def test_search_filter(self):
        response = self.client.get(f"{self.url}?search=goo")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual((response.data["results"])[0]["symbol"], "GOOGL")

    def test_ordering_filter(self):
        response = self.client.get(f"{self.url}?ordering=price")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [stock["price"] for stock in response.data["results"]]
        self.assertEqual(prices, sorted(prices))

    def test_stock_ingest(self):
        self.user.is_staff = True
        self.user.save()
        data = [
            {
                "symbol": "BIT",
                "name": "Bitcoin Inc",
                "exchange": "NASDAQ",
                "price": "255.01",
            }
        ]
        response = self.client.post(self.ingest_url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual("Stock ingested Successfully", response.data["message"])

    @patch("django_redis.get_redis_connection")
    def test_stock_detail(self, mock_get_redis_connection):
        fake_redis = fakeredis.FakeRedis()
        mock_get_redis_connection.return_value = fake_redis

        stock = Stock.objects.create(
            symbol="TSLA", name="Tesla", exchange="NASDAQ", price=250.0
        )
        url = reverse("stocks-detail", kwargs={"symbol": stock.symbol})
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response1.data["symbol"], "TSLA")

        cached_data = fake_redis.get(f"stock:{stock.symbol}")
        self.assertIsNone(cached_data)

        before = len(connection.queries)
        response2 = self.client.get(url)
        after = len(connection.queries)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.data["symbol"], "TSLA")
        print("Number of DB queries:", after - before)


class TradeTests(BaseAuthTestCase):
    @patch("django_redis.get_redis_connection")
    @patch("accounts.views.process_trade.delay")
    def test_create_trade(self, mock_delay, mock_get_redis_connection):
        fake_redis = fakeredis.FakeRedis()
        mock_get_redis_connection.return_value = fake_redis

        stock = Stock.objects.create(
            symbol="AAPL", name="Apple", exchange="NASDAQ", price=170.0
        )
        url = reverse("trades-execute-trade")
        data = {"stock": stock.id, "trade_type": "BUY", "quantity": 10}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("successfully", response.data["message"])
