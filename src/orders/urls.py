from django.urls import path

from src.orders.views import MyOrders

urlpatterns = [
    path('client/myorders', MyOrders.as_view(), name='myorders'),
]
