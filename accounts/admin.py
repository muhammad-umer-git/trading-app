from django.contrib import admin

from .models import Account, CustomUser, Ledger, Position, Stock, Trade

admin.site.register(CustomUser)
admin.site.register(Account)
admin.site.register(Position)
admin.site.register(Ledger)
admin.site.register(Stock)
admin.site.register(Trade)
