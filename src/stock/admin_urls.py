from django.urls import path

from . import views
from .views import StockBatchView, StockBatchListView, StockHistoryView

urlpatterns = [

    path('stocked/detail/<uuid:book_uuid>/', views.stock_detail, name='stock_detail'),

    # path('stock/<uuid:book_uuid>/restock/', views.restock, name='restock'),
    path('stock/<uuid:book_uuid>/restock/', StockBatchView.as_view(), name='restock'),
    path('stock/<uuid:book_uuid>/restock/edit/<uuid:batch_uuid>', StockBatchView.as_view(),
         name='admin_stock_batch_edit'),
    path('stock/<uuid:book_uuid>/update-price/', views.update_price, name='update_price'),

    # path('stocked/batch/<uuid:book_uuid>/batches/', views.stockBatchesView, name='admin_stock_batches'),
    path('stocked/batch/<uuid:book_uuid>/batches/', StockBatchListView.as_view(), name='admin_stock_batches'),

    # path('stocked/stockHistory/<uuid:book_uuid>/history/', views.stockHistoryView, name='admin_stock_history'),
    path('stocked/stockHistory/<uuid:book_uuid>/history/', StockHistoryView.as_view(), name='admin_stock_history'),
    path('stocked/priceHistory/<uuid:book_uuid>/history/', views.stockPriceView, name='admin_price_history'),
    path('stocked/activeReservation/<uuid:book_uuid>/reservation/', views.stockReservationView,
         name='admin_active_reservation'),
]
