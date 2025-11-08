from django.urls import path

from . import views

urlpatterns = [
    # path('stocks/', StockListView.as_view(), name='stock_list'),
    # path('stocks/<int:pk>/', StockDetailView.as_view(), name='stock_detail'),

    path('stocked/detail/<uuid:book_uuid>/', views.stock_detail, name='stock_detail'),
    # path('stocked/detail/<uuid:book_uuid>/', views.stock_detail, name='stock_detail'),
    path('stock/<uuid:book_uuid>/restock/', views.restock, name='restock'),
    path('stock/<uuid:book_uuid>/update-price/', views.update_price, name='update_price'),
]
