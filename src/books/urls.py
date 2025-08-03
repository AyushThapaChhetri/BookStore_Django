from django.urls import path
from . import views
from .views import BookListView, BookCreateView, BookDeleteView, BookUpdateView, BookDetailView

urlpatterns = [
    path('hello', views.hello),
    path('', BookListView.as_view(), name='book_list'),
    path('create/', BookCreateView.as_view(),name='book_create'),
    path('update/<uuid>', BookUpdateView.as_view(),name='book_update'),
    path('delete/<uuid>', BookDeleteView.as_view(), name='book_delete'),
    path('detail/<uuid>', BookDetailView.as_view(),name='book_detail_view'),
    path('search/',views.search_books,name='search_books')
]