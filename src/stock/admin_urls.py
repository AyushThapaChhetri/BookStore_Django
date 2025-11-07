from django.urls import path

from src.stock.views import StockListView, StockDetailView

urlpatterns = [
    path('stocks/', StockListView.as_view(), name='stock_list'),
    path('stocks/<int:pk>/', StockDetailView.as_view(), name='stock_detail'),
]
