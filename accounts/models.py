from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    # name = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.username, self.id}"


class Account(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="account"
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    account_type = models.CharField(
        max_length=20, choices=[("demo", "Demo"), ("live", "Live")], default="demo"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username, self.id}"


class Position(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="positions"
    )
    symbol = models.CharField(max_length=10)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    average_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.symbol} - {self.quantity} @ {self.average_price}"


class Ledger(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="ledger"
    )
    transaction_type = models.CharField(
        max_length=10, choices=[("deposit", "deposit"), ("withdraw", "withdraw")]
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amount} {self.transaction_type} on {self.timestamp}"


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    exchange = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} {self.exchange} @ {self.price}"

    class Meta:
        indexes = [
            models.Index(fields=["symbol"]),
        ]


class Trade(models.Model):
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="trades"
    )
    symbol = models.CharField(max_length=10)
    transaction_type = models.CharField(
        max_length=4, choices=[("buy", "Buy"), ("sell", "Sell")]
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField()
