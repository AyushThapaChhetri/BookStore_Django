# books/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_save


class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.books'

    def ready(self):
        # Import models inside ready(), AFTER apps are loaded
        from .models import Book, Stock

        # Signal handler
        def create_stock_for_new_book(sender, instance, created, **kwargs):
            if created:
                Stock.objects.create(book=instance, stock_quantity=0, price=0.00)
                print(f"[Signal] Stock created for new book: {instance.title}")
            else:
                if not hasattr(instance, 'stock'):
                    Stock.objects.create(book=instance, stock_quantity=0, price=0.00)
                    print(f"[Signal] Stock was missing and has been created for: {instance.title}")

        # Connect the signal
        post_save.connect(create_stock_for_new_book, sender=Book)
