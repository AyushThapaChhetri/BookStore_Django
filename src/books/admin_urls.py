from django.urls import path

from . import views
from .views import BookListView, BookView, AuthorView, PublisherView, GenreView, BookAdminView, BookDetailView, \
    StockListView, StockDetailView, StockView, AuthorListView, AuthorDetailView, PublisherListView, PublisherDetailView, \
    GenreListView, GenreDetailView

urlpatterns = [
    path('', BookAdminView.as_view(), name='admin-pannel'),
    # path('list/', BookListView.as_view(), name='admin-book-list'),
    path('manage/book/list/', BookListView.as_view(), name='admin-book-list'),

    # Specific actions for books
    path('detail/<uuid>', BookDetailView.as_view(), name='book_detail_view'),
    path('book/create/', BookView.as_view(), name='book_view'),
    path('book/edit/<uuid>', BookView.as_view(), name='book_view'),
    path('book/delete/<uuid>/', BookView.as_view(), name='book_delete'),
    path('search/', views.search_books, name='search_books'),
    path('books/recycle-bin/', views.BookRecycleBinListView.as_view(), name='book_recycle_bin'),
    path('books/restore/<uuid:uuid>/', views.BookRestoreView.as_view(), name='book_restore'),
    path('book/permanent-delete/<uuid:uuid>/', views.BookPermanentDeleteView.as_view(), name='book_permanent_delete'),

    # author
    path('search/authors', views.search_authors, name='search_authors'),
    path('authors', AuthorView.as_view(), name="create_author"),
    path('manage/author/list/', AuthorListView.as_view(), name="admin_author_list"),
    path('author/create/', AuthorView.as_view(), name='author_view'),
    path('author/edit/<uuid>', AuthorView.as_view(), name='author_view'),
    path('author/detail/<uuid>', AuthorDetailView.as_view(), name='author_detail_view'),

    path('search/publishers', views.search_publishers, name='search_publishers'),
    path('publisher', PublisherView.as_view(), name="create_publisher"),
    path('manage/publisher/list/', PublisherListView.as_view(), name="admin_publisher_list"),
    path('publisher/create/', PublisherView.as_view(), name='publisher_view'),
    path('publisher/edit/<uuid>', PublisherView.as_view(), name='publisher_view'),
    path('publisher/detail/<uuid>', PublisherDetailView.as_view(), name='publisher_detail_view'),

    # select options
    path("<str:field_name>/options", views.field_options, name="field-options"),

    path('search/genres', views.search_genres, name='search_genres'),
    path('genres', GenreView.as_view(), name="create_genres"),
    path('manage/genre/list/', GenreListView.as_view(), name="admin_genre_list"),
    path('genre/create/', GenreView.as_view(), name='genre_view'),
    path('genre/edit/<uuid>', GenreView.as_view(), name='genre_view'),
    path('genre/detail/<uuid>', GenreDetailView.as_view(), name='genre_detail_view'),

    # cart
    path('manage/stock/list/', StockListView.as_view(), name='admin-stock-list'),
    path('stock/detail/<uuid>', StockDetailView.as_view(), name='stock_detail_view'),
    path('stock/create/', StockView.as_view(), name='stock_view'),
    path('stock/edit/<uuid>', StockView.as_view(), name='stock_view'),
    path('stock/reset/<uuid>/', StockView.as_view(), name='stock_reset'),

    # search books
    path('books/search/', views.search_books, name='search_books')

]
