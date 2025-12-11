from django.urls import path

from . import views
from .views import StockBatchView, StockBatchListView, StockHistoryView, StockBatchSoldDetailView

urlpatterns = [

    path('stocks/<uuid:book_uuid>/', views.stock_detail, name='stock_detail'),

    # path('stock/<uuid:book_uuid>/restock/', views.restock, name='restock'),
    path('stocks/<uuid:book_uuid>/restock/', StockBatchView.as_view(), name='restock'),
    path('stocks/<uuid:book_uuid>/restock/edit/<uuid:batch_uuid>', StockBatchView.as_view(),
         name='admin_stock_batch_edit'),
    path('stocks/<uuid:book_uuid>/update-price/', views.update_price, name='update_price'),

    # path('stocked/batch/<uuid:book_uuid>/batches/', views.stockBatchesView, name='admin_stock_batches'),
    # path('stocked/batch/<uuid:book_uuid>/batches/', StockBatchListView.as_view(), name='admin_stock_batches'),
    path('stocks/<uuid:book_uuid>/batches/', StockBatchListView.as_view(), name='admin_stock_batches'),

    path('stock/batch/<uuid:batch_uuid>/sold/', StockBatchSoldDetailView.as_view(), name='batch_sold_details'),

    # path('stocked/stockHistory/<uuid:book_uuid>/history/', views.stockHistoryView, name='admin_stock_history'),
    # path('stocked/stockHistory/<uuid:book_uuid>/history/', StockHistoryView.as_view(), name='admin_stock_history'),
    path('stocks/<uuid:book_uuid>/stock-history/', StockHistoryView.as_view(), name='admin_stock_history'),
    path('stocks/<uuid:book_uuid>/price-history/', views.stockPriceView, name='admin_price_history'),
    path('stocks/<uuid:book_uuid>/reservation/', views.stockReservationView,
         name='admin_active_reservation'),
]
