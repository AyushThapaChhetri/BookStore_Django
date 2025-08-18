from django.urls import path

from src.shipping.views import DeliverInfoView

urlpatterns = [
    # Specific actions for books
    path('', DeliverInfoView.as_view(), name='book_delivery_info'),
]
