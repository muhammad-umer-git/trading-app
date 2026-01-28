import csv
import logging
import os
import time
from decimal import Decimal

import yfinance as yf
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from accounts.models import Account, Ledger, Position, Stock, Trade

logger = logging.getLogger("trade_logger")


@shared_task(queue="trades", priority=0)
def process_trade(user_id, symbol, quantity, trade_type):
    logger.info(
        f"Starting{trade_type} trade for user={user_id}, symbol={symbol}, quantity={quantity}"
    )
    with transaction.atomic():
        try:
            account = Account.objects.select_for_update().get(user_id=user_id)
            stock = Stock.objects.get(symbol=symbol)
            quantity = Decimal(quantity)
            logger.info(
                f"Fetched account and stock for {symbol} at price={stock.price}"
            )

            if trade_type == "buy":
                total_cost = stock.price * quantity
                if account.balance < total_cost:
                    return {"error": "Insufficient balance."}

                account.balance -= total_cost
                account.save(update_fields=["balance"])

                position = account.positions.filter(symbol=symbol).first()
                if position:
                    position.quantity += quantity
                    position.average_price = stock.price
                    position.save(update_fields=["quantity", "average_price"])

                else:
                    Position.objects.create(
                        account=account,
                        symbol=symbol,
                        quantity=quantity,
                        average_price=stock.price,
                    )

                Ledger.objects.create(
                    account=account,
                    transaction_type="withdraw",
                    amount=total_cost,
                )

                Trade.objects.create(
                    account=account,
                    symbol=symbol,
                    transaction_type="buy",
                    price=stock.price,
                    quantity=quantity,
                    timestamp=timezone.now(),
                )
                logger.info(
                    f"Successfully completed {trade_type} trade for user={user_id}"
                )

                return {"message": f"{trade_type} order executed successfully"}

            elif trade_type == "sell":
                total_revenue = stock.price * quantity

                position = account.positions.filter(symbol=symbol).first()
                if not position or position.quantity < quantity:
                    return {"error": "Not enough stock to sell."}

                account.balance += total_revenue
                account.save(update_fields=["balance"])

                position.quantity -= quantity
                if position.quantity == 0:
                    position.delete()
                else:
                    position.save(update_fields=["quantity"])

                Ledger.objects.create(
                    account=account,
                    transaction_type="deposit",
                    amount=total_revenue,
                )

                Trade.objects.create(
                    account=account,
                    symbol=symbol,
                    transaction_type="sell",
                    price=stock.price,
                    quantity=quantity,
                    timestamp=timezone.now(),
                )

                logger.info(
                    f"Successfully completed {trade_type} trade for user={user_id}"
                )

                return {"message": f"{trade_type} order executed successfully"}
        except Exception as e:
            logger.error(
                f"Trade failed for user={user_id}, symbol={symbol}, error={str(e)}"
            )
            return {"error": str(e)}


@shared_task
def test_beat_task():
    logger.info("Celery beat task executed successfully")
    return "Beat task executed"


@shared_task(rate_limit="9/m", queue="updates", priority=9)
def update_stock_prices():
    logger.info("Starting stock price update task ...")

    symbols = ["AAPL", "GOOGL", "TSLA"]

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.history(period="1d")["Close"].iloc[-1]

            if price:
                stock = Stock.objects.get(symbol=symbol)
                stock.price = price
                stock.save()

                cache.set(f"stock:{symbol}", price, timeout=60 * 5)

                logger.info(f"Updated {symbol} with price {price}")
            else:
                logger.warning(f"Price not found for {symbol}")

        except Exception as e:
            logger.error(f"Failed to update {symbol}: {e}")

        time.sleep(2)


@shared_task(rate_limit="1/h")
def generate_daily_report():
    reports_dir = os.path.join(settings.BASE_DIR, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    today_str = timezone.now().strftime("%Y-%m-%d")
    file_path = os.path.join(reports_dir, f"report_{today_str}.csv")

    with open(file_path, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(
            ["username", "symbol", "trade_type", "quantity", "price", "balance"]
        )

        trades = Trade.objects.filter(timestamp__date=timezone.now().date())

        for trade in trades:
            writer.writerow(
                [
                    trade.account.user.username,
                    trade.symbol,
                    trade.transaction_type,
                    trade.quantity,
                    trade.price,
                    trade.account.balance,
                ]
            )

    return f"Report created: {file_path}"
