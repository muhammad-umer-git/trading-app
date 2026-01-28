from rest_framework import serializers

from accounts.models import Account, CustomUser, Ledger, Position, Stock, Trade


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "password")

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        Account.objects.create(user=user)
        return user


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("account_type", "balance", "created_at")


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ("symbol", "quantity", "average_price", "created_at")


class LedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ledger
        fields = ("id", "transaction_type", "amount", "timestamp")


class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ("symbol", "name", "exchange", "price")


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = ("symbol", "transaction_type", "price", "timestamp")
