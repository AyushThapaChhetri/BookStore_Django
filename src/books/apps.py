# books/apps.py
from django.apps import AppConfig
from django.db import transaction
from django.db.models.signals import post_save


class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.books'

    def ready(self):
        from .models import Book
        from src.stock.models import Stock

        def create_stock_for_new_book(sender, instance, created, **kwargs):
            if created:
                def _create_stock():
                    # Only create Stock if it doesn't exist
                    Stock.objects.get_or_create(
                        book=instance,
                        defaults={
                            'current_price': 0.00,
                            'current_discount_percentage': 0.00,
                            'is_available': False,
                            'last_restock_date': None
                        }
                    )
                    print(f"[Signal] Stock created for new book: {instance.title}")

                # Wait until the transaction is fully committed
                transaction.on_commit(_create_stock)

        post_save.connect(create_stock_for_new_book, sender=Book)

        # Signal handler
        # def create_stock_for_new_book(sender, instance, created, **kwargs):
        # if created and not hasattr(instance, 'stock'):
        #     Stock.objects.create(
        #         book=instance,
        #         current_price=0.00,
        #         current_discount_percentage=0.00,
        #         is_available=False,
        #         last_restock_date=None
        #     )
        #     print(f"[Signal] Stock created for new book: {instance.title}")
        #
        # elif not hasattr(instance, 'stock'):
        #     Stock.objects.create(
        #         book=instance,
        #         current_price=0.00,
        #         current_discount_percentage=0.00,
        #         is_available=False,
        #         last_restock_date=None
        #     )
        #     print(f"[Signal] Missing stock recreated for existing book: {instance.title}")

        # Connect the signal
        # post_save.connect(create_stock_for_new_book, sender=Book)
