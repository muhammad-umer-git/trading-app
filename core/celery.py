import os

from celery import Celery
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.task_queues = (
    Queue("trades", routing_key="trades.#"),
    Queue("updates", routing_key="updates.#"),
)

app.conf.task_default_queue = "default"
app.conf.task_default_exchange = "default"
app.conf.task_default_routing_key = "default"

app.conf.task_routes = {
    "accounts.tasks.process_trade": {"queue": "trades", "routing_key": "trades.high"},
    "accounts.tasks.updates_stock_prices": {
        "queue": "updates",
        "routing_key": "updates.low",
    },
}
