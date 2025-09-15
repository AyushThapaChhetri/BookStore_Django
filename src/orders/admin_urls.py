from django.urls import path

from src.orders.views import MyOrders

urlpatterns = [
    path('myorders', MyOrders.as_view(), name='admin_myorders'),
]
