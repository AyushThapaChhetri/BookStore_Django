from django.urls import path

from . import views
from .views import BookListView, BookDetailView, BookView

urlpatterns = [
    path('hello', views.hello),
    path('list', BookListView.as_view(), name='book_list'),
    path('', BookView.as_view(), name='book_view'),
    path('<uuid>', BookView.as_view(), name='book_view'),
    path('delete/<uuid>', BookView.as_view(), name='book_view'),
    path('detail/<uuid>', BookDetailView.as_view(), name='book_detail_view'),
    path('search/', views.search_books, name='search_books')
]
