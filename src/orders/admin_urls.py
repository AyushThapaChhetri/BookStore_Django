from django.urls import path

from src.orders.views import OrderView
from . import views

urlpatterns = [
    # path('myorders', MyOrders.as_view(), name='admin_myorders'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('manage/order/list/', OrderView.as_view(), name='admin_order_list'),
    # path('order/detail/<uuid>', StockDetailView.as_view(), name='stock_detail_view'),
]
