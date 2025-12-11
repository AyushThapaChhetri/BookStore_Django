from django.urls import path

from . import views
from .views import BookListView, BookView, AuthorView, PublisherView, GenreView, BookAdminView, BookDetailView, \
    StockListView, AuthorListView, AuthorDetailView, PublisherListView, PublisherDetailView, \
    GenreListView, GenreDetailView

urlpatterns = [
    path('', BookAdminView.as_view(), name='admin-pannel'),
    # path('manage/book/list/', BookListView.as_view(), name='admin-book-list'),

    path('books/', BookListView.as_view(), name='admin-book-list'),
    path('books/<uuid>', BookDetailView.as_view(), name='book_detail_view'),
    path('books/create/', BookView.as_view(), name='book_view'),
    path('books/edit/<uuid>', BookView.as_view(), name='book_view'),
    path('books/delete/<uuid>/', BookView.as_view(), name='book_delete'),
    path('search/', views.search_books, name='search_books'),
    path('books/recycle-bin/', views.BookRecycleBinListView.as_view(), name='book_recycle_bin'),
    path('books/restore/<uuid:uuid>/', views.BookRestoreView.as_view(), name='book_restore'),
    path('book/permanent-delete/<uuid:uuid>/', views.BookPermanentDeleteView.as_view(), name='book_permanent_delete'),

    path('search/authors', views.search_authors, name='search_authors'),
    # path('authors', AuthorView.as_view(), name="create_author"),
    # path('manage/author/list/', AuthorListView.as_view(), name="admin_author_list"),
    path('authors/', AuthorListView.as_view(), name="admin_author_list"),
    path('authors/create/', AuthorView.as_view(), name='author_view'),
    path('authors/edit/<uuid>', AuthorView.as_view(), name='author_view'),
    path('authors/<uuid>', AuthorDetailView.as_view(), name='author_detail_view'),

    path('search/publishers', views.search_publishers, name='search_publishers'),
    # path('publisher', PublisherView.as_view(), name="create_publisher"),
    path('publishers/', PublisherListView.as_view(), name="admin_publisher_list"),
    path('publishers/create/', PublisherView.as_view(), name='publisher_view'),
    path('publishers/edit/<uuid>', PublisherView.as_view(), name='publisher_view'),
    path('publishers/<uuid>', PublisherDetailView.as_view(), name='publisher_detail_view'),

    path("<str:field_name>/options", views.field_options, name="field-options"),

    path('search/genres', views.search_genres, name='search_genres'),
    # path('genres', GenreView.as_view(), name="create_genres"),
    # path('manage/genre/list/', GenreListView.as_view(), name="admin_genre_list"),
    path('genres/', GenreListView.as_view(), name="admin_genre_list"),
    path('genres/create/', GenreView.as_view(), name='genre_view'),
    path('genres/edit/<uuid>', GenreView.as_view(), name='genre_view'),
    path('genres/<uuid>', GenreDetailView.as_view(), name='genre_detail_view'),

    # path('manage/stock/list/', StockListView.as_view(), name='admin-stock-list'),
    path('stocks/', StockListView.as_view(), name='admin-stock-list'),
    # path('stocks/detail/<uuid>', StockDetailView.as_view(), name='stock_detail_view'),
    # path('stocks/<uuid>', StockDetailView.as_view(), name='stock_detail_view'),
    # path('stock/create/', StockView.as_view(), name='stock_view'),
    # path('stock/edit/<uuid>', StockView.as_view(), name='stock_view'),
    # path('stock/reset/<uuid>/', StockView.as_view(), name='stock_reset'),

    path('books/search/', views.search_books, name='search_books')

]
