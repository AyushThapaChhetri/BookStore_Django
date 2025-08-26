from django.urls import path

from . import views
from .views import BookListView, BookView, AuthorView, PublisherView, GenreView, BookAdminView, BookDetailView, \
    StockListView, StockDetailView, StockView

urlpatterns = [
    path('', BookAdminView.as_view(), name='admin-pannel'),
    path('list/', BookListView.as_view(), name='admin-book-list'),

    # Specific actions for books
    path('detail/<uuid>', BookDetailView.as_view(), name='book_detail_view'),
    path('book/create/', BookView.as_view(), name='book_view'),
    path('edit/<uuid>', BookView.as_view(), name='book_view'),
    path('book/delete/<uuid>', BookView.as_view(), name='book_delete'),
    path('search/', views.search_books, name='search_books'),

    # author
    path('authors', AuthorView.as_view(), name="create_author"),
    path('publisher', PublisherView.as_view(), name="create_publisher"),
    path('genres', GenreView.as_view(), name="create_genres"),

    # cart
    path('manage/stock/list/', StockListView.as_view(), name='admin-stock-list'),
    path('stock/detail/<uuid>', StockDetailView.as_view(), name='stock_detail_view'),
    path('stock/create/', StockView.as_view(), name='stock_view'),
    path('stock/edit/<uuid>', StockView.as_view(), name='stock_view'),
    path('stock/reset/<uuid>', StockView.as_view(), name='stock_reset'),

]
